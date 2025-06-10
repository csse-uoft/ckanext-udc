from typing import Any, List, Dict, cast
from datetime import datetime

from ckanext.udc_import_other_portals.logger import ImportLogger
from ckanext.udc_import_other_portals.logic.base import delete_package, purge_package

from ckan.types import Context
import ckan.logic as logic
import ckan.model as model

from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportJob


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
