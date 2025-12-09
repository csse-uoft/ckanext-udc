from __future__ import annotations

import json
import traceback
import re
from collections import OrderedDict
from typing import Any, Callable, Collection, KeysView, Optional, Union, cast

from ckan.types import Schema, Context
from ckan.common import _
import ckan
import ckan.plugins as plugins
import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan.plugins.toolkit import (chained_action, side_effect_free, chained_helper)
import ckan.lib.helpers as h
from ckan.common import current_user, _

from .graph.logic import onUpdateCatalogue, onDeleteCatalogue, get_catalogue_graph
from ckanext.udc.file_format.logic import before_package_update as before_package_update_for_file_format

import logging
import json
import chalk

log = logging.getLogger(__name__)


import time

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
    # Pre-process custom file format
    before_package_update_for_file_format(context, data_dict)
    
    result = original_action(context, data_dict)
    try:
        if not plugins.get_plugin('udc').disable_graphdb:
            onUpdateCatalogue(context, result)
    except Exception as e:
        log.error(e)
        print(e)
        raise logic.ValidationError([_("Error occurred in updating the knowledge graph, please contact administrator:\n") + str(e)])
    return result

@side_effect_free
@chained_action
def package_delete(original_action, context, data_dict):
    print(f"Package Delete: ", data_dict)
    result = original_action(context, data_dict)
    try:
        if not plugins.get_plugin('udc').disable_graphdb:
            onDeleteCatalogue(context, data_dict)
    except Exception as e:
        log.error(e)
        print(e)
        raise logic.ValidationError([_("Error occurred in updating the knowledge graph, please contact administrator:\n") + str(e)])
    return result


# Register a chained helpers for humanize_entity_type() to change labels.
@chained_helper
def humanize_entity_type(next_helper: Callable[..., Any],
                         entity_type: str, object_type: str, purpose: str):

    if (entity_type, object_type) == ("package", "catalogue"):
        if purpose == "main nav":
            return _("Catalogue")
        elif purpose == "search placeholder":
            return _("Search Catalogue Entries")
        elif purpose == "search_placeholder":
            # Don't know where is this used.
            return _("Catalogue Entry")
        elif purpose == "create title":
            return _("Create Catalogue Entry")
        elif purpose == "create label":
            return _("Create Catalogue Entry")
        elif purpose == "add link":
            return _("Add Catalogue Entry")
        elif purpose == "no description":
            return _("There is no description for this catalogue entry")
        elif purpose == "view label":
            return _("View Catalogue Entry")


    original_text = next_helper(entity_type, object_type, purpose)
    # print(entity_type, object_type, purpose, original_text)

    return original_text


def get_default_facet_titles():
    facets: dict[str, str] = OrderedDict()
    
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
    
    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, "catalogue")
    return facets

def process_facets_fields(facets_fields: dict):
    """For search page displaying search filters"""
    print("facets_fields", facets_fields)
    results = {}
    for field in facets_fields:
        if field.startswith("filter-logic"):
            continue
        
        if field.startswith("extras_"):
            field_name = field[7:]
        elif field.endswith("_ngram"):
            field_name = field[:-6]
        else:
            field_name = field
        
        if field_name not in results:
            results[field_name] = {"logic": "or", "values": []}
        
        if 'values' in facets_fields[field]:
            values = facets_fields[field]['values']
            is_fts = facets_fields[field].get('fts', False)
            for item in values:
                results[field_name]["values"].append({
                    "ori_field": field,
                    "ori_value": item,
                    "value": f'Search for "{item}"' if is_fts else item,
                })
        else:
            # Date or number ranges
            min = facets_fields[field].get('min')
            max = facets_fields[field].get('max')

            if min:
                results[field_name]["values"].append({
                    "ori_field": "min_" + field_name,
                    "ori_value": min,
                    "value": f"From: {min}",
                })
            if max:
                results[field_name]["values"].append({
                    "ori_field": "max_" + field_name,
                    "ori_value": max,
                    "value": f"To: {max}",
                })
           
        
        if "filter-logic-" + field in facets_fields and facets_fields["filter-logic-" + field][0] == "and":
            results[field_name]["logic"] = "and"
            
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


def get_system_info(name: str):
    return model.system_info.get_system_info(name)


def udc_json_attr(value):
    """Return a JSON string safe to embed in an HTML attribute.

    - If value is already a string, assume it is JSON (or plain text) and
      return it as-is; Jinja's autoescape will handle HTML encoding.
    - If value is a dict/list/etc, json.dumps it to a compact string.
    """

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return ""
