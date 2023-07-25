from __future__ import annotations

import json
import traceback
import re
from collections import OrderedDict
from typing import Any, Callable, Collection, KeysView, Optional, Union, cast

from ckan.types import Schema, Context
import ckan
import ckan.plugins as plugins
import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan.plugins.toolkit import (chained_action, side_effect_free, chained_helper)
import ckan.lib.helpers as h
from ckan.common import current_user, _

from .graph.logic import onUpdateCatalogue

import logging

log = logging.getLogger(__name__)

# Register a chained action after `config_option_update(...)` is triggered, i.e. config is saved from the settings page.
# We need to reload the UDC plugin to make sure the maturity model is up to date.
@side_effect_free
@chained_action
def config_option_update(original_action, context, data_dict):
    try:
        # Call our plugin to update the config
        log.info("config_option_update: Update UDC Config")
        plugins.get_plugin('udc').reload_config(
            json.loads(data_dict["ckanext.udc.config"]))
    except:
        log.error

    res = original_action(context, data_dict)
    return res

@side_effect_free
@chained_action
def package_update(original_action, context, data_dict):
    onUpdateCatalogue(context, data_dict)
    return original_action(context, data_dict)

@side_effect_free
@chained_action
def package_delete(original_action, context, data_dict):
    print(f"Package Delete: ", data_dict)
    return original_action(context, data_dict)


# Register a chained helpers for humanize_entity_type() to change labels.
@chained_helper
def humanize_entity_type(next_helper: Callable[..., Any],
                         entity_type: str, object_type: str, purpose: str):

    if (entity_type, object_type) == ("package", "catalogue"):
        if purpose == "main nav":
            return "Catalogue"
        elif purpose == "search placeholder":
            return "Search Catalogue Entries"
        elif purpose == "search_placeholder":
            # Don't know where is this used.
            return "Catalogue Entry"
        elif purpose == "create title":
            return "Create Catalogue Entry"
        elif purpose == "create label":
            return "Create Catalogue Entry"
        elif purpose == "add link":
            return "Add Catalogue Entry"
        elif purpose == "no description":
            return "There is no description for this catalogue entry"
        elif purpose == "view label":
            return "View Catalogue Entry"


    original_text = next_helper(entity_type, object_type, purpose)
    # print(entity_type, object_type, purpose, original_text)

    return original_text


# The home page view does not pass the full search_facets to template.
# This helper get all search_facets that are required to call `h.get_facet_items_dict(...)`
def get_full_search_facets():
    context = cast(Context, {
        'model': model,
        'session': model.Session,
        'user': current_user.name,
        'auth_user_obj': current_user
    }
    )
    default_limit: int = ckan.common.config.get('search.facets.default')
    facets = [*h.facets(), *plugins.get_plugin('udc').facet_titles.keys(), 'author']
    data_dict: dict[str, Any] = {
        'q': '*:*',
        'facet.field': facets,
        'rows': default_limit,
        'start': 0,
        'sort': 'view_recent desc',
        'fq': 'capacity:"public"'}
    query = logic.get_action('package_search')(context, data_dict)
    return query['search_facets']

def get_default_facet_titles():
    # Copied from ckan.views.dataset.search
    org_label = h.humanize_entity_type(
        u'organization',
        h.default_group_type(u'organization'),
        u'facet label') or _(u'Organizations')

    group_label = h.humanize_entity_type(
        u'group',
        h.default_group_type(u'group'),
        u'facet label') or _(u'Groups')

    default_facet_titles = {
        u'organization': org_label,
        u'groups': group_label,
        u'tags': _(u'Tags'),
        u'res_format': _(u'Formats'),
        u'license_id': _(u'Licenses'),
    }
    return default_facet_titles

def process_facets_fields(facets_fields):
    """For search page displaying search filters"""

    results = {}
    for field in facets_fields:
        if field.startswith("extras_"):
            if field[7:] not in results:
                results[field[7:]] = []

            for item in facets_fields[field]:
                results[field[7:]].append({
                    "ori_field": field,
                    "ori_value": item,
                    "value": f'"{item}"'
                })
            
        else:
            if field not in results:
                results[field] = []

            for item in facets_fields[field]:
                results[field].append({
                    "ori_field": field,
                    "ori_value": item,
                    "value": item
                })
    # print(results)
    return results

def get_maturity_percentages(config, pkg_dict):
    percentages = []
    for idx, level in enumerate(config):
        num_not_empty = 0
        total_size = 0
        for field in level["fields"]:
            if field.get("ckanField"):
                # Skip custom_fields
                if field.get("ckanField") in ['custom_fields']:
                    continue
                # organization_and_visibility is always filled
                if field.get("ckanField") == 'organization_and_visibility':
                    num_not_empty += 2
                    total_size += 1
                # `description` is stored as `notes`
                elif field.get("ckanField") == 'description' and pkg_dict.get("notes"):
                    num_not_empty += 1
                # `source` is stored as `url`
                elif field.get("ckanField") == 'source' and pkg_dict.get("url"):
                    num_not_empty += 1
                elif pkg_dict.get(field["ckanField"]):
                    num_not_empty += 1
            else:
                if field.get("name") and field.get("label") and pkg_dict.get(field["name"]):
                    num_not_empty += 1

            total_size += 1
        percentages.append(str(round(num_not_empty / total_size * 100)) + "%")

    return percentages
