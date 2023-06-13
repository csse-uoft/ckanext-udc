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
from ckan.plugins.toolkit import (chained_action, side_effect_free)
import ckan.lib.helpers as h
from ckan.common import current_user

import logging
from .cli import udc as cli_udc
from .validator import udc_config_validor
from .helpers import config_option_update, get_full_search_facets,\
      get_default_facet_titles, process_facets_fields, humanize_entity_type, get_maturity_percentages

"""
See https://docs.ckan.org/en/latest/theming/templates.html
See https://docs.ckan.org/en/latest/extensions/adding-custom-fields.html
See https://docs.ckan.org/en/2.10/extensions/remote-config-update.html
See https://docs.ckan.org/en/2.10/extensions/custom-config-settings.html?highlight=config%20declaration
See https://docs.ckan.org/en/2.10/theming/webassets.html
"""

log = logging.getLogger(__name__)

# Add UDC CLI
# We can then `ckan -c /etc/ckan/default/ckan.ini udc move-to-catalogues` to run the migration script
if hasattr(ckan, 'cli') and hasattr(ckan.cli, 'cli'):
    ckan.cli.cli.ckan.add_command(cli_udc.udc)


class UdcPlugin(plugins.SingletonPlugin, tk.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IFacets)

    def __init__(self, name=""):
        existing_config = ckan.model.system_info.get_system_info(
            "ckanext.udc.maturity_model")
        self.config = []
        self.all_fields = []
        self.facet_titles = {}
        if existing_config:
            try:
                # Call our plugin to update the config
                self.reload_config(json.loads(existing_config))
            except:
                log.error
        log.info("UDC Plugin Loaded!")

    def reload_config(self, config: list):
        try:
            log.info("tring to load udc config:")
            log.info(config)
            all_fields = []
            self.facet_titles.clear()
            for level in config:
                for field in level["fields"]:
                    if field.get("name"):
                        all_fields.append(field["name"])
                    type = field.get("type")
                    if field.get("name") and (type == '' or type is None or type == 'text' or type == 'single_select'):
                        self.facet_titles[field["name"]] = tk._(field["label"])

            # Do not mutate the vars
            self.all_fields.clear()
            self.all_fields.extend(all_fields)
            self.config.clear()
            self.config.extend(config)
            # self.facet_titles.update(get_default_facet_titles())

        except Exception as e:
            log.error("UDC Plugin Error:")
            traceback.print_exc()

    def update_config(self, config_):
        tk.add_template_directory(config_, 'templates')
        tk.add_public_directory(config_, 'public')
        tk.add_resource('assets', 'udc')

    def _modify_package_schema(self, schema: Schema) -> Schema:
        # our custom field
        for field in self.all_fields:
            schema.update({
                field: [tk.get_validator('ignore_missing'),
                        tk.get_converter('convert_to_extras')],
            })

        return schema

    def create_package_schema(self) -> Schema:
        # let's grab the default schema in our plugin
        schema: Schema = super(UdcPlugin, self).create_package_schema()
        return self._modify_package_schema(schema)

    def update_package_schema(self) -> Schema:
        schema: Schema = super(UdcPlugin, self).update_package_schema()
        # our custom field
        return self._modify_package_schema(schema)

    def show_package_schema(self) -> Schema:
        schema: Schema = super(UdcPlugin, self).show_package_schema()
        for field in self.all_fields:
            schema.update({
                field: [tk.get_converter('convert_from_extras'),
                        tk.get_validator('ignore_missing')],
            })

        return schema

    def get_helpers(self):
        return {
            "config": self.config,
            "facet_titles": self.facet_titles,
            "get_full_search_facets": get_full_search_facets,
            "get_default_facet_titles": get_default_facet_titles,
            "process_facets_fields": process_facets_fields,
            "humanize_entity_type": humanize_entity_type,
            "get_maturity_percentages": get_maturity_percentages,
        }

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):  # -> list[str]
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return ['dataset', 'catalogue']

    def update_config_schema(self, schema: Schema):

        ignore_missing = tk.get_validator('ignore_missing')
        unicode_safe = tk.get_validator('unicode_safe')
        json_object = tk.get_validator('json_object')

        schema.update({
            # This is a custom configuration option
            'ckanext.udc.maturity_model': [
                ignore_missing, unicode_safe, udc_config_validor
            ],
        })

        return schema

    def get_actions(self):
        """
        Override CKAN's default actions.
        """
        return {
            "config_option_update": config_option_update
        }

    def dataset_facets(self, facets_dict: OrderedDict[str, Any], package_type: str):
        for name in self.facet_titles:
            facets_dict[name] = self.facet_titles[name]
        return facets_dict

    def group_facets(self, facets_dict: OrderedDict[str, Any], group_type: str, package_type: Optional[str]):
        return facets_dict

    def organization_facets(self, facets_dict: OrderedDict[str, Any], organization_type: str, package_type: Optional[str]):
        return facets_dict
