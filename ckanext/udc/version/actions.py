from __future__ import annotations

import logging
from typing import Any, Dict

from bs4 import BeautifulSoup  # type: ignore

import ckan.logic as logic
from ckan.types import Context
from ckan.common import _, config
from ckan.lib.navl.dictization_functions import DataError

import requests

log = logging.getLogger(__name__)


def _scrape_html_title_description(url: str) -> Dict[str, str]:
    """Best-effort scrape of <title> and a description from an HTML page.

    This is intentionally simple and defensive: it fetches the URL with a
    short timeout, parses HTML with BeautifulSoup if available, and tries
    to extract:

      - <title>
      - <meta name="description"> or <meta property="og:description">

    Any errors result in an empty dict.
    """
    headers = {
        "User-Agent": config.get(
            "udc.version_meta.user_agent",
            "CKAN-UDC-VersionMeta/1.0 (+https://ckan.org)",
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        log.warning("udc_version_meta: error fetching %s: %s", url, e)
        return {}

    content_type = resp.headers.get("Content-Type", "")
    if "html" not in content_type.lower():
        return {}

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:  # pragma: no cover - extremely unlikely
        log.warning("udc_version_meta: error parsing HTML from %s: %s", url, e)
        return {}

    title = ""
    desc = ""

    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if meta_desc:
        desc = meta_desc.get("content") or ""
        desc = desc.strip()

    out: Dict[str, str] = {}
    if title:
        out["title"] = title
    if desc:
        out["description"] = desc
    return out


def _extract_cudc_dataset_name(url: str) -> str | None:
    """Extract dataset name from a CUDC catalogue URL if possible.

    Expected forms include:
      - /catalogue/<name>
      - /catalogue/<type>/<name>
    """

    try:
        from urllib.parse import urlparse
    except Exception:  # pragma: no cover
        return None

    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    # find 'catalogue' segment and take the following as name (or the next)
    for idx, part in enumerate(parts):
        if part == "catalogue" and idx + 1 < len(parts):
            # If there are two segments after 'catalogue', the last one is likely the dataset
            if idx + 2 < len(parts):
                return parts[idx + 2]
            return parts[idx + 1]
    return None


def udc_version_meta(context: Context, data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Return title/description for a dataset-like URL.

    For CUDC catalogue URLs, resolve via CKAN's package_show.
    For other URLs, perform a lightweight HTML scrape.
    """

    url = (data_dict.get("url") or "").strip()
    if not url:
        raise logic.ValidationError({"url": [_("Missing url")]})

    # Optional: require logged-in user
    user = context.get("user")
    if not user:
        raise logic.NotAuthorized(_("You must be logged in to use this action"))

    # 1) Try to resolve CUDC catalogue entries via package_show
    result: Dict[str, Any] = {}
    if "/catalogue/" in url:
        name = _extract_cudc_dataset_name(url)
        if name:
            try:
                pkg = logic.get_action("package_show")(context, {"id": name})
                title = pkg.get("title") or pkg.get("name") or ""
                desc = pkg.get("summary") or pkg.get("notes") or ""
                if title:
                    result["title"] = title
                if desc:
                    result["description"] = desc
            except logic.NotFound:
                log.info("udc_version_meta: package %s not found for url %s", name, url)
            except Exception as e:
                log.warning(
                    "udc_version_meta: error resolving package %s for url %s: %s",
                    name,
                    url,
                    e,
                )

    # 2) If nothing yet, and allowed by config, scrape the URL
    if not result:
        allow_scrape = config.get("udc.version_meta.scrape", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        if allow_scrape:
            scraped = _scrape_html_title_description(url)
            if scraped:
                result.update(scraped)

    return result
