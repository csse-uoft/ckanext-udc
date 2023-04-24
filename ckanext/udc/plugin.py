from __future__ import annotations

import json
import traceback
import re
from collections import OrderedDict
from typing import Any, Callable, Collection, KeysView, Optional, Union

from ckan.types import Schema
import ckan
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.plugins.toolkit import (chained_action,side_effect_free)
import logging



"""
See https://docs.ckan.org/en/latest/theming/templates.html
See https://docs.ckan.org/en/latest/extensions/adding-custom-fields.html
See https://docs.ckan.org/en/2.10/extensions/remote-config-update.html
See https://docs.ckan.org/en/2.10/extensions/custom-config-settings.html?highlight=config%20declaration
"""

log = logging.getLogger(__name__)

class UdcPlugin(plugins.SingletonPlugin, tk.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IFacets)

    SUPPORTED_CKAN_FIELDS = ["title", "description", "tags", "license", "author"]

    def __init__(self, name=""):
        existing_config = ckan.model.system_info.get_system_info("ckanext.udc.maturity_model")
        self.config = []
        self.all_fields = []
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
            for level in config:
                for field in level["fields"]:
                    if field.get("name"):
                        all_fields.append(field["name"])
            # Do not mutate the vars
            self.all_fields.clear()
            self.all_fields.extend(all_fields)
            self.config.clear()
            self.config.extend(config)

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
        return {"config": self.config}

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):  # -> list[str]
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

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
        return {
            "config_option_update": config_option_update
        }
    
    def dataset_facets(self, facets_dict: OrderedDict[str, Any], package_type: str):
        print(facets_dict)
        for level in self.config:
            for field in level["fields"]:
                type = field.get("type")
                if field.get("name") and (type is '' or type == 'text' or type == 'single_select'):
                    facets_dict[field["name"]] = plugins.toolkit._(field["label"])
        return facets_dict
    
    def group_facets(self, facets_dict: OrderedDict[str, Any], group_type: str, package_type: Optional[str]):
        return facets_dict
    
    def organization_facets(self, facets_dict: OrderedDict[str, Any], organization_type: str, package_type: Optional[str]):
        return facets_dict


@side_effect_free
@chained_action
def config_option_update(original_action, context, data_dict):
    try:
        # Call our plugin to update the config
        log.info("config_option_update: Update UDC Config")
        plugins.get_plugin('udc').reload_config(json.loads(data_dict["ckanext.udc.maturity_model"]))
    except:
        log.error

    res = original_action(context, data_dict)
    return res


# CKAN Config Validator
def udc_config_validor(config_str):
    try:
        config = json.loads(config_str)
    except:
        raise tk.Invalid("UDC Config: Malformed JSON Format.")
    
    for level in config:
        if not ("title" in level and "name" in level and "fields" in level):
            raise tk.Invalid(f'Malformed UDC Config: "title", "name" and "fields" are required for each level.')
        for field in level["fields"]:
            if "ckanField" in field:
                if field["ckanField"] not in UdcPlugin.SUPPORTED_CKAN_FIELDS:
                    raise tk.Invalid(f"Malformed UDC Config: The provided CKAN field `{field['ckanField']}` is not supported.")
            else:
                if not ("name" in field and "label" in field):
                    raise tk.Invalid(f"Malformed UDC Config: `name` and `label` is required for custom field.")
                if re.match(r'^\w+$', field['name']) is None:
                    raise tk.Invalid(f"Malformed UDC Config: The provided field name `{field['name']}` is not alpha-numeric.")
                
    return config_str
