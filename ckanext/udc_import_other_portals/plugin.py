import logging
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.types import Action, AuthFunction, Schema
from ckan.common import CKANConfig
import ckan.plugins.toolkit as tk
from typing import Dict
from .logic.actions import (
    cudc_import_configs_get,
    cudc_import_config_delete,
    cudc_import_config_update,
    cudc_import_run,
    cudc_import_status_get,
    cudc_import_logs_get,
    cudc_import_log_delete,
)

log = logging.getLogger(__name__)


class UdcImportOtherPortalsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IActions)

    def configure(self, config: CKANConfig):
        log.info("Udc ImportOtherPortals Plugin Loaded!")

    # IActions
    def get_actions(self) -> Dict[str, Action]:
        return {
            "cudc_import_configs_get": cudc_import_configs_get,
            "cudc_import_config_update": cudc_import_config_update,
            "cudc_import_run": cudc_import_run,
            "cudc_import_status_get": cudc_import_status_get,
            "cudc_import_config_delete": cudc_import_config_delete,
            "cudc_import_logs_get": cudc_import_logs_get,
            "cudc_import_log_delete": cudc_import_log_delete,
        }

    # IConfigurable
    def update_config_schema(self, schema: Schema):

        ignore_missing = tk.get_validator("ignore_missing")
        unicode_safe = tk.get_validator("unicode_safe")

        schema.update(
            {
                "ckanext.udc_import_other_portals.side_panel_text": [
                    ignore_missing,
                    unicode_safe,
                ],
                # This is a custom configuration option
                "ckanext.udc_import_other_portals.import_configs": [
                    ignore_missing,
                    unicode_safe,
                ],
            }
        )

        return schema
