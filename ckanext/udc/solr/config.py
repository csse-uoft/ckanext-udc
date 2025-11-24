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
