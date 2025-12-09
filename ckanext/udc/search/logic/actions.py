from __future__ import annotations
from typing import Any, Callable, Collection, KeysView, Optional, Union, cast
from ckanext.udc.search.logic.utils import profile_func, cache_for
from ckan import model, authz, logic
from ckan.common import _, config, current_user
import ckan.plugins as plugins
import ckan.lib.helpers as h
from ckan.plugins.toolkit import side_effect_free

import logging

log = logging.getLogger(__name__)


# @profile_func
@side_effect_free
def filter_facets_get(context, data_dict):
    return _filter_facets_get(data_dict)

from collections import OrderedDict
from typing import Any
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import ckan.logic as logic
import ckan.lib.helpers as h

from ckanext.udc.solr.config import get_current_lang


def _facet_cache_key(data_dict=None, *_, **kwargs):
    if isinstance(data_dict, dict):
        lang = data_dict.get("lang")
    else:
        lang = None

    if not lang and "lang" in kwargs:
        lang = kwargs["lang"]

    if not lang and isinstance(kwargs.get("data_dict"), dict):
        lang = kwargs["data_dict"].get("lang")

    if not lang:
        lang = get_current_lang()

    return lang or "__default__"


@cache_for(60, key_func=_facet_cache_key)
def _filter_facets_get(data_dict) -> dict[str, Any]:
    """
    data_dict only needs to contain "lang" (optional).
    
    Multilingual facets with stable outward keys:

      'tags'            -> Solr 'tags_<lang>_f'
      '<text_field>'    -> Solr '<text_field>_<lang>_f'
      'extras_<name>'   -> Solr 'extras_<name>' (non-text stays as-is)

    The Solr response is renamed back to the stable keys so the UI
    and your existing code keep working unchanged.
    """
    lang = data_dict.get("lang") or get_current_lang()

    # 1) Gather facet keys (prefer plugin-provided; then CKAN defaults)
    ordered_plugin_keys: list[str] = []
    for p in plugins.PluginImplementations(plugins.IFacets):
        try:
            provided = p.dataset_facets(OrderedDict(), "catalogue") or {}
            for k in provided.keys():
                if k not in ordered_plugin_keys:
                    ordered_plugin_keys.append(k)
        except Exception:
            continue

    facet_keys: list[str] = []
    for k in ordered_plugin_keys + list(h.facets()):
        if k not in facet_keys:
            facet_keys.append(k)

    # 2) Build alias -> Solr mapping
    try:
        udc = plugins.get_plugin("udc")
        text_fields = set(udc.text_fields or [])
        dropdown_options = udc.dropdown_options or {}
    except Exception:
        text_fields = set()
        dropdown_options = {}

    alias_to_solr: OrderedDict[str, str] = OrderedDict()
    for key in facet_keys:
        if key == "tags":
            alias_to_solr[key] = f"tags_{lang}_f"
        # version relationship helper facets: use *_title_url for display
        # but map outward stable keys to URL-only Solr fields
        elif key == "version_dataset":
            alias_to_solr[key] = "version_dataset_url"
        elif key == "dataset_versions":
            alias_to_solr[key] = "dataset_versions_url"
        elif key.startswith("extras_"):
            # Non-text maturity fields (date/number/select) facet via extras_*
            alias_to_solr[key] = key
        elif key in text_fields:
            # Text maturity fields use language-specific facet fields
            alias_to_solr[key] = f"{key}_{lang}_f"
        else:
            # Any other core facet stays as-is
            alias_to_solr[key] = key

    facet_fields_solr = list(dict.fromkeys(alias_to_solr.values()))  # de-dupe preserve order

    # 3) Query Solr
    try:
        default_limit = int(tk.config.get("search.facets.default", 10))
    except Exception:
        default_limit = 10

    data_dict: dict[str, Any] = {
        "q": "*:*",
        "facet.limit": -1,
        "facet.field": facet_fields_solr,
        "rows": default_limit,
        "start": 0,
        "fq": 'capacity:"public"',
    }
    query = logic.get_action("package_search")({}, data_dict)
    raw_facets: dict[str, Any] = query.get("search_facets", {})

    # 4) Rename Solr facet keys back to stable outward keys
    facets: dict[str, Any] = {}
    for alias, solr_name in alias_to_solr.items():
        if solr_name in raw_facets:
            facets[alias] = raw_facets[solr_name]

    # 5) Localize dropdown option labels for extras_* facets
    for stable_key, payload in facets.items():
        # For extras_*, strip prefix to lookup configured option labels
        base = stable_key[7:] if stable_key.startswith("extras_") else stable_key
        options_map = dropdown_options.get(base)
        if not options_map:
            continue
        for item in payload.get("items", []):
            label = options_map.get(item.get("name"))
            if label:
                item["display_name"] = label

    return facets
