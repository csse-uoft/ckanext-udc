from ckanext.udc_import_other_portals.logger import ImportLogger, generate_trace
from ckanext.udc_import_other_portals.model import CUDCImportConfig
from ckanext.udc_import_other_portals.worker.socketio_client import SocketClient
import ckan.plugins.toolkit as toolkit
from ckan.types import Context
import ckan.logic as logic
import ckan.model as model
from ckan.common import current_user
from ckan.lib.search.common import SearchIndexError
from sqlalchemy.exc import IntegrityError

import threading
import time
from typing import List, Dict, cast
from .deduplication import find_duplicated_packages, process_duplication

import logging
import uuid

base_logger = logging.getLogger(__name__)

lock = threading.Lock()

class ImportError(ValueError):
    pass


def get_package(context: Context, package_id: str = None, package_name: str = None):
    if not package_id and not package_name:
        raise ValueError("Either package_id or package_name should be provided.")
    if package_id and package_name:
        raise ValueError("Only one of package_id or package_name should be provided.")
    if package_id:
        data_dict = {"id": package_id}
    else:
        data_dict = {"name": package_name}
    logic.check_access("package_show", context, data_dict=data_dict)
    package_dict = logic.get_action("package_show")(context, data_dict)

    # Prevent the package with the same name but different id (the provided id is treated as a name)
    if package_id and package_dict["id"] != package_id:
        raise ValueError(f"Package id={package_id} is not found.")

    return package_dict

def iterate_package_by_import_config_id(context: Context, import_id: str):
    """
    Search for a package by its import config ID.
    """
    def _get_package(rows, offset):
        fq = f'cudc_import_config_id:"{import_id}"'
        logic.check_access("package_search", context, {"fq": fq, "start": offset, "rows": rows})
        package = logic.get_action("package_search")(context, {"fq": fq, "start": offset, "rows": rows})
        return package["results"]

    # Get all packages
    rows = 500
    offset = 0
    while True:
        packages = _get_package(rows, offset)
        if not packages:
            break
        yield from packages
        offset += rows

def get_package_ids_by_import_config_id(context: Context, import_id: str):
    """
    Get all package IDs by import config ID.
    """
    return [pkg["id"] for pkg in iterate_package_by_import_config_id(context, import_id)]


def check_existing_package_id_or_name(context, id: str = None, name: str = None):
    if not id and not name:
        raise ValueError("Either id or name should be provided.")
    if id and name:
        raise ValueError("Only one of id or name should be provided.")
    try:
        get_package(context, id, name)
        return True
    except Exception as e:
        pass
    return False


def import_package(context: Context, package: dict, merge: bool = False):
    """
    :param merge: Merge with the fields from the existing package
    """
    is_id_existed = check_existing_package_id_or_name(context, id=package["id"])
    is_name_existed = check_existing_package_id_or_name(context, name=package["name"])
    print(is_id_existed, is_name_existed)

    if not is_id_existed and is_name_existed:
        raise ImportError(
            f'There is a package name={package["name"]} with the "different id" but the "same name".'
        )

    existing_package = {}
    action = "package_create"

    try:
        existing_package = get_package(context, package["id"])
        # If there is an existing package, we should call 'package_update'
        action = "package_update"
    except:
        pass

    if merge:
        existing_package.update(package)
    else:
        existing_package = package

    logic.check_access("package_show", context, data_dict=existing_package)
    logic.check_access(action, context, data_dict=existing_package)
    # print(action, existing_package)
    try:
        logic.get_action(action)(context, existing_package)
    except IntegrityError as e:
        base_logger.error(f"IntegrityError: {e}")
        # Rollback session to make sure future transactions are not affected
        model.Session.rollback()
        raise e
    return "created" if action == "package_create" else "updated"


def delete_package(context: Context, package_id: str):
    logic.check_access("package_delete", context, data_dict={"id": package_id})
    logic.get_action("package_delete")(context, {"id": package_id})
    

def purge_package(context: Context, package_id: str):
    """
    Purge a package from the database and search index.
    """
    logic.check_access("dataset_purge", context, data_dict={"id": package_id})
    logic.get_action("dataset_purge")(context, {"id": package_id})

def get_organization(context: Context, organization_id: str = None):
    data_dict = {"id": organization_id}
    logic.check_access("organization_show", context, data_dict=data_dict)
    return logic.get_action("organization_show")(context, data_dict)


def get_organization_ids(context: Context):
    logic.check_access("organization_list", context)
    return logic.get_action("organization_list")(context)


def ensure_organization(context: Context, organization: dict):
    with lock:
        if not context:
            # testing environment, do not create organization
            return
        logic.check_access("organization_list", context)
        organization_ids = logic.get_action("organization_list")(context)
        for organization_id in organization_ids:
            if organization_id == organization["id"]:
                return

        logic.check_access("organization_create", context, data_dict=organization)
        try:
            logic.get_action("organization_create")(context, organization)
        except IntegrityError:
            # Another process created it; re-check and continue.
            model.Session.rollback()
            organization_ids = logic.get_action("organization_list")(context)
            if organization["id"] not in organization_ids:
                raise


class BaseImport:
    """
    Abstract class that manages logging and provides interface to backend APIs
    """

    logger = ImportLogger(base_logger)
    import_size = 0
    running = False
    socket_client: SocketClient = None

    def __init__(self, context, import_config: "CUDCImportConfig", job_id):
        self.context = context
        self.import_config = import_config
        self.job_id = job_id
        self._imported_map_pending = 0
        self._last_imported_map_persist = 0.0

    def build_context(self):
        if not self.context:
            # testing environment, do not create context
            return
        userobj = model.User.get(self.import_config.run_by)
        context = cast(
            Context,
            {
                "model": model,
                "session": model.Session,
                "user": userobj.name,
                "auth_user_obj": userobj,
            },
        )
        return context

    def _persist_imported_id_map(self, imported_id_map, *, force: bool = False):
        if not self.import_config:
            return
        if self.import_config.other_data is None:
            self.import_config.other_data = {}

        now = time.monotonic()
        if not force:
            # Throttle writes so we don't commit on every dataset.
            if self._imported_map_pending < 25 and (now - self._last_imported_map_persist) < 30:
                return

        # Persist the mapping to survive main-process restarts during long imports.
        self.import_config.other_data["imported_id_map"] = imported_id_map
        if self.import_config.other_data.get("imported_ids"):
            del self.import_config.other_data["imported_ids"]

        try:
            model.Session.add(self.import_config)
            model.Session.commit()
            self._imported_map_pending = 0
            self._last_imported_map_persist = now
        except Exception:
            # Failed commit should not poison future DB operations.
            model.Session.rollback()

    def map_to_cudc_package(self, src: dict, target: dict):
        """
        Map source package to cudc package.

        Args:
            src (dict): The source package that needs to be mapped.
        """
        raise NotImplementedError()

    def process_package(self, src, mapped_id=None):
        """
        Process a single package: map it to cudc package and import it.

        Args:
            src (dict): The source package to process.

        Returns:
            str: The ID of the mapped package.
        """
        # Some defaults
        target = {
            "owner_org": self.import_config.owner_org,
            "type": "catalogue",
            "license_id": "notspecified",
        }
        platform = self.import_config.platform
        if platform == "ckan":
            org_import_mode = self.import_config.other_config.get("org_import_mode")
            org_mapping = self.import_config.other_config.get("org_mapping") or {}

            if org_import_mode == "importToOwnOrg":
                if org_mapping.get(src["owner_org"]):
                    target["owner_org"] = org_mapping[src["owner_org"]]
                else:
                    # Use the same organization id
                    target["owner_org"] = src["owner_org"]
                    
                    
                    query = (
                        model.Session.query(model.Group)
                        .filter(model.Group.id == src["owner_org"])
                        .filter(model.Group.is_organization == True)
                    )
                    org = query.first()
                    
                    # Create the organization if not exists
                    if org is None:
                        organization = self.before_create_organization(src["organization"], src)
                        ensure_organization(
                            self.build_context(),
                            {
                                "id": organization["id"],
                                "name": organization["name"],
                                "title": organization["title"],
                                "description": organization["description"],
                            },
                        )
                        model.Session.commit()

        try:
            mapped = self.map_to_cudc_package(src, target)
        except Exception as e:
            self.logger.error(f"ERROR: Failed to map package from source.")
            self.logger.exception(e)
            self.logger.finished_one(
                "errored",
                src.get("id"),  # Using source package info
                src.get("name", ""),
                src.get("title", ""),
                f"Failed to map package from source.\n{generate_trace(e)}",
            )
            raise
        
        if not mapped:
            self.logger.info(
                f"INFO: Skipped {src['name']} ({src['id']}) - map_to_cudc_package returned None"
            )
            return None
            
        # Replace with a new UUID
        mapped["cudc_import_remote_id"] = mapped["id"]
        # Preserve the ID if exists
        mapped["id"] = mapped_id if mapped_id else str(uuid.uuid4())
        # if mapped_id:
        #     print("Mapped ID:", mapped_id)

        try:
            action_done, duplications_log, err_msg = self.import_to_cudc(mapped)
            self.logger.info(f'INFO: Updated {mapped["name"]} ({mapped["id"]})')
            if err_msg:
                # Package is imported but deduplications run into issues
                self.logger.error("Package is imported but deduplications run into issues." + err_msg)
                self.logger.finished_one(
                    "errored",
                    mapped["id"],
                    mapped["name"],
                    mapped["title"],
                    logs=err_msg,
                    duplications=duplications_log,
                )
            else:
                self.logger.finished_one(
                    action_done,
                    mapped["id"],
                    mapped["name"],
                    mapped["title"],
                    duplications=duplications_log,
                )

            return src["id"], mapped["id"], mapped["name"]
        except Exception as e:
            self.logger.error(
                f'ERROR: Failed to update {mapped["name"]} ({mapped["id"]})'
            )
            self.logger.exception(e)
            self.logger.finished_one(
                "errored",
                mapped["id"],
                mapped["name"],
                mapped["title"],
                f'ERROR: Failed to update {mapped["name"]} ({mapped["id"]})\n{generate_trace(e)}',
            )
            raise

    def import_to_cudc(self, package, merge=False):
        """
        Call the API to do the actual import for a single package.
        """

        # Save which import config it used
        package["cudc_import_config_id"] = self.import_config.id

        # Use different context for each package import
        # This will replace with the exisiting package
        action_done = import_package(self.build_context(), package, merge)
        duplications_log = None
        err_msg = None

        # Duplication check
        duplications, reason = find_duplicated_packages(
            self.build_context(), package, self.import_config.id
        )

        if duplications:

            duplications_log = [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "title": p["title"],
                    "reason": reason,
                }
                for p in duplications["results"]
            ]

            if duplications["count"] >= 20:
                err_msg = f'Skipped: More than 20 packages are duplicated for package {package["name"]}({package["id"]}), {reason}'
                err_msg += ", ".join(
                    [f'{p["name"]}({p["id"]})' for p in duplications["results"]]
                )
                self.logger.error(err_msg)
            else:
                self.logger.warning(
                    f'Found {duplications["count"]} duplication(s) for package {package["name"]}({package["id"]}), {reason}'
                )
                self.logger.warning(
                    ", ".join(
                        [f'{p["name"]}({p["id"]})' for p in duplications["results"]]
                    )
                )

                try:
                    process_duplication(
                        self.build_context(), [package, *duplications["results"]]
                    )
                except Exception as e:
                    self.logger.error(f"Failed to create unified package.")
                    self.logger.exception(e)
                    err_msg = f"Package is imported but failed to create a unified package.\n{generate_trace(e)}"

        return action_done, duplications_log, err_msg

    def run_imports(self):
        """
        Run imports for all source packages.
        """
        raise NotImplemented()
    
    def before_create_organization(self, organization: dict, related_package: dict):
        """
        A hook to modify the organization before creating it.
        """
        return organization


def ensure_license(context, license_id, license_title, license_url, check=True):
    """Ensure that the license exists in the database."""
    with lock:
        if not context:
            # tesing environment, do not create license
            return
        licenses = logic.get_action("licenses_get")(context)
        for license in licenses:
            if license["id"] == license_id:
                return
        try:
            logic.get_action("license_create")(
                context, {"id": license_id, "title": license_title, "url": license_url}
            )
        except IntegrityError:
            # Another process created it; re-check and continue.
            model.Session.rollback()
            licenses = logic.get_action("licenses_get")(context)
            if not any(l.get("id") == license_id for l in licenses):
                raise
        except Exception:
            # Keep behavior for unexpected errors.
            pass
        return
