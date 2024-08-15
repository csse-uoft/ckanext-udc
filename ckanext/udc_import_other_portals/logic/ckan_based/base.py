import traceback
import logging
import requests

from ckanext.udc_import_other_portals.logger import ImportLogger

from ckanext.udc_import_other_portals.logic.ckan_based.api import get_package_ids, get_package, check_site_alive
from ckanext.udc_import_other_portals.logic.base import BaseImport, delete_package

from ckan import model, logic
from ckan.common import config
import ckan.lib.helpers as h
import ckan.lib.jobs as jobs

base_logger = logging.getLogger(__name__)


class CKANBasedImport(BaseImport):
    """
    Abstract class for imports
    """

    def __init__(self, context, import_config, base_api):
        super().__init__(context, import_config)
        self.base_api = base_api

    def iterate_imports(self):
        """
        Iterate all possible imports from the source api.
        """
        packages_ids = get_package_ids(self.base_api)

        # Set the import size for reporting in the frontend
        self.import_size = len(packages_ids)

        for package_id in packages_ids:
            package = get_package(package_id, self.base_api)
            yield package

    def map_to_cudc_package(self, src: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
        """
        raise NotImplementedError()

    def run_imports(self):
        """
        Run imports for all source packages. Users should not override this.
        """
        self.running = True
        self.logger = ImportLogger(base_logger)

        # Check if packages are deleted from the remote since last import
        if self.import_config.other_data is None:
            self.import_config.other_data = {}
    
        try:
            # Make sure remote endpoint is alive
            if check_site_alive(self.base_api):
                # In the CKAN based import, we only care about the ids
                if self.import_config.other_data.get("imported_ids"):
                    for imported_package_id in self.import_config.other_data.get("imported_ids"):
                        try:
                            get_package(imported_package_id, self.base_api)
                        except:
                            # Deleted
                            delete_package(self.build_context(), imported_package_id)
                
                # Iterate remote packages
                imported_ids = []
                for src in self.iterate_imports():
                    try:
                        mapped = self.map_to_cudc_package(src)
                    except Exception as e:
                        self.logger.error(f'ERROR: Failed to update {mapped["name"]} ({mapped["id"]})')
                        self.logger.exception(e)
                    try:
                        self.import_to_cudc(mapped)
                        self.logger.info(f'INFO: Updated {mapped["name"]} ({mapped["id"]})')
                    except Exception as e:
                        self.logger.error(f'ERROR: Failed to update {mapped["name"]} ({mapped["id"]})')
                        self.logger.exception(e)
                    imported_ids.append(mapped["id"])
                self.import_config.other_data["imported_ids"] = imported_ids
            else:
                self.logger.error(f'ERROR: Remote endpoint is not alive!')
            
        except Exception as e:
            self.logger.error(f'ERROR: Failed:')
            self.logger.exception(e)
            
        self.running = False

