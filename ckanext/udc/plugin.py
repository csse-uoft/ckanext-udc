from __future__ import annotations

import sys
import json
import traceback
import chalk
from collections import OrderedDict
from typing import Any, Callable, Collection, KeysView, Optional, Union, cast, Iterable, List
from functools import partial

from ckanext.udc.search.logic.actions import filter_facets_get
from ckan.types import Schema, Context, CKANApp, Response, SignalMapping
import ckan
import ckan.plugins as plugins
import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as tk
import ckan.lib.base as base
from ckan.plugins.toolkit import chained_action, side_effect_free
import ckan.lib.helpers as h
from ckan.lib.helpers import Page
from ckan.common import asbool, current_user, CKANConfig, request, g, config, _
from ckan.views.dataset import _get_search_details, remove_field, _sort_by, _pager_url, _setup_template_variables, _get_pkg_template
from ckan.lib.search import SearchQueryError, SearchError

from flask import Blueprint

import logging
from ckanext.udc.cli import udc as cli_udc
from ckanext.udc.validator import udc_config_validator
from ckanext.udc.helpers import (
    config_option_update,
    get_default_facet_titles,
    process_facets_fields,
    humanize_entity_type,
    get_maturity_percentages,
    package_update,
    package_delete,
    get_system_info,
)
from ckanext.udc.graph.sparql_client import SparqlClient
from ckanext.udc.graph.preload import preload_ontologies

from ckanext.udc.licenses.logic.action import (
    license_create,
    license_delete,
    licenses_get,
    license_update,
    init_licenses,
    test_long_task,
)
from ckanext.udc.licenses.utils import license_options_details
from ckanext.udc.file_format.logic import (
    file_format_create,
    file_format_delete,
    file_formats_get,
)
from ckanext.udc.desc.actions import summary_generate, update_summary, default_ai_summary_config
from ckanext.udc.desc.utils import init_plugin as init_udc_desc
from ckanext.udc.error_handler import override_error_handler
from ckanext.udc.system.actions import reload_supervisord, get_system_stats
from ckanext.udc.solr import update_solr_maturity_model_fields


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
if hasattr(ckan, "cli") and hasattr(ckan.cli, "cli"):
    ckan.cli.cli.ckan.add_command(cli_udc.udc)


@tk.blanket.blueprints
class UdcPlugin(plugins.SingletonPlugin, tk.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController)
    plugins.implements(plugins.IMiddleware)
    plugins.implements(plugins.IBlueprint)

    disable_graphdb = False
    maturity_model = []
    mappings = {}
    preload_ontologies = {}
    all_fields: List[str] = []
    facet_titles = {}
    text_fields: List[str] = []
    date_fields: List[str] = []
    multiple_select_fields: List[str] = []
    dropdown_options: dict[str, dict[str, str]] = {}

    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "udc")

    def _cli_configure(self):
        """Partial load for CLI"""
        self.disable_graphdb = True
        existing_config = ckan.model.system_info.get_system_info("ckanext.udc.config")
        if existing_config:
            try:
                # Call our plugin to update the config
                self.reload_config(json.loads(existing_config))
            except:
                log.error

        # Load custom licenses
        init_licenses()

    def configure(self, config: CKANConfig):
        log.info(sys.argv)
        if not ("run" in sys.argv or "uwsgi" in sys.argv or ("jobs" in sys.argv and "worker" in sys.argv)):
            log.info("Skipping UDC Plugin Configuration")
            # Do not load the plugin if we are running the CLI
            self._cli_configure()
            return
        existing_config = ckan.model.system_info.get_system_info("ckanext.udc.config")
        # print(existing_config)

        # Load sparql client
        endpoint = tk.config.get("udc.sparql.endpoint")
        username = tk.config.get("udc.sparql.username") or None
        password = tk.config.get("udc.sparql.password") or None

        if endpoint is None:
            self.disable_graphdb = True
            log.info("No GraphDB Endpoint is provided.")

        else:
            self.sparql_client = SparqlClient(
                endpoint, username=username, password=password
            )
            if self.sparql_client.test_connecetion():
                log.info("GraphDB connected: " + endpoint)
            else:
                log.error("UDC cannot connect to the GraphDB")
                self.disable_graphdb = True

        # Load config
        if existing_config:
            try:
                # Call our plugin to update the config
                self.reload_config(json.loads(existing_config))
            except:
                log.error

        # Load custom licenses
        init_licenses()

        # Init chatgpt summary plugin
        init_udc_desc()

        log.info("UDC Plugin Loaded!")

    def reload_config(self, config: list):
        try:
            # log.info("tring to load udc config:")
            # log.info(config)
            all_fields = []
            self.facet_titles.clear()
            for level in config["maturity_model"]:
                for field in level["fields"]:
                    if field.get("name"):
                        all_fields.append(field["name"])
                    type = field.get("type")
                    if field.get("name") and (
                        type == ""
                        or type is None
                        or type == "text"
                        or type == "single_select"
                        or type == "multiple_select"
                        or type == "number"
                        or type == "date"
                    ):
                        self.facet_titles[field["name"]] = tk._(field["label"])
                    if field.get("name") and (type == "text" or type is None):
                        self.text_fields.append(field["name"])
                    if field.get("type") == "date":
                        self.date_fields.append(field["name"])
                    if field.get("type") == "multiple_select":
                        self.multiple_select_fields.append(field["name"])

            # Preload ontologies
            if not self.disable_graphdb:
                endpoint = tk.config.get("udc.sparql.endpoint")
                username = tk.config.get("udc.sparql.username") or None
                password = tk.config.get("udc.sparql.password") or None
                # This will preload ontologies and
                # populate options to the fields that uses 'optionsFromQuery'
                preload_ontologies(
                    config, endpoint, username, password, self.sparql_client
                )

            # Store dropdown options
            for level in config["maturity_model"]:
                for field in level["fields"]:
                    if field.get("type") == "multiple_select" or field.get("type") == "single_select":
                        options = self.dropdown_options[field["name"]] = {}
                        for option in field["options"]:
                            options[option["value"]] = (
                                tk._(option["text"])
                            )
                        log.info(f"Dropdown options for field {field['name']} loaded: {len(options.keys())}")
            
            # Update solr index
            update_solr_maturity_model_fields(config["maturity_model"])

            # Do not mutate the vars
            self.all_fields.clear()
            self.all_fields.extend(all_fields)
            self.maturity_model.clear()
            self.maturity_model.extend(config["maturity_model"])
            self.mappings.clear()
            self.mappings.update(config["mappings"])
            self.preload_ontologies.clear()
            self.preload_ontologies.update(config["preload_ontologies"])

        except Exception as e:
            log.error("UDC Plugin Error:")
            traceback.print_exc()

    def _modify_package_schema(self, schema: Schema) -> Schema:
        # our custom field
        for field in self.all_fields:
            schema.update(
                {
                    field: [
                        tk.get_validator("ignore_missing"),
                        tk.get_converter("convert_to_extras"),
                    ],
                }
            )

        schema.update(
            {
                # For import from other portals plugin
                "cudc_import_config_id": [
                    tk.get_validator("ignore_missing"),
                    tk.get_converter("convert_to_extras"),
                ],
                # Keep track of the remote ID from the source portal
                "cudc_import_remote_id": [
                    tk.get_validator("ignore_missing"),
                    tk.get_converter("convert_to_extras"),
                ],
                "is_unified": [
                    tk.get_validator("ignore_missing"),
                    tk.get_validator("boolean_validator"),
                    tk.get_converter("convert_to_extras"),
                ],
                "source_last_updated": [
                    tk.get_validator("ignore_missing"),
                    tk.get_converter("convert_to_extras"),
                ],
                # ---- chatgpt summary ------
                "summary": [
                    tk.get_validator("ignore_missing"),
                    tk.get_converter("convert_to_extras"),
                ],
            }
        )
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
            schema.update(
                {
                    field: [
                        tk.get_converter("convert_from_extras"),
                        tk.get_validator("ignore_missing"),
                    ],
                }
            )

        schema.update(
            {
                # For import from other portals plugin
                "cudc_import_config_id": [
                    tk.get_converter("convert_from_extras"),
                    tk.get_validator("ignore_missing"),
                ],
                # Keep track of the remote ID from the source portal
                "cudc_import_remote_id": [
                    tk.get_converter("convert_from_extras"),
                    tk.get_validator("ignore_missing"),
                ],
                # For Unified Package:
                # If the package is unified, it uses 'unified_has_versions' to link other packages.
                # For every other packages that is not unified, use 'potential_duplicates' to link other duplicated packages.
                "is_unified": [
                    tk.get_converter("convert_from_extras"),
                    tk.get_validator("ignore_missing"),
                ],
                "source_last_updated": [
                    tk.get_converter("convert_from_extras"),
                    tk.get_validator("ignore_missing"),
                ],
                # ---- chatgpt summary ------
                "summary": [
                    tk.get_converter("convert_from_extras"),
                    tk.get_validator("ignore_missing"),
                ],
            }
        )

        return schema

    def get_helpers(self):
        return {
            "config": self.maturity_model,
            "facet_titles": self.facet_titles,
            "maturity_model_text_fields": self.text_fields,
            "get_default_facet_titles": get_default_facet_titles,
            "process_facets_fields": process_facets_fields,
            "humanize_entity_type": humanize_entity_type,
            "get_maturity_percentages": get_maturity_percentages,
            "get_system_info": get_system_info,
            "license_options_details": license_options_details,
        }

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):  # -> list[str]
        # This plugin just registers itself as the 'catalogue'.
        return ["dataset", "catalogue"]

    def update_config_schema(self, schema: Schema):

        ignore_missing = tk.get_validator("ignore_missing")
        unicode_safe = tk.get_validator("unicode_safe")
        json_object = tk.get_validator("json_object")

        schema.update(
            {
                # This is a custom configuration option
                "ckanext.udc.config": [
                    ignore_missing,
                    unicode_safe,
                    udc_config_validator,
                ],
                "ckanext.udc.group_side_panel_text": [ignore_missing, unicode_safe],
                "ckanext.udc.organization_side_panel_text": [
                    ignore_missing,
                    unicode_safe,
                ],
                "ckanext.udc.dataset_side_panel_text": [ignore_missing, unicode_safe],
                "ckanext.udc.catalogue_side_panel_text": [ignore_missing, unicode_safe],
                # ---- chatgpt summary config ------
                "ckanext.udc.desc.config": [ignore_missing, unicode_safe],
            }
        )

        return schema

    def get_actions(self):
        """
        Override CKAN's default actions.
        """
        return {
            "config_option_update": config_option_update,
            "package_update": package_update,
            "package_delete": package_delete,
            # Custom Licenses
            "license_create": license_create,
            "license_delete": license_delete,
            "licenses_get": licenses_get,
            "license_update": license_update,
            "test_long_task": test_long_task,
            # Custom file format
            "file_format_create": file_format_create,
            "file_format_delete": file_format_delete,
            "file_formats_get": file_formats_get,
            # Chatgpt summary actions
            "summary_generate": summary_generate,
            "update_summary": update_summary,
            "default_ai_summary_config": default_ai_summary_config,
            # System actions
            "reload_supervisord": reload_supervisord,
            "get_system_stats": get_system_stats,
            # "maturity_model_get": get_maturity_model,
            # Filters
            "filter_facets_get": filter_facets_get,
        }

    def dataset_facets(self, facets_dict: OrderedDict[str, Any], package_type: str):
        for name in self.facet_titles:
            if name in self.text_fields:
                # The text fields (solr type=text) can be used as facets
                # We need to use the builtin facet name
                # and not the extras_ prefix
                facets_dict[name] = self.facet_titles[name]
            else:
                # We need the extras_ prefix for our custom solr schema
                facets_dict["extras_" + name] = self.facet_titles[name]

        return facets_dict

    def group_facets(
        self,
        facets_dict: OrderedDict[str, Any],
        group_type: str,
        package_type: Optional[str],
    ):
        return facets_dict

    def organization_facets(
        self,
        facets_dict: OrderedDict[str, Any],
        organization_type: str,
        package_type: Optional[str],
    ):
        return facets_dict

    def read(self, entity: "model.Package") -> None:
        print(chalk.red("create"))
        pass

    def create(self, entity: "model.Package") -> None:
        pass

    def edit(self, entity: "model.Package") -> None:
        pass

    def delete(self, entity: "model.Package") -> None:
        pass

    def after_dataset_create(self, context: Context, pkg_dict: dict[str, Any]) -> None:
        pass

    def after_dataset_update(self, context: Context, pkg_dict: dict[str, Any]) -> None:
        pass

    def after_dataset_delete(self, context: Context, pkg_dict: dict[str, Any]) -> None:
        pass

    def after_dataset_show(self, context: Context, pkg_dict: dict[str, Any]) -> None:
        # Add related packages
        related_packages = []

        if pkg_dict.get("is_unified"):
            rel = (
                model.meta.Session.query(model.PackageRelationship)
                .filter(model.PackageRelationship.subject_package_id == pkg_dict["id"])
                .all()
            )
            for r in rel:
                related_package = model.Package.get(r.object_package_id)
                related_packages.append({
                    "title": related_package.title,
                    "id": related_package.id,
                    "name": related_package.name,
                })
        else:
            # Non-unified package need to get the unified package and then get the related packages
            rel = (
                model.meta.Session.query(model.PackageRelationship)
                .filter(model.PackageRelationship.object_package_id == pkg_dict["id"])
                .all()
            )

            for r in rel:
                unified_package = model.Package.get(r.subject_package_id)
                related_packages.append({
                    "title": unified_package.title,
                    "id": unified_package.id,
                    "name": unified_package.name,
                })

                rel2 = (
                    model.meta.Session.query(model.PackageRelationship)
                    .filter(model.PackageRelationship.subject_package_id == unified_package.id)
                    .filter(model.PackageRelationship.object_package_id != pkg_dict["id"])
                    .all()
                )

                for r in rel2:
                    related_package = model.Package.get(r.object_package_id)
                    # Check if exists
                    if related_package.id not in set([p["id"] for p in related_packages]):
                        related_packages.append({
                            "title": related_package.title,
                            "id": related_package.id,
                            "name": related_package.name,
                        })

        pkg_dict["related_packages"] = related_packages

    def before_dataset_search(self, search_params: dict[str, Any]) -> dict[str, Any]:
        # print(chalk.red("before_dataset_search"))
        # print(search_params)
        return search_params

    def after_dataset_search(
        self, search_results: dict[str, Any], search_params: dict[str, Any]
    ) -> dict[str, Any]:
        return search_results

    def before_dataset_index(self, pkg_dict: dict[str, Any]) -> dict[str, Any]:
        # Do not index related packages
        del pkg_dict["related_packages"]
        print(chalk.red("before_dataset_index"))
        # Map multiple select fields and covert to array
        # The field name should be 'extras_' + field_name for using our custom solr schema
        for field in self.multiple_select_fields:
            if field in pkg_dict:
                pkg_dict["extras_" + field] = pkg_dict[field].split(",")
        return pkg_dict

    def before_dataset_view(self, pkg_dict: dict[str, Any]) -> dict[str, Any]:
        return pkg_dict

    # IMiddleware
    def make_middleware(self, app: CKANApp, config: CKANConfig) -> CKANApp:
        override_error_handler(app, config)
        return app
    
    def make_error_log_middleware(self, app, config: CKANConfig) -> CKANApp:
        return app
