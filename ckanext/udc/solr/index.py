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


    # Pretty-print the final indexed document for debugging
    log.info("Indexed document: %s", json.dumps(index, indent=2, ensure_ascii=True))

    return index
