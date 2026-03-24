from typing import Any, List, Dict, Optional, cast
from datetime import datetime

from ckanext.udc_import_other_portals.logger import ImportLogger
from ckanext.udc_import_other_portals.logic.base import (
    delete_package,
    get_package,
    get_package_ids_by_import_config_id,
    purge_package,
)
from ckanext.udc_import_other_portals.logic.arcgis_based.api import get_dataset

from ckan.types import Context
import ckan.logic as logic
import ckan.model as model

from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportJob


def _build_context_for_user(user_id: str) -> Context:
    """Build a CKAN action context for a specific user ID."""
    # Background jobs need the same action context shape as API-triggered work.
    userobj = model.User.get(user_id)
    return cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": userobj.name,
            "auth_user_obj": userobj,
        },
    )


def _source_last_updated_iso(attributes: Dict[str, Any]) -> Optional[str]:
    """Convert upstream ArcGIS modified fields to the ISO format used in extras."""
    # ArcGIS uses either itemModified or modified depending on item type.
    modified_ms = (attributes or {}).get("itemModified") or (attributes or {}).get("modified")
    if not modified_ms:
        return None
    return datetime.utcfromtimestamp(modified_ms / 1000).isoformat()


def _update_import_extra(extras: List[Dict[str, Any]], key: str, value: str) -> List[Dict[str, Any]]:
    """Replace or append a single key/value pair inside the import extras list."""
    # Replace any existing key so package_patch stays idempotent across refreshes.
    updated = [item for item in extras if item.get("key") != key]
    updated.append({"key": key, "value": value})
    return updated


def job_run_import(import_config_id: str, run_by: str, job_id: str):
    """
    Run imports.
    Raises:
        logic.NotAuthorized
        logic.ValidationError
        logic.ValidationError
    """
    logger = ImportLogger()
    userobj = model.User.get(run_by)

    import_instance = None
    try:
        if not import_config_id:
            raise logger.exception(
                logic.ValidationError("import_config_id should be provided.")
            )

        import_config: "CUDCImportConfig" = CUDCImportConfig.get(import_config_id)

        if not import_config:
            raise logger.exception(
                logic.ValidationError(f"import_config not found: {import_config_id}")
            )

        import_log = CUDCImportJob.get(job_id)
        run_flags = (import_log.other_data or {}) if import_log else {}
        import_config._delete_previously_imported_for_run = bool(
            run_flags.get("delete_previously_imported_once")
        )

        # Check existing import instance
        # if import_config.is_running:
        #     raise logger.exception(logic.ValidationError("Already running."))

        code = import_config.code
        if not code:
            raise logger.exception(logic.ValidationError("Code does not existed."))

        # Run the provided code
        locals = {}
        try:
            exec(code, globals(), locals)

        except Exception as e:
            raise logger.exception(e)

        DefaultImportClass = locals.get("DefaultImportClass")

        if not DefaultImportClass:
            raise logic.ValidationError("DefaultImportClass is not defined.")

        try:
            context = cast(
                Context,
                {
                    "model": model,
                    "session": model.Session,
                    "user": userobj.name,
                    "auth_user_obj": userobj,
                },
            )
            import_config.run_by = run_by
            import_instance = DefaultImportClass(context, import_config, job_id)
            import_instance.run_imports()
            model.Session.add(import_config)
            model.Session.commit()

        except Exception as e:
            raise logger.exception(e)

    except Exception as e:
        raise logger.exception(e)
    finally:
        # Finished
        import_log = CUDCImportJob.get(job_id)
        import_log.is_running = False
        if import_instance and import_instance.import_config:
            import_instance.import_config.is_running = False
            model.Session.add(import_instance.import_config)
        elif import_config_id:
            config = CUDCImportConfig.get(import_config_id)
            if config:
                config.is_running = False
                model.Session.add(config)

        if import_instance:
            import_log.has_error = logger.has_error or import_instance.logger.has_error
            import_log.has_warning = (
                logger.has_warning or import_instance.logger.has_warning
            )
            import_log.logs = "\n".join([*logger.logs, *import_instance.logger.logs])
        else:
            import_log.has_error = logger.has_error
            import_log.has_warning = logger.has_warning
            import_log.logs = "\n".join([*logger.logs])
        import_log.finished_at = datetime.utcnow()
        print(import_log.logs)

        model.Session.add(import_log)
        model.Session.commit()


def job_refresh_arcgis_source_last_updated(import_config_id: str, run_by: str, job_id: str):
    """Refresh only source_last_updated for packages belonging to one ArcGIS import config."""
    # This job intentionally avoids remapping/importing datasets and only updates import extras.
    logger = ImportLogger()
    import_log = CUDCImportJob.get(job_id)
    config = CUDCImportConfig.get(import_config_id)

    try:
        if not import_config_id:
            raise logger.exception(logic.ValidationError("import_config_id should be provided."))
        if not config:
            raise logger.exception(logic.ValidationError(f"import_config not found: {import_config_id}"))

        other_config = config.other_config or {}
        if (config.platform or "").lower() != "arcgis":
            raise logger.exception(logic.ValidationError("Source-last-updated refresh only supports ArcGIS configs."))

        base_api = other_config.get("base_api")
        if not base_api:
            raise logger.exception(logic.ValidationError("base_api is required in import configuration."))

        context = _build_context_for_user(run_by)
        package_ids = get_package_ids_by_import_config_id(context, import_config_id)
        refreshed = 0
        skipped = 0

        for package_id in package_ids:
            package = get_package(context, package_id=package_id)
            remote_id = package.get("cudc_import_remote_id")
            if not remote_id:
                skipped += 1
                logger.warning(f"Skip package {package_id}: missing cudc_import_remote_id")
                continue

            dataset = get_dataset(remote_id, base_api)
            if not dataset:
                skipped += 1
                logger.warning(f"Skip package {package_id}: upstream dataset not found ({remote_id})")
                continue

            source_last_updated = _source_last_updated_iso(dataset.get("attributes") or {})
            if not source_last_updated:
                skipped += 1
                logger.warning(f"Skip package {package_id}: upstream dataset has no modified timestamp ({remote_id})")
                continue

            import_extras = package.get("udc_import_extras") or []
            if not isinstance(import_extras, list):
                import_extras = []
            # Keep the existing import extras payload intact and only replace this one key.
            updated_import_extras = _update_import_extra(
                import_extras,
                "source_last_updated",
                source_last_updated,
            )

            logic.get_action("package_patch")(
                context,
                {
                    "id": package_id,
                    "udc_import_extras": updated_import_extras,
                },
            )
            refreshed += 1

        logger.info(
            f"Source last updated refresh finished for config {import_config_id}: refreshed={refreshed}, skipped={skipped}"
        )
        import_log.has_error = logger.has_error
        import_log.has_warning = logger.has_warning
        import_log.logs = "\n".join(logger.logs)
        import_log.other_data = {
            **(import_log.other_data or {}),
            "task_type": "source_last_updated_refresh",
            "refreshed": refreshed,
            "skipped": skipped,
        }
    except Exception as e:
        logger.exception(e)
        import_log.has_error = True
        import_log.has_warning = logger.has_warning
        import_log.logs = "\n".join(logger.logs)
        import_log.other_data = {
            **(import_log.other_data or {}),
            "task_type": "source_last_updated_refresh",
        }
    finally:
        import_log.is_running = False
        import_log.finished_at = datetime.utcnow()
        if config:
            config.is_running = False
            model.Session.add(config)
        model.Session.add(import_log)
        model.Session.commit()


def delete_organization_packages(userid: str, organization_id: str):
    """
    Delete all packages for the given organization.
    """

    userobj = model.User.get(userid)

    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "user": userobj.name,
            "auth_user_obj": userobj,
        },
    )

    packages = logic.get_action("package_search")(
        context, {"q": f"organization:{organization_id}", "rows": 50000}
    )
    print("number of packages to delete", len(packages["results"]))
    while len(packages["results"]) > 0:
        number_of_packages = len(packages["results"])
        print("number of packages to delete", number_of_packages)
        for package in packages["results"]:
            print(f"Deleting package {package['id']} - {package['title']}")
            # delete_package(context, package["id"])
            purge_package(context, package["id"])

        packages = logic.get_action("package_search")(
            context, {"q": f"organization:{organization_id}", "rows": 50000}
        )
