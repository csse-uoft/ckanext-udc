from __future__ import annotations

import json
import os
import traceback

from ckan.types import Schema
import ckan
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.plugins.toolkit import (chained_action,side_effect_free)



"""
See https://docs.ckan.org/en/latest/theming/templates.html
See https://docs.ckan.org/en/latest/extensions/adding-custom-fields.html
See https://docs.ckan.org/en/2.10/extensions/remote-config-update.html
See https://docs.ckan.org/en/2.10/extensions/custom-config-settings.html?highlight=config%20declaration
"""

udcPlugin = None

class UdcPlugin(plugins.SingletonPlugin, tk.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IConfigDeclaration)
    plugins.implements(plugins.IActions)

    # Load JSON config
    config_file = open(os.path.join(os.path.dirname(__file__), "config.json"))
    default_config = json.load(config_file)
    config = default_config

    all_fields = []

    def __init__(self, name=""):
        global udcPlugin
        udcPlugin = self
        existing_config = ckan.model.system_info.get_system_info("ckanext.udc.maturity_model")
        if existing_config:
            try:
                # Call our plugin to update the config
                udcPlugin.reload_config(json.loads(existing_config)) 
            except:
                print
        print("UDC Plugin Loaded!")
        

    def reload_config(self, config: list):
        try:
            print("tring to load udc config:")
            print(config)
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
            print("UDC Plugin Error:")
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

    def declare_config_options(self, declaration, key):
        # if tk.config.get("ckanext.udc.maturity_model") is None:
        # declaration.annotate("UDC Config section")
        # declaration.declare("ckanext.udc.maturity_model", json.dumps(self.default_config, indent=4))
        pass

    def get_actions(self):
        return {
            "config_option_update": config_option_update
        }


@side_effect_free
@chained_action
def config_option_update(original_action, context, data_dict):
    try:
        # Call our plugin to update the config
        udcPlugin.reload_config(json.loads(data_dict["ckanext.udc.maturity_model"]))
    except:
        print

    res = original_action(context, data_dict)
    return res


# CKAN Config Validator
def udc_config_validor(config_str):
    try:
        config = json.loads(config_str)
        all_fields = []
        for level in config:
            for field in level["fields"]:
                if field.get("name"):
                    all_fields.append(field["name"])
    except:
        raise tk.Invalid("Malformed UDC JSON Config.")
    return config_str