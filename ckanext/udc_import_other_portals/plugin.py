import logging
import sys

from ckanext.udc_import_other_portals.model import init_startup
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.types import Action, AuthFunction, Schema
from ckan.common import CKANConfig
import ckan.plugins.toolkit as tk
from typing import Dict
from .logic.actions import (
    cudc_import_configs_get,
    cudc_import_configs_list,
    cudc_import_config_show,
    cudc_import_remote_orgs_list,
    cudc_organization_list_min,
    cudc_import_config_delete,
    cudc_import_config_update,
    cudc_import_run,
    cudc_import_logs_get,
    cudc_import_log_delete,
    cudc_clear_organization,
    cudc_import_language_options,
)
from .logic.arcgis_based.actions import (
    arcgis_hub_portal_discovery,
    arcgis_hub_portal_discovery_get,
    arcgis_hub_portal_discovery_counts,
    arcgis_hub_portal_discovery_config_get,
    arcgis_hub_portal_discovery_config_default,
    arcgis_hub_portal_discovery_config_update,
    arcgis_auto_import_configs_get,
    arcgis_auto_import_configs_create,
    arcgis_auto_import_configs_delete,
)
from .logic.relationships import init_relationships
from .scheduler import sync_cron_jobs

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
        
        if ("run" in sys.argv or "uwsgi" in sys.argv) and not ("worker" in sys.argv):
            # We want the main CKAN instance to run startup tasks
            init_startup()
            sync_cron_jobs()
            log.info("Udc ImportOtherPortals DB startup!")
 
        log.info("Udc ImportOtherPortals Plugin Loaded!")

    # IActions
    def get_actions(self) -> Dict[str, Action]:
        return {
            "cudc_import_configs_get": cudc_import_configs_get,
            "cudc_import_configs_list": cudc_import_configs_list,
            "cudc_import_config_show": cudc_import_config_show,
            "cudc_import_remote_orgs_list": cudc_import_remote_orgs_list,
            "cudc_organization_list_min": cudc_organization_list_min,
            "cudc_import_config_update": cudc_import_config_update,
            "cudc_import_run": cudc_import_run,
            "cudc_import_config_delete": cudc_import_config_delete,
            "cudc_import_logs_get": cudc_import_logs_get,
            "cudc_import_log_delete": cudc_import_log_delete,
            "cudc_clear_organization": cudc_clear_organization,
            "cudc_import_language_options": cudc_import_language_options,
            "arcgis_hub_portal_discovery": arcgis_hub_portal_discovery,
            "arcgis_hub_portal_discovery_get": arcgis_hub_portal_discovery_get,
            "arcgis_hub_portal_discovery_counts": arcgis_hub_portal_discovery_counts,
            "arcgis_hub_portal_discovery_config_get": arcgis_hub_portal_discovery_config_get,
            "arcgis_hub_portal_discovery_config_default": arcgis_hub_portal_discovery_config_default,
            "arcgis_hub_portal_discovery_config_update": arcgis_hub_portal_discovery_config_update,
            "arcgis_auto_import_configs_get": arcgis_auto_import_configs_get,
            "arcgis_auto_import_configs_create": arcgis_auto_import_configs_create,
            "arcgis_auto_import_configs_delete": arcgis_auto_import_configs_delete,
        }
