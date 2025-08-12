import traceback
import logging
from ckanext.udc_import_other_portals.model import CUDCImportConfig
from ckanext.udc_import_other_portals.worker.socketio_client import SocketClient
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ckanext.udc_import_other_portals.logger import ImportLogger

from ckanext.udc_import_other_portals.logic.ckan_based.api import get_package_ids, get_package, check_site_alive, get_all_packages
from ckanext.udc_import_other_portals.logic.base import BaseImport, delete_package, get_package as get_self_package, purge_package, get_package_ids_by_import_config_id
from ckan import model


base_logger = logging.getLogger(__name__)


class CKANBasedImport(BaseImport):
    """
    Abstract class for imports
    """

    def __init__(self, context, import_config: 'CUDCImportConfig', job_id: str):
        super().__init__(context, import_config, job_id)
        self.base_api = import_config.other_config.get("base_api")

    def iterate_imports(self):
        """
        Iterate all possible imports from the source api.
        """
        for package in self.all_packages:
            yield package

    def run_imports(self):
        """
        Run imports for all source packages. Users should not override this.
        """
        self.running = True
        self.socket_client = SocketClient(self.job_id)
        self.logger = ImportLogger(base_logger, 0, self.socket_client)
        
        self.all_packages = get_all_packages(self.base_api, cb=lambda x: self.logger.info(x))
        
        # Preprocess the packages, includes filtering and adding extra data
        self.all_packages = [*self.iterate_imports()]
        
        self.packages_ids = [p['id'] for p in self.all_packages]
        # Set the import size for reporting in the frontend
        self.logger.total = self.import_size = len(self.packages_ids)
        
        # Make sure the sockeio server is connected
        while not self.socket_client.registered:
            time.sleep(0.2)
            base_logger.info("Waiting socketio to be connected.")
        base_logger.info("socketio connected.")
        print("self.import_size", self.import_size)

        # Check if packages are deleted from the remote since last import
        if self.import_config.other_data is None:
            self.import_config.other_data = {}
            
    
        try:
            # Make sure remote endpoint is alive
            base_logger.info("Make sure remote endpoint is alive")
            if check_site_alive(self.base_api):
                
                # remote ID -> cudc ID
                imported_id_map = {}
                
                def _delete_all_imports():
                    for package_id_to_delete in get_package_ids_by_import_config_id(self.build_context(), self.import_config.id):
                        try:
                            package_to_delete = get_self_package(self.build_context(), package_id_to_delete)
                            purge_package(self.build_context(), package_id_to_delete)
                            self.logger.finished_one('deleted', package_id_to_delete, package_to_delete['name'], package_to_delete['title'])
                        except Exception as e:
                            self.logger.error(f"ERROR: Failed to get package {package_id_to_delete} from remote")
                            self.logger.exception(e)
                

                if self.import_config.other_data.get("imported_id_map"):
                    imported_id_map = self.import_config.other_data["imported_id_map"]

                elif self.import_config.other_data.get("imported_ids"):
                    # Backward compatibility without imported_id_map
                    # Delete all previous imports
                    _delete_all_imports()

                # In the CKAN based import, we only care about the ids
                # Remove packages that are removed from the remote
                if len(imported_id_map):

                    if self.import_config.other_config.get("delete_previously_imported"):
                        # Delete all packages that were previously imported
                        for package_id_to_remove in imported_id_map.values():
                            _delete_all_imports()
                    else:
                        # Get all packages that are deleted from the remote server, Remove them in ours
                        for package_id_to_remove in [v for k, v in imported_id_map.items() if k not in self.packages_ids]:
                            try:
                                package_to_delete = get_self_package(self.build_context(), package_id_to_remove)
                                # delete_package(self.build_context(), package_id_to_remove)
                                purge_package(self.build_context(), package_id_to_remove)
                                self.logger.finished_one('deleted', package_id_to_remove, package_to_delete['name'], package_to_delete['title'])
                                imported_id_map.pop(package_id_to_remove, None)
                            except Exception as e:
                                self.logger.error(f"ERROR: Failed to get package {package_id_to_remove} from remote")
                                self.logger.exception(e)

                # Iterate remote packages
                base_logger.info("Starting iteration")
                with ThreadPoolExecutor(max_workers=4) as executor:
                    self.socket_client.executor = executor
                    futures = {executor.submit(self.process_package, src): src for src in self.all_packages}
                    for future in as_completed(futures):
                        try:
                            remote_id, mapped_id, name = future.result()
                            imported_id_map[remote_id] = mapped_id
                        except Exception as e:
                            self.logger.error('ERROR: A package import failed.')
                            self.logger.exception(e)
                        
                        if self.socket_client.stop_requested:
                            break
                        
                    # Cleanup
                    self.socket_client.executor = None
                        
                self.import_config.other_data["imported_id_map"] = imported_id_map
            else:
                self.logger.error(f'ERROR: Remote endpoint is not alive!')
            
        except Exception as e:
            self.logger.error(f'ERROR: Failed:')
            self.logger.exception(e)
        finally:
            self.socket_client.disconnect()
            self.socket_client = None
            
        self.running = False
        
    def test(self, use_cache=False):
        from ckanext.udc_import_other_portals.logic.ckan_based.api import (
            get_all_packages,
        )
        self.test = True
        
        cache_file = f"/tmp/all_packages_{self.import_config.id}.json"

        if use_cache:
            # Check if there is a file with all packages
            try:
                import json

                with open(cache_file, "r") as f:
                    self.all_packages = json.load(f)
            except:
                self.all_packages = get_all_packages(self.base_api)
                # save all packages to a file
                import json

                with open(cache_file, "w") as f:
                    json.dump(self.all_packages, f)
        else:
            self.all_packages = get_all_packages(self.base_api)
            # save all packages to a file
            import json

            with open(cache_file, "w") as f:
                json.dump(self.all_packages, f)

        # Iterrate all packages and make sure no error occurred
        for src in self.all_packages:
            mapped = self.map_to_cudc_package(src)

