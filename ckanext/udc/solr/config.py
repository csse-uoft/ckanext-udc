from __future__ import annotations
import logging
from typing import Union

from ckan.plugins.toolkit import config
from ckan.lib.search.common import SolrSettings
import ckan.lib.helpers as h

log = logging.getLogger(__name__)


def get_udc_langs():
    # read dataset languages, ensure default locale is included
    default_lang = config.get("ckan.locale_default", "en") or "en"
    raw_langs = config.get("udc.multilingual.languages", default_lang)

    # normalize and keep original order
    langs = [l.strip() for l in raw_langs.split() if l.strip()]

    # deduplicate while preserving order
    seen = set()
    ordered_langs = []
    for lang in langs:
        if lang not in seen:
            ordered_langs.append(lang)
            seen.add(lang)

    # ensure default language is first
    remaining_langs = [lang for lang in ordered_langs if lang != default_lang]
    return [default_lang] + remaining_langs

def get_default_lang():
    """Get the default language from the config, defaulting to 'en'."""
    return config.get("ckan.locale_default", "en") or "en"


def get_current_lang():
    """Get the current language from the request context or default to 'en'."""
    lang = h.lang()
    if not lang:
        lang = config.get("ckan.locale_default", "en") or "en"
    return lang


def pick_locale(texts: Union[str, dict], lang: str = None) -> str:
    """Pick the text in the specified language from a dict of texts.

    If texts is a string, return it directly.
    If texts is a dict, return the text in the specified language if available,
    otherwise return the first text in the dict.
    """
    if not lang:
        lang = h.lang() or "en"
    if isinstance(texts, str):
        return texts
    elif isinstance(texts, dict):
        if lang in texts:
            return texts[lang]
        elif "en" in texts:
            return texts["en"]
        elif len(texts) > 0:
            return list(texts.values())[0]
    return ""


def pick_locale_with_fallback(texts: Union[str, dict], lang: str = None) -> tuple:
    """Pick the text in the specified language from a dict of texts with fallback chain.

    Returns a tuple of (text, actual_lang_used) where actual_lang_used is None if
    the requested language was used, or the language code if a fallback was used.

    If texts is a string, return (texts, None).
    If texts is a dict, try requested language, then follow the precedence order
    from get_udc_langs(). Empty strings are treated as missing values.
    """
    if not lang:
        lang = h.lang() or get_default_lang()
    
    if isinstance(texts, str):
        return (texts, None)
    
    if not isinstance(texts, dict):
        return ("", None)
    
    # Helper to check if value is non-empty
    def is_non_empty(val):
        if val is None:
            return False
        if isinstance(val, str) and not val.strip():
            return False
        if isinstance(val, (list, dict)) and not val:
            return False
        return True
    
    # If requested language exists and is non-empty, return it with None (no fallback)
    if lang in texts and is_non_empty(texts[lang]):
        return (texts[lang], None)
    
    # Otherwise, try fallback languages in order
    lang_order = get_udc_langs()
    for fallback_lang in lang_order:
        if fallback_lang in texts and is_non_empty(texts[fallback_lang]):
            # Return the value and the language code used
            return (texts[fallback_lang], fallback_lang)
    
    # Last resort: return any available non-empty value
    for k, v in texts.items():
        if is_non_empty(v):
            return (v, k)
    
    return ("", None)
