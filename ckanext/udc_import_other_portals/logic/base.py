from ckanext.udc_import_other_portals.logger import ImportLogger
import ckan.plugins.toolkit as toolkit
from ckan.types import Context
import ckan.logic as logic
import ckan.model as model
from ckan.common import current_user
from ckan.lib.search.common import SearchIndexError

from typing import List, Dict, cast
from .deduplication import find_duplicated_packages, process_duplication

import logging
import time

base_logger = logging.getLogger(__name__)


class ImportError(ValueError):
    pass


def get_package(context: Context, package_id: str):
    data_dict = {"id": package_id}
    logic.check_access("package_show", context, data_dict=data_dict)
    package_dict = logic.get_action("package_show")(context, data_dict)
    return package_dict


def check_existing_package_id_or_name(context, id_or_name: str):
    try:
        get_package(context, id_or_name)
        return True
    except Exception as e:
        # base_logger.error("!!!!!!!!")
        # base_logger.exception(e)
        pass
    return False


def import_package(context: Context, package: dict, merge: bool = False):
    """
    :param merge: Merge with the fields from the existing package
    """
    is_id_existed = check_existing_package_id_or_name(context, package["id"])
    is_name_existed = check_existing_package_id_or_name(context, package["name"])
    print(is_id_existed, is_name_existed)

    if not is_id_existed and is_name_existed:
        raise ImportError(
            f"There is an {is_name_existed} with the 'different id' but the 'same name'."
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

    logic.get_action(action)(context, existing_package)


def delete_package(context: Context, package_id: str):
    logic.check_access("package_delete", context, data_dict={"id": package_id})
    logic.get_action("package_delete")(context, {"id": package_id})


class BaseImport:
    """
    Abstract class that manages logging and provides interface to backend APIs
    """

    logger = ImportLogger(base_logger)
    import_size = 0
    running = False

    def __init__(self, context, import_config):
        self.context = context
        self.import_config = import_config

    def build_context(self):
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

    def import_to_cudc(self, package, merge=False):
        """
        Call the API to do the actual import for a single package.
        """
        
        # Save which import config it used
        package["cudc_import_config_id"] = self.import_config.id
        
        # Use different context for each package import
        # This will replace with the exisiting package
        import_package(self.build_context(), package, merge)

        # Duplication check
        duplication_result, reason = find_duplicated_packages(self.build_context(), package, self.import_config.id)
        if duplication_result:
            
            if duplication_result["count"] >= 20:
                self.logger.error(f'Skipped: More than 20 packages are duplicated for package {package["name"]}({package["id"]}), {reason}')
                self.logger.error(', '.join([f'{p["name"]}({p["id"]})' for p in duplication_result["results"]]))
                return
            
            self.logger.warning(f'Found {duplication_result["count"]} duplication(s) for package {package["name"]}({package["id"]}), {reason}')
            self.logger.warning(', '.join([f'{p["name"]}({p["id"]})' for p in duplication_result["results"]]))
            
            try:
                process_duplication(self.build_context(), [package, *duplication_result["results"]])
            except:
                self.logger.error(f'Failed to create unified package.')
                raise
            



    def run_imports(self):
        """
        Run imports for all source packages.
        """
        raise NotImplemented()
