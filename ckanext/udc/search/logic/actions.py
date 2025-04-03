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
    return _filter_facets_get()


@cache_for(60)
def _filter_facets_get() -> dict[str, Any]:
    """
    Get the facets for the search page.
    """

    default_limit: int = config.get("search.facets.default")
    facets_fields = h.facets()  # [*h.facets(), "author"]

    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets_fields.extend(plugin.dataset_facets({}, "catalogue").keys())

    data_dict: dict[str, Any] = {
        "q": "*:*",
        "facet.limit": -1,
        "facet.field": facets_fields,
        "rows": default_limit,
        "start": 0,
        # "sort": "view_recent desc",
        "fq": 'capacity:"public"',
    }

    query = logic.get_action("package_search")({}, data_dict)

    return query["search_facets"]
