import logging
import json
from typing import Any, List, Dict
import traceback
import asyncio
import uuid

from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportLog
from ckanext.udc_import_other_portals.jobs import job_run_import

from ckan.types import Context
import ckan.logic as logic
import ckan.authz as authz
import ckan.lib.jobs as jobs

from .base import BaseImport
from .utils import with_exit_stack


log = logging.getLogger(__name__)

# We only allow a single instance running
import_instance: BaseImport = None


@logic.side_effect_free
def cudc_import_configs_get(context: Context, data_dict):
    """
    Get import configs

    Raises:
    logic.NotAuthorized
    """
    model = context["model"]
    user = context["user"]

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    configs = CUDCImportConfig.get_all_configs()
    result = {}
    for config in configs:
        result[config.id] = config.as_dict()
    return result


def cudc_import_config_update(context: Context, data: Dict[str, Any]):
    """
    Create or upadte a new import config.
    Provides an exisint UUID to update the config.
    {
        "import_config": {
            "uuid": "some-uuid",
            "name": "import name",
            "code": "import python code..."
        }
    }
    Provides no UUID to create a new import.
    {
        "import_config": {
            "name": "import name",
            "code": "import python code..."
        }
    }

    Set 'ckanext.udc_import_other_portals.import_config'

    {
        "some-uuid": {
            { "name": "import name", "code": "import python code...", ... },
        }
    }


    Raises:
        logic.NotAuthorized
        logic.ValidationError
        logic.ValidationError
    """
    model = context["model"]
    user = context["user"]

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    userobj = model.User.get(user)

    # Checks
    import_config = data.get("import_config")
    if not isinstance(import_config, dict):
        raise logic.ValidationError("import_config codes should be a dict.")

    if "uuid" in import_config:
        current_config = CUDCImportConfig.get(import_config["uuid"])
        # Provides an existing config with uuid
        if current_config is None:
            raise logic.ValidationError("Import config UUID not found.")
        else:
            current_config.update(**import_config)
            model.Session.add(current_config)
            model.Session.commit()
            return current_config.as_dict()
    else:
        new_config = CUDCImportConfig(created_by=userobj.id, **import_config)
        model.Session.add(new_config)
        model.Session.commit()
        return new_config.as_dict()


def cudc_import_config_delete(context: Context, data: Dict[str, Any]):
    """
    Delete an import config.
    Provides an exisint UUID to delete.
    {
        "uuid": "some-uuid"
    }

    Raises:
        logic.NotAuthorized
        logic.ValidationError
        logic.ValidationError
    """
    model = context["model"]
    user = context["user"]

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    # Checks
    uuid_to_delete = data.get("uuid")
    if not uuid_to_delete:
        raise logic.ValidationError("uuid missing.")

    CUDCImportConfig.delete_by_id(uuid_to_delete)
    model.Session.commit()


def cudc_import_run(context: Context, data: Dict[str, Any]):
    """
    Set 'ckanext.udc_import_other_portals.import_configs'

    Raises:
        logic.NotAuthorized
        logic.ValidationError
        logic.ValidationError
    """

    model = context["model"]
    user = context["user"]

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")
    
    userobj = model.User.get(user)

    # Checks
    if not isinstance(data, dict):
        raise logic.ValidationError("Input should be a dict.")

    uuid = data.get("uuid")
    print(data)

    if not uuid:
        raise logic.ValidationError("uuid should be provided.")

    current_config = CUDCImportConfig.get(uuid)
    if not current_config:
        raise logic.ValidationError("import config does not exists.")
    
    if not current_config.code:
        raise logic.ValidationError("Code does not existed.")
    
    if current_config.is_running:
        raise logic.ValidationError("Another import instance is running.")

    # Submit the job
    jobs.enqueue(job_run_import, [uuid, userobj.id])

    return {"success": True, "message": "Job submitted."}


@logic.side_effect_free
def cudc_import_status_get(context: Context, data: Dict[str, Any]):
    """
    Get the previous or current import status.
    """
    global import_instance
    if import_instance:
        return import_instance.get_status()
    else:
        return {"running": False, "message": "There is no previous import."}

@logic.side_effect_free
def cudc_import_logs_get(context: Context, data_dict):
    """
    Get import logs for a specific import config
    
    Provides an exisint config UUID to check.
    {
        "config_id": "some-uuid"
    }

    Raises:
    logic.NotAuthorized
    """
    model = context["model"]
    user = context["user"]

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")
    
    
    # Checks
    if not isinstance(data_dict, dict):
        raise logic.ValidationError("Input should be a dict.")

    config_id = data_dict.get("config_id")
    
    if not config_id:
        raise logic.ValidationError("config_id should be provided.")
    
    
    logs = CUDCImportLog.get_by_config_id(config_id)
    
    return [log.as_dict() for log in logs]



def cudc_import_log_delete(context: Context, data: Dict[str, Any]):
    """
    Delete an import config log.
    Provides an exisint UUID to delete.
    {
        "id": "some-uuid"
    }

    Raises:
        logic.NotAuthorized
        logic.ValidationError
        logic.ValidationError
    """
    model = context["model"]
    user = context["user"]

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    # Checks
    id_to_delete = data.get("id")
    if not id_to_delete:
        raise logic.ValidationError("id missing.")

    CUDCImportLog.delete_by_id(id_to_delete)
    model.Session.commit()
