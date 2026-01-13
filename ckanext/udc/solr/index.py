from __future__ import annotations
from typing import Union, Any
import json
import logging
import ckan.plugins.toolkit as tk
import ckan.plugins as plugins
from .config import get_udc_langs

log = logging.getLogger(__name__)


def _jsonish(v):
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return None


def _tag_names(core_tags):
    out = []
    for t in core_tags or []:
        if isinstance(t, dict) and t.get("name"):
            out.append(t["name"])
        elif isinstance(t, str):
            out.append(t)
    return out


def _safe_json_load(value: Any) -> Any:
    """Parse JSON from a string, or pass through dict / list / None.

    If parsing fails, return None rather than raising.
    """
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return None


def _extract_version_single(raw: Any) -> dict[str, Any] | None:
    """Normalize a single version JSON object.

    Expected shape (best-effort): {"url": str, "title": str, "description": str}.
    Accept bare strings (treated as url) and dicts with at least url or title.
    """
    # Already a dict with something useful
    if isinstance(raw, dict):
        url = raw.get("url") or raw.get("href") or ""
        title = raw.get("title") or ""
        desc = raw.get("description") or raw.get("notes") or ""
        if not (url or title or desc):
            return None
        out: dict[str, Any] = {}
        if url:
            out["url"] = url
        if title:
            out["title"] = title
        if desc:
            out["description"] = desc
        return out or None

    # Bare string -> treat as URL
    if isinstance(raw, str) and raw.strip():
        return {"url": raw.strip()}

    return None


def _extract_version_list(raw: Any) -> list[dict[str, Any]]:
    """Normalize list-like version field into a list of objects."""
    if raw is None:
        return []
    if isinstance(raw, str):
        parsed = _safe_json_load(raw)
    else:
        parsed = raw

    items: list[dict[str, Any]] = []
    if isinstance(parsed, list):
        for item in parsed:
            norm = _extract_version_single(item)
            if norm:
                items.append(norm)
    else:
        norm = _extract_version_single(parsed)
        if norm:
            items.append(norm)
    return items


def before_dataset_index(pkg_dict: dict[str, Any]) -> dict[str, Any]:
    
    log.info("Running before_dataset_index hook")
    log.info("Original document: %s", json.dumps(pkg_dict, indent=2, ensure_ascii=True))

    # Get the UDC plugin instance
    udcPlugin = plugins.get_plugin('udc')
    
    # Make a shallow copy so we don't mutate CKAN's original
    index = dict(pkg_dict)
    
    # Do not index related packages
    index.pop("related_packages", None)

    langs = get_udc_langs()
    default_lang = langs[0]

    # multiple_select -> extras_<name> (array)
    for field in udcPlugin.multiple_select_fields or []:
        if field in index and isinstance(index[field], str):
            index["extras_" + field] = [v for v in index[field].split(",") if v.strip()]

    # CORE: title / notes translated
    title_t = _jsonish(index.get("title_translated")) or {}
    notes_t = _jsonish(index.get("notes_translated")) or {}
    if default_lang not in title_t and isinstance(index.get("title"), str):
        title_t[default_lang] = index["title"]
    if default_lang not in notes_t and isinstance(index.get("notes"), str):
        notes_t[default_lang] = index["notes"]

    for L in langs:
        v = title_t.get(L)
        if isinstance(v, str) and v.strip():
            index[f"title_{L}_txt"] = v
        v = notes_t.get(L)
        if isinstance(v, str) and v.strip():
            index[f"notes_{L}_txt"] = v

    # tags translated -> facet (and partial text search)
    # Build tags_translated from provided JSON or seed from core tags for default_lang
    tags_t = _jsonish(index.get("tags_translated")) or {}
    if default_lang not in tags_t:
        core_tags = _tag_names(index.get("tags"))
        if core_tags:
            tags_t[default_lang] = core_tags

    for L in langs:
        arr = tags_t.get(L) or []
        if isinstance(arr, str):
            arr = [arr]
        arr = [a for a in arr if isinstance(a, str) and a.strip()]
        if arr:
            index[f"tags_{L}_f"] = arr
            # Make tags searchable per language:
            index[f"tags_{L}_txt"] = " ".join(arr)

    # maturity model TEXT fields (multilingual JSON in-place)

    for name in udcPlugin.text_fields:
        raw = index.get(name)
        if raw is None and f"extras_{name}" in index:
            raw = index.get(f"extras_{name}")
        obj = _jsonish(raw) or {}
        # Prevent JSON from going into 'extras_*' (default schema would copy to 'text')
        index.pop(f"extras_{name}", None)

         # Write language-aware text & facets
        for L in langs:
            v = obj.get(L)
            if isinstance(v, str) and v.strip():
                index[f"{name}_{L}_txt"] = v
                index[f"{name}_{L}_f"] = [v]

    # Version relationship fields
    # ----------------------------
    # These are stored canonically as JSON in extras `version_dataset`
    # and `dataset_versions`. At index-time we derive URL-only and
    # label fields suitable for filtering and display in facets/search.

    # Drop raw extras to avoid indexing schema conflicts.
    index.pop("extras_version_dataset", None)
    index.pop("extras_dataset_versions", None)

    # Single "is version of" target
    raw_version_dataset = index.get("version_dataset")
    vd_obj: dict[str, Any] | None = None
    if raw_version_dataset is not None:
        parsed = _safe_json_load(raw_version_dataset)
        vd_obj = _extract_version_single(parsed)

    version_dataset_url_val = None
    version_dataset_label_val = None
    if vd_obj:
        url = vd_obj.get("url") or ""
        title = vd_obj.get("title") or ""
        desc = vd_obj.get("description") or ""

        if url:
            version_dataset_url_val = url
        # Title for label: prefer explicit, otherwise fall back to description
        label_title = title or desc or ""
        if version_dataset_url_val and label_title:
            version_dataset_label_val = f"{label_title} ({version_dataset_url_val})"

    if version_dataset_url_val:
        index["version_dataset_url"] = version_dataset_url_val
    if version_dataset_label_val:
        index["version_dataset_title_url"] = version_dataset_label_val

    # Multiple "has version" targets
    raw_dataset_versions = index.get("dataset_versions")
    dv_list = _safe_json_load(raw_dataset_versions)
    dv_items = _extract_version_list(dv_list)

    urls: list[str] = []
    labels: list[str] = []
    for item in dv_items:
        url = item.get("url") or ""
        title = item.get("title") or ""
        desc = item.get("description") or ""
        if not (url or title or desc):
            continue
        if url:
            urls.append(url)
        label_title = title or desc or ""
        if url and label_title:
            labels.append(f"{label_title} ({url})")

    if urls:
        index["dataset_versions_url"] = urls
    if labels:
        index["dataset_versions_title_url"] = labels


    # Pretty-print the final indexed document for debugging
    log.info("Indexed document: %s", json.dumps(index, indent=2, ensure_ascii=True))

    return index
