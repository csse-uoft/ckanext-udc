import logging
import sys
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
    cudc_import_logs_get,
    cudc_import_log_delete,
    cudc_clear_organization,
)
from .logic.relationships import init_relationships

log = logging.getLogger(__name__)


class UdcImportOtherPortalsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurable)
    

    def configure(self, config: CKANConfig):
        # The CLI for re-indexing the search index is not working without loading the additional relationship types
        
        # if not ("run" in sys.argv or "uwsgi" in sys.argv or ("jobs" in sys.argv and "worker" in sys.argv)):
        #     # Do not load the plugin if we are running the CLI
        #     return
        init_relationships()
        log.info("Udc ImportOtherPortals Plugin Loaded!")

    # IActions
    def get_actions(self) -> Dict[str, Action]:
        return {
            "cudc_import_configs_get": cudc_import_configs_get,
            "cudc_import_config_update": cudc_import_config_update,
            "cudc_import_run": cudc_import_run,
            "cudc_import_config_delete": cudc_import_config_delete,
            "cudc_import_logs_get": cudc_import_logs_get,
            "cudc_import_log_delete": cudc_import_log_delete,
            "cudc_clear_organization": cudc_clear_organization,
        }
