import traceback
import logging
import time

from ckanext.udc_import_other_portals.logger import ImportLogger

from ckanext.udc_import_other_portals.logic.ckan_based.api import import_package, get_package_ids, get_package
from ckanext.udc_import_other_portals.logic.base import BaseImport

from ckan import model, logic
from ckan.common import config
import ckan.lib.helpers as h
import ckan.lib.jobs as jobs

base_logger = logging.getLogger(__name__)


class CKANBasedImport(BaseImport):
    """
    Abstract class for imports
    """

    def __init__(self, base_api):
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

    def run_imports(self, context):
        """
        Run imports for all source packages. Users should not override this.
        """
        self.running = True
        self.logger = ImportLogger(base_logger)
    
        try:
            for src in self.iterate_imports():
            
                try:
                    mapped = self.map_to_cudc_package(src)
                except Exception as e:
                    self.logger.error(f'ERROR: Failed to update {mapped["name"]} ({mapped["id"]})')
                    self.logger.exception(e)
                try:
                    self.import_to_cudc(context, mapped)
                    self.logger.info(f'INFO: Updated {mapped["name"]} ({mapped["id"]})')
                except Exception as e:
                    self.logger.error(f'ERROR: Failed to update {mapped["name"]} ({mapped["id"]})')
                    self.logger.exception(e)
            
        except Exception as e:
            self.logger.error(f'ERROR: Failed:')
            self.logger.exception(e)
            
        self.running = False

