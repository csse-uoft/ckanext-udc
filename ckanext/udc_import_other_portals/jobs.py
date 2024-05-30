import logging
import json
from typing import Any, List, Dict, cast
from datetime import datetime

from ckanext.udc_import_other_portals.logger import ImportLogger

from ckan.types import Context
import ckan.logic as logic
import ckan.authz as authz
import ckan.lib.jobs as jobs
import ckan.model as model

from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportLog
from .logic.base import BaseImport


def job_run_import(import_config_id: str, run_by: str):
    """
    Run imports.
    Raises:
        logic.NotAuthorized
        logic.ValidationError
        logic.ValidationError
    """
    logger = ImportLogger()
    import_log = CUDCImportLog(import_config_id=import_config_id, 
                               run_at=datetime.utcnow(),
                               run_by=run_by)
    userobj = model.User.get(run_by)
    
    import_instance = None
    try:
        if not import_config_id:
            raise logger.exception(
                logic.ValidationError("import_config_id should be provided.")
            )

        import_config = CUDCImportConfig.get(import_config_id)

        if not import_config:
            raise logger.exception(
                logic.ValidationError(f"import_config not found: {import_config_id}")
            )

        # Check existing import instance
        if import_config.is_running:
            raise logger.exception(logic.ValidationError("Already running."))

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
            import_instance = DefaultImportClass()
            context = cast(
                Context,
                {
                    "model": model,
                    "session": model.Session,
                    "user": userobj.name,
                    "auth_user_obj": userobj,
                },
            )
            import_instance.run_imports(context)
        except Exception as e:
            raise logger.exception(e)

    except Exception as e:
        raise logger.exception(e)
    finally:
        # Finished
        if import_instance:
            import_log.has_error = logger.has_error or import_instance.logger.has_error
            import_log.has_warning = logger.has_warning or import_instance.logger.has_warning
            import_log.logs = "\n".join([*logger.logs, *import_instance.logger.logs])
        else:
            import_log.has_error = logger.has_error
            import_log.has_warning = logger.has_warning
            import_log.logs = "\n".join([*logger.logs].join("\n"))
        import_log.finished_at = datetime.utcnow()
        print(import_log.logs)
        
        model.Session.add(import_log)
        model.Session.commit()
