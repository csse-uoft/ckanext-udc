import logging
import uuid
from datetime import datetime
from typing import Any, List, Dict

from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportJob
from ckanext.udc_import_other_portals.jobs import job_run_import, delete_organization_packages

from ckan.types import Context
import ckan.logic as logic
import ckan.authz as authz
import ckan.lib.jobs as jobs

from .base import BaseImport


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
    
    # TODO: check if any package is imported by this config

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

    config_uuid = data.get("uuid")
    print(data)

    if not config_uuid:
        raise logic.ValidationError("uuid should be provided.")

    current_config = CUDCImportConfig.get(config_uuid)
    if not current_config:
        raise logic.ValidationError("import config does not exists.")
    
    if not current_config.code:
        raise logic.ValidationError("Code does not existed.")
    
    # if current_config.is_running:
    #     raise logic.ValidationError("Another import instance is running.")
    
    current_config.is_running = True
    model.Session.add(current_config)
    

    # Init the import log instance
    job_uuid = str(uuid.uuid4())
    import_log_data = {
        "import_config_id": config_uuid,
        "run_at": datetime.utcnow(),
        "run_by": userobj.id,
        "id": job_uuid,
        "is_running": True
    }
    import_log = CUDCImportJob(**import_log_data)
    model.Session.add(import_log)
    model.Session.commit()

    # Submit the job
    jobs.enqueue(job_run_import, [config_uuid, userobj.id, job_uuid])

    return {"success": True, "message": "Job submitted."}


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
    
    
    logs = CUDCImportJob.get_by_config_id(config_id)
    
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

    CUDCImportJob.delete_by_id(id_to_delete)
    model.Session.commit()

def cudc_clear_organization(context: Context, data: Dict[str, Any]):
    """
    Clear all packages for a specific organization
    {
        "organization": "organization_id"
    }

    Raises:
        logic.NotAuthorized
        logic.ValidationError
        
    e.g.
    await (await fetch("/api/3/action/cudc_clear_organization", {method: 'post', headers: {"Content-Type": "application/json"}, body: JSON.stringify({organization: 'open-alberta'})})).json()
    """
    model = context["model"]
    user = context["user"]
    userobj = model.User.get(user)

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    # Checks
    org_id = data.get("organization")
    if not org_id:
        raise logic.ValidationError("organization missing.")
    
    jobs.enqueue(delete_organization_packages, [userobj.id, org_id])
    
    # delete_organization_packages(context, org_id)
    
    return {"success": True, "message": "Organization packages deleted."}