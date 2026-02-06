import json
import logging
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import func

import ckan.authz as authz
import ckan.logic as logic
from ckan import model
from .api import get_site_scope_group_ids
from .http_utils import get_with_fast_fail
from .keyword_groups import canada_keyword_groups
from ckan.model.system_info import get_system_info, set_system_info
from ckan.types import Context
from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportJob
from ckanext.udc_import_other_portals.logic.base import get_package_ids_by_import_config_id
from ckanext.udc.solr.config import get_udc_langs

log = logging.getLogger(__name__)


ARCGIS_PORTAL_CACHE_KEY = "ckanext.udc_import_other_portals.arcgis_portal_discovery"
ARCGIS_PORTAL_CONFIG_KEY = "ckanext.udc_import_other_portals.arcgis_portal_discovery_config"
ARCGIS_AUTO_IMPORT_FLAG = "auto_arcgis"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _unique_strings(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(values))


def _slugify_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-_")
    return slug


def _build_or_terms(terms: List[str]) -> str:
    quoted = []
    for term in terms:
        cleaned = term.replace('"', "")
        quoted.append(f"\"{cleaned}\"")
    return f"({ ' OR '.join(quoted) })"


def _canada_keyword_groups() -> List[Dict[str, List[str]]]:
    return canada_keyword_groups()


def _normalize_keyword_groups(groups: Any) -> List[Dict[str, List[str]]]:
    if not isinstance(groups, list):
        return []
    normalized: List[Dict[str, List[str]]] = []
    for idx, group in enumerate(groups):
        if not isinstance(group, dict):
            continue
        label = group.get("label")
        if not isinstance(label, str) or not label.strip():
            label = f"group_{idx + 1}"
        terms = group.get("terms")
        if not isinstance(terms, list):
            continue
        cleaned_terms = [str(term).strip() for term in terms if str(term).strip()]
        cleaned_terms = _unique_strings(cleaned_terms)
        if not cleaned_terms:
            continue
        normalized.append({"label": label.strip(), "terms": cleaned_terms})
    return normalized


def _load_keyword_groups() -> List[Dict[str, List[str]]]:
    cached = get_system_info(ARCGIS_PORTAL_CONFIG_KEY)
    if cached:
        try:
            payload = json.loads(cached)
        except ValueError:
            payload = {}
        groups = _normalize_keyword_groups(payload.get("keyword_groups"))
        if groups:
            return groups
    return _canada_keyword_groups()


def _class_name_from_title(title: str, portal_id: str) -> str:
    slug = _slugify_ascii(title)
    if not slug:
        slug = f"portal-{portal_id[:6]}"
    parts = re.split(r"[^a-zA-Z0-9]+", slug)
    base = "".join(part.capitalize() for part in parts if part)
    if not base:
        base = "ArcGIS"
    if not base[0].isalpha():
        base = f"ArcGIS{base}"
    if not base.endswith("Import"):
        base = f"{base}Import"
    return base


def _name_prefix_from_title(title: str, portal_id: str) -> str:
    slug = _slugify_ascii(title)
    suffix = portal_id[:6] if portal_id else "portal"
    base = f"{slug}-{suffix}" if slug else f"portal-{suffix}"
    return f"{base}-"


def _build_base_api(portal_url: str) -> Optional[str]:
    if not portal_url:
        return None
    try:
        parsed = requests.utils.urlparse(portal_url)
    except Exception:
        return None
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _build_import_code(
    portal_url: str,
    class_name: str,
    name_prefix: str,
    source_portal: str,
    language: Optional[str] = None,
) -> str:
    safe_portal = source_portal.replace('"""', '"')
    language_line = f"    language = {language!r}\n" if language else ""
    return (
        "from ckanext.udc_import_other_portals.logic.arcgis_based.base import ArcGISBasedImport\n\n"
        f"# {portal_url}\n\n"
        f"class {class_name}(ArcGISBasedImport):\n"
        '    """\n'
        f"    Import implementation for {safe_portal} ({portal_url})\n"
        '    """\n'
        f"    name_prefix = {name_prefix!r}\n"
        f"    source_portal = {source_portal!r}\n\n"
        f"{language_line}"
        f"DefaultImportClass = {class_name}\n"
    )


def _normalize_language(value: Optional[str], allowed: List[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower().replace("_", "-")
    allowed_map = {lang.lower(): lang for lang in allowed}
    if normalized in allowed_map:
        return allowed_map[normalized]
    if "-" in normalized:
        prefix = normalized.split("-", 1)[0]
        if prefix in allowed_map:
            return allowed_map[prefix]
    return None


def _load_portal_cache() -> Dict[str, Any]:
    cached = get_system_info(ARCGIS_PORTAL_CACHE_KEY)
    if not cached:
        return {}
    try:
        return json.loads(cached)
    except ValueError:
        return {}


def _auto_arcgis_configs() -> List[CUDCImportConfig]:
    configs = model.Session.query(CUDCImportConfig).all()
    return [
        config
        for config in configs
        if (config.other_config or {}).get(ARCGIS_AUTO_IMPORT_FLAG)
    ]


def _ensure_arcgis_organization(context: Context, portal_id: str, title: str, description: str) -> str:
    existing = model.Group.get(portal_id)
    if existing and existing.is_organization:
        return portal_id

    base_name = _slugify_ascii(title)
    if base_name:
        existing_by_name = model.Group.by_name(base_name)
        if existing_by_name and existing_by_name.is_organization:
            return existing_by_name.id

    if base_name:
        name = base_name
        if model.Group.by_name(name):
            suffix = portal_id[:6] if portal_id else "portal"
            name = f"{name}-{suffix}"
    else:
        suffix = portal_id[:6] if portal_id else "portal"
        name = f"portal-{suffix}"

    org_data = {
        "id": portal_id,
        "name": name,
        "title": title,
        "description": description or "",
    }
    org_context = logic.fresh_context(context)
    logic.check_access("organization_create", org_context, data_dict=org_data)
    logic.get_action("organization_create")(org_context, org_data)
    return portal_id


def _requests_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=6, connect=0, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


def _fetch_json(
    session: requests.Session,
    url: str,
    params: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    request_timeout = timeout if isinstance(timeout, tuple) else (5, timeout)
    response = get_with_fast_fail(session.get, url, params=params, timeout=request_timeout)
    response.raise_for_status()
    return response.json()


def _search_hub_sites_by_terms(session: requests.Session, arcgis_root: str, terms: List[str], max_items: int = 10000) -> List[Dict[str, Any]]:
    or_terms = _build_or_terms(terms)
    query = f'type:"Hub Site Application" AND access:public AND {or_terms}'

    results: List[Dict[str, Any]] = []
    start = 1

    while True:
        if len(results) >= max_items:
            break
        params = {
            "f": "json",
            "q": query,
            "num": "100",
            "start": str(start),
            "sortField": "modified",
            "sortOrder": "desc",
        }
        data = _fetch_json(session, f"{arcgis_root}/sharing/rest/search", params=params)
        for item in data.get("results", []):
            if item.get("type") != "Hub Site Application":
                continue
            results.append(item)
        next_start = data.get("nextStart")
        if not next_start or next_start <= 0:
            break
        if next_start > 10000:
            break
        start = next_start

    return results


def _fetch_portal_name(session: requests.Session, arcgis_root: str, org_id: str) -> Optional[str]:
    try:
        data = _fetch_json(session, f"{arcgis_root}/sharing/rest/portals/{org_id}", params={"f": "json"})
        return data.get("portalName") or data.get("name")
    except Exception:
        return None


def _count_importable_datasets(datasets: List[Dict[str, Any]]) -> int:
    service_item_ids: set[str] = set()
    for dataset in datasets:
        attributes = dataset.get("attributes") or {}
        item_id = attributes.get("itemId") or dataset.get("id")
        if attributes.get("type") == "Feature Service" and item_id:
            service_item_ids.add(item_id)

    count = 0
    for dataset in datasets:
        attributes = dataset.get("attributes") or {}
        if attributes.get("access") != "public":
            continue
        item_id = attributes.get("itemId") or dataset.get("id")
        if attributes.get("type") == "Feature Layer" and item_id in service_item_ids:
            continue
        count += 1
    return count


def _fetch_all_datasets_for_count(
    session: requests.Session, base_url: str, group_ids: List[str], page_size: int = 100
) -> List[Dict[str, Any]]:
    datasets: List[Dict[str, Any]] = []
    page_number = 1
    while True:
        params = {
            "page[size]": str(page_size),
            "page[number]": str(page_number),
        }
        if group_ids:
            params["filter[groupIds]"] = f"any({','.join(group_ids)})"
        data = _fetch_json(
            session,
            f"{base_url}/api/v3/datasets",
            params=params,
            timeout=10,
        )
        result_datasets = data.get("data", [])
        if not result_datasets:
            break
        datasets.extend(result_datasets)
        next_link = data.get("links", {}).get("next")
        if not next_link:
            break
        page_number += 1
    return datasets


def _fetch_dataset_count(session: requests.Session, base_url: str, *, accurate: bool = True) -> Optional[int]:
    if not base_url:
        return None
    try:
        group_ids = get_site_scope_group_ids(base_url)
    except Exception as e:
        log.warning("Skipping dataset count for %s due to site scope error: %s", base_url, e)
        return 0
    try:
        if not group_ids:
            return 0
        if not accurate:
            params = {"page[size]": "1", "filter[groupIds]": f"any({','.join(group_ids)})"}
            log.debug(f"Fetching fast dataset count from {base_url} with groups: {group_ids}")
            data = _fetch_json(
                session,
                f"{base_url}/api/v3/datasets",
                params=params,
                timeout=10,
            )
            total = (
                data.get("meta", {})
                .get("stats", {})
                .get("totalCount")
            )
            if total is None:
                total = data.get("meta", {}).get("total")
            if total is None:
                return 0
            try:
                return int(total)
            except (TypeError, ValueError):
                return 0
        log.debug(f"Fetching datasets for accurate count from {base_url} with groups: {group_ids}")
        datasets = _fetch_all_datasets_for_count(session, base_url, group_ids)
    except Exception as e:
        log.warning("Failed to fetch dataset count from %s: %s", base_url, e)
        return 0

    return _count_importable_datasets(datasets)


def _score_candidate(item: Dict[str, Any], portal_name: Optional[str], terms: List[str]) -> Dict[str, Any]:
    tags_text = _normalize_text(" ".join(item.get("tags") or []))
    title_text = _normalize_text(item.get("title") or "")
    snippet_text = _normalize_text(item.get("snippet") or "")
    description_text = _normalize_text(item.get("description") or "")
    portal_text = _normalize_text(portal_name or "")

    matched = []
    reasons = []
    score = 0
    for term in terms:
        t = _normalize_text(term)
        hit_in_tags = t in tags_text
        hit_in_title = t in title_text
        hit_in_description = t in description_text
        hit_in_snippet = t in snippet_text
        hit_in_portal = t in portal_text
        if hit_in_tags or hit_in_title or hit_in_description or hit_in_snippet or hit_in_portal:
            matched.append(term)
        if hit_in_tags:
            score += 3
            reasons.append(f"tag: {term}")
        if hit_in_title:
            score += 2
            reasons.append(f"title: {term}")
        if hit_in_description:
            score += 2
            reasons.append(f"description: {term}")
        if hit_in_snippet:
            score += 1
            reasons.append(f"snippet: {term}")
        if hit_in_portal:
            score += 2
            reasons.append(f"portal: {term}")

    return {
        "score": score,
        "matched_terms": _unique_strings(matched),
        "match_reasons": _unique_strings(reasons),
    }


CANADA_BBOX = (-141.0, 41.7, -52.0, 83.5)


def _extent_to_bbox(extent: Any) -> Optional[Tuple[float, float, float, float]]:
    if isinstance(extent, dict):
        try:
            return (
                float(extent.get("xmin")),
                float(extent.get("ymin")),
                float(extent.get("xmax")),
                float(extent.get("ymax")),
            )
        except (TypeError, ValueError):
            return None
    if isinstance(extent, list) and len(extent) == 2:
        try:
            minx, miny = extent[0]
            maxx, maxy = extent[1]
            return (float(minx), float(miny), float(maxx), float(maxy))
        except (TypeError, ValueError):
            return None
    return None


def _extent_overlaps_canada(extent: Any) -> bool:
    bbox = _extent_to_bbox(extent)
    if not bbox:
        return True
    minx, miny, maxx, maxy = bbox
    if any(abs(v) > 180 for v in (minx, maxx)) or any(abs(v) > 90 for v in (miny, maxy)):
        return True
    # Heuristic: exclude extents entirely south of ~48N and west of ~95W (likely US Pacific/Midwest).
    if maxy < 48.0 and maxx < -95.0:
        return False
    cminx, cminy, cmaxx, cmaxy = CANADA_BBOX
    if maxx < cminx or minx > cmaxx or maxy < cminy or miny > cmaxy:
        return False
    centroid_x = (minx + maxx) / 2.0
    centroid_y = (miny + maxy) / 2.0
    if not (cminx <= centroid_x <= cmaxx and cminy <= centroid_y <= cmaxy):
        return False
    return True


@logic.side_effect_free
def arcgis_hub_portal_discovery(context: Context, data_dict: Dict[str, Any]):
    """
    Discover ArcGIS Hub/GeoHub public sites related to Canada keywords.

    Optional params:
        arcgis_root: override ArcGIS root (default https://www.arcgis.com)
        concurrency: portal name lookup concurrency (default 12)
    """
    user = context["user"]

    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    if data_dict is None:
        data_dict = {}

    arcgis_root = data_dict.get("arcgis_root") or "https://www.arcgis.com"
    concurrency = int(data_dict.get("concurrency") or 6)

    cached_payload = _load_portal_cache()
    cached_results = cached_payload.get("results") or []
    cached_by_id = {item.get("id"): item for item in cached_results if item.get("id")}
    cached_by_url = {item.get("url"): item for item in cached_results if item.get("url")}
    cached_counts_updated_at = cached_payload.get("counts_updated_at")

    session = _requests_session()
    groups = _load_keyword_groups()
    raw_by_id: Dict[str, Dict[str, Any]] = {}

    for group in groups:
        items = _search_hub_sites_by_terms(session, arcgis_root, group["terms"])
        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            raw_by_id[item_id] = item

    org_ids = _unique_strings(
        [
            item.get("orgid") or item.get("orgId")
            for item in raw_by_id.values()
            if (item.get("orgid") or item.get("orgId"))
        ]
    )

    portal_name_by_org: Dict[str, Optional[str]] = {}
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(_fetch_portal_name, session, arcgis_root, org_id): org_id for org_id in org_ids
        }
        for future in as_completed(futures):
            org_id = futures[future]
            portal_name_by_org[org_id] = future.result()

    all_terms = _unique_strings([term for group in groups for term in group["terms"]])
    candidates_by_url: Dict[str, Dict[str, Any]] = {}

    for item in raw_by_id.values():
        url = item.get("url") or ""
        if not url:
            continue
        extent = item.get("extent") or item.get("orgExtent")
        if extent and not _extent_overlaps_canada(extent):
            continue
        org_id = item.get("orgid") or item.get("orgId") or ""
        portal_name = portal_name_by_org.get(org_id)
        score_info = _score_candidate(item, portal_name, all_terms)

        candidate = {
            "id": item.get("id"),
            "title": item.get("title") or "",
            "url": url,
            "orgId": org_id,
            "tags": item.get("tags") or [],
            "snippet": item.get("snippet") or "",
            "description": item.get("description") or "",
            "matchedTerms": score_info["matched_terms"],
            "matchReasons": score_info["match_reasons"],
            "score": score_info["score"],
            "portalName": portal_name,
            "raw": item,
        }
        cached = cached_by_id.get(candidate["id"]) or cached_by_url.get(url)
        if cached:
            if cached.get("datasetCount") is not None:
                candidate["datasetCount"] = cached.get("datasetCount")
            if cached.get("countsUpdatedAt"):
                candidate["countsUpdatedAt"] = cached.get("countsUpdatedAt")

        existing = candidates_by_url.get(url)
        if not existing or candidate["score"] > existing["score"]:
            candidates_by_url[url] = candidate

    final_list = sorted(candidates_by_url.values(), key=lambda x: x["score"], reverse=True)
    payload = {
        "total": len(final_list),
        "arcgis_root": arcgis_root,
        "results": final_list,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if cached_counts_updated_at:
        payload["counts_updated_at"] = cached_counts_updated_at
    set_system_info(ARCGIS_PORTAL_CACHE_KEY, json.dumps(payload, ensure_ascii=True))
    return payload


@logic.side_effect_free
def arcgis_hub_portal_discovery_get(context: Context, data_dict: Dict[str, Any]):
    """
    Get cached ArcGIS Hub/GeoHub discovery results.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    cached = get_system_info(ARCGIS_PORTAL_CACHE_KEY)
    if not cached:
        return {"total": 0, "arcgis_root": "https://www.arcgis.com", "results": [], "updated_at": None}
    try:
        return json.loads(cached)
    except ValueError:
        return {"total": 0, "arcgis_root": "https://www.arcgis.com", "results": [], "updated_at": None}


def arcgis_hub_portal_discovery_counts(context: Context, data_dict: Dict[str, Any]):
    """
    Fetch dataset counts for cached portal discovery results.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    if data_dict is None:
        data_dict = {}

    portal_ids = data_dict.get("portal_ids") or []
    if portal_ids and not isinstance(portal_ids, list):
        raise logic.ValidationError({"portal_ids": ["Provide a list of portal ids."]})

    cached = get_system_info(ARCGIS_PORTAL_CACHE_KEY)
    if not cached:
        return {"total": 0, "arcgis_root": "https://www.arcgis.com", "results": [], "updated_at": None}

    payload = json.loads(cached)
    results = payload.get("results") or []
    portal_map = {item.get("id"): item for item in results if item.get("id")}

    target_ids = portal_ids or list(portal_map.keys())
    if not target_ids:
        return payload

    session = _requests_session()
    concurrency = int(data_dict.get("concurrency") or 6)
    count_mode = (data_dict.get("count_mode") or "accurate").lower()
    accurate_counts = count_mode != "fast"

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {}
        for portal_id in target_ids:
            candidate = portal_map.get(portal_id)
            if not candidate:
                continue
            base_url = _build_base_api(candidate.get("url") or "")
            if not base_url:
                continue
            futures[executor.submit(_fetch_dataset_count, session, base_url, accurate=accurate_counts)] = portal_id

        for future in as_completed(futures):
            portal_id = futures[future]
            try:
                count = future.result()
            except Exception as e:
                log.warning("Skipping dataset count for portal %s due to error: %s", portal_id, e)
                continue
            if count is None:
                continue
            candidate = portal_map.get(portal_id)
            if candidate is not None:
                candidate["datasetCount"] = count
                candidate["countsUpdatedAt"] = datetime.now(timezone.utc).isoformat()

    payload["results"] = results
    payload["counts_updated_at"] = datetime.now(timezone.utc).isoformat()
    set_system_info(ARCGIS_PORTAL_CACHE_KEY, json.dumps(payload, ensure_ascii=True))
    return payload


@logic.side_effect_free
def arcgis_hub_portal_discovery_config_get(context: Context, data_dict: Dict[str, Any]):
    """
    Get keyword group configuration for ArcGIS Hub portal discovery.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    cached = get_system_info(ARCGIS_PORTAL_CONFIG_KEY)
    if not cached:
        return {"keyword_groups": _canada_keyword_groups(), "updated_at": None}
    try:
        payload = json.loads(cached)
    except ValueError:
        return {"keyword_groups": _canada_keyword_groups(), "updated_at": None}

    groups = _normalize_keyword_groups(payload.get("keyword_groups"))
    if not groups:
        groups = _canada_keyword_groups()
    return {"keyword_groups": groups, "updated_at": payload.get("updated_at")}


@logic.side_effect_free
def arcgis_hub_portal_discovery_config_default(context: Context, data_dict: Dict[str, Any]):
    """
    Get the default keyword groups for ArcGIS Hub portal discovery.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    return {"keyword_groups": _canada_keyword_groups(), "updated_at": None}


def arcgis_hub_portal_discovery_config_update(context: Context, data_dict: Dict[str, Any]):
    """
    Update keyword group configuration for ArcGIS Hub portal discovery.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    if data_dict is None:
        data_dict = {}

    groups = data_dict.get("keyword_groups")
    if not isinstance(groups, list):
        raise logic.ValidationError({"keyword_groups": ["Must be a list of group objects."]})

    normalized = _normalize_keyword_groups(groups)
    if not normalized:
        raise logic.ValidationError({"keyword_groups": ["Provide at least one group with terms."]})

    payload = {
        "keyword_groups": normalized,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    set_system_info(ARCGIS_PORTAL_CONFIG_KEY, json.dumps(payload, ensure_ascii=True))
    return payload


@logic.side_effect_free
def arcgis_auto_import_configs_get(context: Context, data_dict: Dict[str, Any]):
    """
    List auto-generated ArcGIS import configs with portal metadata.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    portal_cache = _load_portal_cache()
    portal_results = portal_cache.get("results") or []
    portal_map = {item.get("id"): item for item in portal_results if item.get("id")}
    counts_updated_at = portal_cache.get("counts_updated_at")
    has_portal_cache = bool(portal_results)

    configs = _auto_arcgis_configs()
    config_ids = [config.id for config in configs]
    last_run_by_config: Dict[str, Optional[str]] = {}
    if config_ids:
        rows = (
            model.Session.query(CUDCImportJob.import_config_id, func.max(CUDCImportJob.run_at))
            .filter(CUDCImportJob.import_config_id.in_(config_ids))
            .group_by(CUDCImportJob.import_config_id)
            .all()
        )
        last_run_by_config = {
            config_id: run_at.isoformat() if run_at else None for config_id, run_at in rows
        }

    results = []
    for config in configs:
        item = config.as_dict()
        item["last_run_at"] = last_run_by_config.get(config.id)
        portal_id = (config.other_config or {}).get("portal_id")
        portal_snapshot = (config.other_data or {}).get("portal_snapshot") or {}
        cached_snapshot = portal_map.get(portal_id) if portal_id else None
        discoverable = bool(cached_snapshot) if has_portal_cache else None
        dataset_count = None
        portal_counts_updated_at = None
        if cached_snapshot:
            dataset_count = cached_snapshot.get("datasetCount")
            portal_counts_updated_at = cached_snapshot.get("countsUpdatedAt")
        if dataset_count is None and isinstance(portal_snapshot, dict):
            dataset_count = portal_snapshot.get("datasetCount")
        if portal_counts_updated_at is None and isinstance(portal_snapshot, dict):
            portal_counts_updated_at = portal_snapshot.get("countsUpdatedAt")

        if isinstance(portal_snapshot, dict) and dataset_count is not None:
            portal_snapshot = dict(portal_snapshot)
            portal_snapshot["datasetCount"] = dataset_count
            if portal_counts_updated_at:
                portal_snapshot["countsUpdatedAt"] = portal_counts_updated_at

        item["portal_snapshot"] = portal_snapshot
        item["datasetCount"] = dataset_count
        item["countsUpdatedAt"] = portal_counts_updated_at
        item["discoverable"] = discoverable
        results.append(item)
    return {"total": len(results), "results": results, "counts_updated_at": counts_updated_at}


def arcgis_auto_import_configs_create(context: Context, data_dict: Dict[str, Any]):
    """
    Create auto-generated ArcGIS import configs for selected portal ids.
    """
    model_obj = context["model"]
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    if data_dict is None:
        data_dict = {}

    portal_ids = data_dict.get("portal_ids") or []
    if not isinstance(portal_ids, list) or not portal_ids:
        raise logic.ValidationError({"portal_ids": ["Provide a list of portal ids."]})

    portal_cache = _load_portal_cache()
    portal_results = portal_cache.get("results") or []
    portal_map = {item.get("id"): item for item in portal_results if item.get("id")}

    created: List[Dict[str, Any]] = []
    skipped: List[Tuple[str, str]] = []
    errors: List[Tuple[str, str]] = []

    userobj = model_obj.User.get(user)
    if not userobj:
        raise logic.ValidationError("User not found.")

    existing_map = {
        (config.other_config or {}).get("portal_id"): config
        for config in _auto_arcgis_configs()
    }
    supported_langs = get_udc_langs()

    for portal_id in portal_ids:
        if not isinstance(portal_id, str) or not portal_id:
            errors.append((str(portal_id), "Invalid portal id."))
            continue

        existing = existing_map.get(portal_id)
        if existing:
            skipped.append((portal_id, existing.id))
            continue

        portal = portal_map.get(portal_id)
        if not portal:
            errors.append((portal_id, "Portal not found in cached discovery results."))
            continue
        dataset_count = portal.get("datasetCount")
        try:
            if dataset_count is not None and int(dataset_count) == 0:
                skipped.append((portal_id, "Zero datasets (skipped)."))
                continue
        except (TypeError, ValueError):
            pass

        title = portal.get("title") or portal.get("portalName") or "ArcGIS Portal"
        url = portal.get("url") or ""
        description = portal.get("snippet") or portal.get("description") or ""
        portal_raw = portal.get("raw") or {}
        culture = portal_raw.get("culture") or portal.get("culture")
        language = _normalize_language(culture, supported_langs)
        base_api = _build_base_api(url)
        if not base_api:
            errors.append((portal_id, "Failed to derive base API from portal URL."))
            continue

        name_prefix = _name_prefix_from_title(title, portal_id)
        class_name = _class_name_from_title(title, portal_id)
        code = _build_import_code(url, class_name, name_prefix, title, language)

        owner_org = _ensure_arcgis_organization(context, portal_id, title, description)

        other_config = {
            "base_api": base_api,
            ARCGIS_AUTO_IMPORT_FLAG: True,
            "portal_id": portal_id,
            "portal_title": title,
            "portal_url": url,
            "name_prefix": name_prefix,
            "source_portal": title,
        }
        if language:
            other_config["language"] = language
        other_data = {
            "portal_snapshot": portal,
        }

        new_config = CUDCImportConfig(
            created_by=userobj.id,
            name=title,
            notes="Auto-generated from ArcGIS portal discovery.",
            code=code,
            platform="arcgis",
            owner_org=owner_org,
            other_config=other_config,
            other_data=other_data,
            stop_on_error=False,
        )
        model.Session.add(new_config)
        model.Session.commit()
        created.append(new_config.as_dict())

    return {"created": created, "skipped": skipped, "errors": errors}


def arcgis_auto_import_configs_delete(context: Context, data_dict: Dict[str, Any]):
    """
    Delete auto-generated ArcGIS import configs by id.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    if data_dict is None:
        data_dict = {}

    config_ids = data_dict.get("config_ids") or []
    if not isinstance(config_ids, list) or not config_ids:
        raise logic.ValidationError({"config_ids": ["Provide a list of config ids."]})

    deleted: List[str] = []
    skipped: List[Tuple[str, str]] = []
    blocked: List[Dict[str, Any]] = []

    for config_id in config_ids:
        config = CUDCImportConfig.get(config_id)
        if not config:
            skipped.append((str(config_id), "Config not found."))
            continue
        other_config = config.other_config or {}
        if not other_config.get(ARCGIS_AUTO_IMPORT_FLAG):
            skipped.append((config_id, "Not an auto ArcGIS import config."))
            continue
        try:
            imported_ids = get_package_ids_by_import_config_id(context, config.id)
            imported_count = len(imported_ids)
        except Exception as exc:
            log.exception("Failed to check imported datasets for config %s", config.id)
            blocked.append(
                {
                    "id": config_id,
                    "imported_count": None,
                    "owner_org": config.owner_org,
                    "reason": f"Failed to check imported datasets: {exc}",
                }
            )
            continue
        if imported_count > 0:
            blocked.append(
                {
                    "id": config_id,
                    "imported_count": imported_count,
                    "owner_org": config.owner_org,
                }
            )
            continue
        CUDCImportConfig.delete_by_id(config_id)
        deleted.append(config_id)

    model.Session.commit()
    return {"deleted": deleted, "skipped": skipped, "blocked": blocked}
