from ckanext.udc_import_other_portals.logger import ImportLogger
import ckan.plugins.toolkit as toolkit
from ckan.types import Context
import ckan.logic as logic
import ckan.model as model
from ckan.common import current_user

from typing import List, Dict, cast

import logging

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
        base_logger.error("!!!!!!!!")
        base_logger.exception(e)
        pass
    return False


def import_package(context: Context, package: dict, merge: bool = False):
    """
    :param merge: Merge with the existing package
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

    logic.check_access(action, context, data_dict=existing_package)
    logic.get_action(action)(context, existing_package)


class BaseImport:
    """
    Abstract class that manages logging and provides interface to backend APIs
    """

    logger = ImportLogger(base_logger)
    import_size = 0
    running = False
    
    # TODO: remove get status
    def get_logs(self):
        return "\n".join(self.logger.logs)

    def get_status(self):
        return {
            "running": self.running,
            "current": len(self.logs),
            "size": self.import_size,
            "logs": self.get_logs(),
        }

    def import_to_cudc(self, context, package, merge=False):
        """
        Call the API to do the actual import.
        """
        # This will replace with the exisiting package
        import_package(context, package, merge)

    def run_imports(self, context):
        """
        Run imports for all source packages.
        """
        raise NotImplemented()
