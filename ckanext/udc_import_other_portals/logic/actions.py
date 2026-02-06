import logging
import uuid
from datetime import datetime
from typing import Any, List, Dict, Optional

import requests
from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportJob
from ckanext.udc_import_other_portals.jobs import job_run_import, delete_organization_packages

from ckan.types import Context
import ckan.logic as logic
import ckan.authz as authz
import ckan.lib.jobs as jobs
from sqlalchemy.orm import load_only

from .base import BaseImport
from ckanext.udc_import_other_portals.scheduler import sync_cron_jobs
from ckanext.udc.solr.config import get_udc_langs, get_default_lang
from babel import Locale


log = logging.getLogger(__name__)

# We only allow a single instance running
import_instance: BaseImport = None


def _language_label(code: str, fallback: str) -> str:
    default_lang = (fallback or get_default_lang() or "en").replace("-", "_")
    try:
        display_locale = Locale.parse(default_lang)
        target = Locale.parse(code.replace("-", "_"))
        label = target.get_display_name(display_locale)
        if isinstance(label, str) and label:
            return label[0].upper() + label[1:]
    except Exception:
        pass
    return code.upper()


def _normalize_language(value: str, allowed: List[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower().replace("_", "-")
    allowed_map = {lang.lower(): lang for lang in allowed}
    if normalized in allowed_map:
        return allowed_map[normalized]
    if "-" in normalized:
        prefix = normalized.split("-", 1)[0]
        if prefix in allowed_map:
            return allowed_map[prefix]
    return None


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


@logic.side_effect_free
def cudc_import_configs_list(context: Context, data_dict):
    """
    List import configs with minimal fields for UI lists.
    """
    model = context["model"]
    user = context["user"]

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    configs = (
        model.Session.query(CUDCImportConfig)
        .options(load_only("id", "name", "platform", "updated_at", "other_config"))
        .order_by(CUDCImportConfig.created_at)
        .all()
    )
    results: List[Dict[str, Any]] = []
    for config in configs:
        auto_arcgis = bool((config.other_config or {}).get("auto_arcgis"))
        results.append(
            {
                "id": config.id,
                "name": config.name,
                "platform": config.platform,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                "auto_arcgis": auto_arcgis,
            }
        )
    return results


@logic.side_effect_free
def cudc_import_language_options(context: Context, data_dict):
    """
    List supported language codes and labels for import configs.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    langs = get_udc_langs()
    default_lang = langs[0] if langs else get_default_lang() or "en"
    labels = {code: _language_label(code, default_lang) for code in langs}
    return {"languages": langs, "default": default_lang, "labels": labels}


@logic.side_effect_free
def cudc_import_config_show(context: Context, data_dict):
    """
    Get a single import config by uuid.
    """
    user = context["user"]

    # If not sysadmin.
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    if not isinstance(data_dict, dict):
        raise logic.ValidationError("Input should be a dict.")

    config_id = data_dict.get("uuid") or data_dict.get("id")
    if not config_id:
        raise logic.ValidationError("uuid should be provided.")

    config = CUDCImportConfig.get(config_id)
    if not config:
        raise logic.ValidationError("import config does not exists.")

    return config.as_dict()


@logic.side_effect_free
def cudc_import_remote_orgs_list(context: Context, data_dict):
    """
    List organizations from a remote CKAN instance via server-side request.
    """
    user = context["user"]
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    if not isinstance(data_dict, dict):
        raise logic.ValidationError("Input should be a dict.")

    base_api = data_dict.get("base_api")
    if not isinstance(base_api, str) or not base_api.strip():
        raise logic.ValidationError("base_api should be provided.")

    base = base_api.strip().rstrip("/")
    if base.endswith("/api/3/action"):
        url = f"{base}/organization_list?all_fields=true&limit=10000"
    elif base.endswith("/api/3"):
        url = f"{base}/action/organization_list?all_fields=true&limit=10000"
    elif base.endswith("/api"):
        url = f"{base}/3/action/organization_list?all_fields=true&limit=10000"
    else:
        url = f"{base}/api/3/action/organization_list?all_fields=true&limit=10000"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        log.warning("Failed to fetch remote organizations from %s: %s", url, exc)
        return []

    if not isinstance(payload, dict) or payload.get("success") is False:
        return []

    orgs = payload.get("result") or []
    results = []
    for org in orgs:
        if not isinstance(org, dict):
            continue
        if org.get("package_count", 0) <= 0:
            continue
        name = org.get("title") or org.get("display_name") or org.get("name") or org.get("id")
        results.append(
            {
                "id": org.get("id"),
                "name": name or "",
                "description": org.get("description") or "",
            }
        )
    return results


@logic.side_effect_free
def cudc_organization_list_min(context: Context, data_dict):
    """
    Return minimal organization fields for UI selectors.
    """
    model = context["model"]
    user = context["user"]

    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    groups = (
        model.Session.query(model.Group)
        .filter(model.Group.type == "organization")
        .filter(model.Group.state == "active")
        .options(load_only("id", "name", "title", "description"))
        .order_by(model.Group.title)
        .all()
    )

    results: List[Dict[str, Any]] = []
    for group in groups:
        title = group.title or group.name or ""
        results.append(
            {
                "id": group.id,
                "name": group.name,
                "title": title,
                "display_name": title,
                "description": group.description or "",
            }
        )
    return results


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

    other_config = import_config.get("other_config") or {}
    if isinstance(other_config, dict) and other_config.get("language"):
        allowed_langs = get_udc_langs()
        normalized = _normalize_language(other_config.get("language"), allowed_langs)
        if not normalized:
            raise logic.ValidationError({"language": ["Unsupported language."]})
        other_config["language"] = normalized
        import_config["other_config"] = other_config

    if "uuid" in import_config:
        current_config = CUDCImportConfig.get(import_config["uuid"])
        # Provides an existing config with uuid
        if current_config is None:
            raise logic.ValidationError("Import config UUID not found.")
        else:
            current_config.update(**import_config)
            model.Session.add(current_config)
            model.Session.commit()
            sync_cron_jobs()
            return current_config.as_dict()
    else:
        new_config = CUDCImportConfig(created_by=userobj.id, **import_config)
        model.Session.add(new_config)
        model.Session.commit()
        sync_cron_jobs()
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
    sync_cron_jobs()


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
