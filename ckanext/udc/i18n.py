from __future__ import annotations
import json
import logging
from typing import Dict, List, Any
import ckan.plugins.toolkit as tk
from ckan.lib.navl.dictization_functions import Missing, missing

log = logging.getLogger(__name__)


def _is_missing(v):
    return v is missing or isinstance(v, Missing) or v is None or v == ""


def udc_lang_object(value, context):
    """
    Validate a localized string object: {lang: "text", ...}
    Accepts missing/None/'' (returns None).
    Accepts a plain string by coercing to {default_lang: string}.
    """
    if _is_missing(value):
        return None
    if isinstance(value, str):
        # Coerce a bare string to the default locale
        default_lang = tk.config.get("ckan.locale_default", "en") or "en"
        return {default_lang: value}
    if not isinstance(value, dict):
        raise tk.Invalid("Expected an object of {lang: string} for localized text.")
    # Validate entries
    for k, v in list(value.items()):
        if _is_missing(v):
            value.pop(k, None)
        elif not isinstance(v, str):
            raise tk.Invalid("Localized text values must be strings.")
    if not value:
        return None
    # Ensure default language exists by seeding from any available value
    default_lang = tk.config.get("ckan.locale_default", "en") or "en"
    if default_lang not in value:
        # pick one existing language to seed default
        first = next(iter(value.values()))
        if isinstance(first, str) and first.strip():
            value[default_lang] = first
    return value


def udc_json_dump(value, context):
    """
    If value is dict/list, dump to JSON string.
    If already a string or missing/empty, pass through.
    """
    if _is_missing(value):
        return None
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            log.debug("udc_json_dump: could not dump (leaving as-is): %r", value)
            return value
    return value


def udc_json_load(value, context):
    """
    If value is a JSON string, parse to Python object.
    If already a dict/list, return as-is.
    If missing/empty, return None (so ignore_missing upstream/downstream can skip).
    Never raise on CKAN Missing; no spurious warnings.
    """
    if _is_missing(value):
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            # Soft-fail: leave it as-is so subsequent validators can decide.
            log.debug("udc_json_load: not JSON (leaving as-is): %r", value)
            return value
    # Unknown type; pass through
    return value


def udc_core_translated_to_extras(core_field: str):
    """
    INPUT: when receiving <core_field>_translated, copy default-locale value into core_field.
    """

    def _copy(value, context):
        if _is_missing(value):
            return None
        # value may be dict or JSON string
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                return value
        if isinstance(value, dict):
            default_lang = tk.config.get("ckan.locale_default", "en") or "en"
            s = value.get(default_lang)
            if isinstance(s, str) and s.strip():
                data = context.get("data") or context.get("data_dict") or {}
                data[core_field] = s
        return value

    return _copy


def udc_set_core_from_translated(core_field: str):
    """
    Output (show) side: if `<core_field>` is empty, fill it from
    `<core_field>_translated[default_lang]`.
    """

    def _output(value, context):
        data = context.get("data") or context.get("data_dict") or {}
        default_lang = tk.config.get("ckan.locale_default", "en")
        translated = data.get(f"{core_field}_translated")
        if (not data.get(core_field)) and isinstance(translated, dict):
            v = translated.get(default_lang)
            if v:
                data[core_field] = v
        return value

    return _output


def udc_lang_string_list(value, context):
    """
    Validate {lang: [string, ...]} (used by tags_translated).
    Missing/empty -> None.
    A single string is coerced to a one-item list.
    """
    if _is_missing(value):
        return None
    if not isinstance(value, dict):
        raise tk.Invalid("Expected an object of {lang: [strings]}")

    out = {}
    for lang, vals in value.items():
        if _is_missing(vals):
            continue
        if isinstance(vals, str):
            vals = [vals]
        if not isinstance(vals, list) or not all(isinstance(x, str) for x in vals):
            raise tk.Invalid(
                'Expected a list of strings for language "{}"'.format(lang)
            )
        # dedupe + strip empties
        seen = set()
        cleaned = []
        for x in vals:
            x = x.strip()
            if x and x not in seen:
                seen.add(x)
                cleaned.append(x)
        if cleaned:
            out[lang] = cleaned
    return out or None


def udc_set_core_tags_from_translated(value, context):
    """
    If data['tags_translated'][default_lang] exists, set core 'tags' accordingly.
    Runs in the tags_translated pipeline and (optionally) in the tags pipeline.
    """
    data = context.get("data") or context.get("data_dict") or {}
    t = data.get("tags_translated")
    # handle Missing / JSON string
    if _is_missing(t):
        return value
    if isinstance(t, str):
        try:
            t = json.loads(t)
        except Exception:
            return value
    if not isinstance(t, dict):
        return value
    default_lang = tk.config.get("ckan.locale_default", "en") or "en"
    names = t.get(default_lang) or []
    if isinstance(names, str):
        names = [names]
    if isinstance(names, list):
        cleaned = []
        seen = set()
        for n in names:
            if isinstance(n, str):
                n = n.strip()
                if n and n not in seen:
                    seen.add(n)
                    cleaned.append({"name": n})
        if cleaned:
            data["tags"] = cleaned
    return value


def udc_fill_tags_translated_from_core(value, context):
    """
    On show: if tags_translated is absent or missing default_lang, seed from core tags.
    """
    data = context.get("data") or context.get("data_dict") or {}
    default_lang = tk.config.get("ckan.locale_default", "en") or "en"
    
    tags_trans = data.get("tags_translated")
    
    # If tags_translated exists and has data for default language, keep it
    if isinstance(tags_trans, dict) and tags_trans and tags_trans.get(default_lang):
        return value
    
    # Otherwise, seed from core tags
    tags = data.get("tags") or []
    names = []
    for t in tags:
        if isinstance(t, dict) and isinstance(t.get("name"), str):
            names.append(t["name"])
        elif isinstance(t, str):
            names.append(t)
    
    if names:
        # If tags_translated exists but is missing default_lang, add it
        if isinstance(tags_trans, dict):
            tags_trans[default_lang] = names
            data["tags_translated"] = tags_trans
        else:
            # Create new tags_translated
            data["tags_translated"] = {default_lang: names}
    
    return value


def udc_seed_translated_from_core(core_field: str):
    """
    INPUT (create/update): if <translated> is empty, seed {default_lang: core} so it gets stored.
    """

    def _seed(value, context):
        if not _is_missing(value) and value:
            return value
        data = context.get("data") or context.get("data_dict") or {}
        core_val = data.get(core_field)
        if isinstance(core_val, str) and core_val.strip():
            default_lang = tk.config.get("ckan.locale_default", "en") or "en"
            return {default_lang: core_val}
        return None

    return _seed


def udc_fill_translated_from_core_on_show(core_field: str):
    """
    SHOW (read): ensure translated_field appears by seeding from core if absent.
    """
    translated_field = core_field + "_translated"

    def _fill(value, context):
        data = context.get("data") or context.get("data_dict") or {}
        tval = data.get(translated_field)
        if isinstance(tval, dict) and tval:
            return value
        core_val = data.get(core_field)
        if isinstance(core_val, str) and core_val.strip():
            default_lang = tk.config.get("ckan.locale_default", "en") or "en"
            data[translated_field] = {default_lang: core_val}
        return value

    return _fill
