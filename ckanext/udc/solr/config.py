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
    langs = config.get("udc.multilingual.languages", default_lang).split()

    # Merge and deduplicate, ensuring default is first
    if default_lang not in langs:
        langs = [default_lang] + [l for l in langs if l != default_lang]
    # normalize
    langs = [l.strip() for l in langs if l.strip()]

    return langs


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
