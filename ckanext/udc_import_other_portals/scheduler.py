import logging
import uuid
from datetime import datetime
from typing import Optional

import ckan.lib.jobs as jobs
import ckan.model as model
from rq_scheduler import Scheduler

from ckanext.udc_import_other_portals.jobs import job_run_import
from ckanext.udc_import_other_portals.logic.arcgis_based.settings import (
    get_global_source_last_updated_cron,
)
from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportJob

log = logging.getLogger(__name__)

SCHEDULE_PREFIX = "udc-import:"
SOURCE_LAST_UPDATED_CRON_KEY = "source_last_updated_cron_schedule"
ARCGIS_AUTO_IMPORT_FLAG = "auto_arcgis"


def _start_scheduled_job(import_config_id: str, run_by: str, task_type: str) -> Optional[str]:
    """Create the shared run-log record used by scheduled import tasks."""
    # Full imports and lightweight refreshes both use the same run-log model.
    config = CUDCImportConfig.get(import_config_id)
    if not config:
        log.warning("Cron %s skipped: config not found %s", task_type, import_config_id)
        return None
    if config.is_running:
        log.info("Cron %s skipped: already running %s", task_type, import_config_id)
        return None

    job_uuid = str(uuid.uuid4())
    config.is_running = True
    model.Session.add(config)

    import_log = CUDCImportJob(
        import_config_id=import_config_id,
        run_at=datetime.utcnow(),
        run_by=run_by,
        id=job_uuid,
        is_running=True,
        other_data={"task_type": task_type},
    )
    model.Session.add(import_log)
    model.Session.commit()
    return job_uuid


def scheduled_run_import(import_config_id: str, run_by: str) -> None:
    """Run the full scheduled import for a saved import configuration."""
    config = CUDCImportConfig.get(import_config_id)
    if not config:
        log.warning("Cron import skipped: config not found %s", import_config_id)
        return
    if not config.code:
        log.warning("Cron import skipped: empty code for %s", import_config_id)
        return

    job_uuid = _start_scheduled_job(import_config_id, run_by, "import")
    if not job_uuid:
        return

    job_run_import(import_config_id, run_by, job_uuid)


def sync_cron_jobs() -> None:
    """Rebuild rq-scheduler entries from the current import configuration records."""
    queue = jobs.get_queue()
    scheduler = Scheduler(queue=queue, connection=queue.connection)
    global_refresh_cron = get_global_source_last_updated_cron()

    # Rebuild the scheduler state from DB config so edits take effect immediately.
    for job in scheduler.get_jobs():
        if job.id and job.id.startswith(SCHEDULE_PREFIX):
            scheduler.cancel(job)

    configs = CUDCImportConfig.get_all_configs()
    import_job_count = 0
    for config in configs:
        other_config = config.other_config or {}
        is_auto_arcgis = (config.platform or "").lower() == "arcgis" and bool(
            other_config.get(ARCGIS_AUTO_IMPORT_FLAG)
        )

        if is_auto_arcgis:
            cron = (
                (other_config.get(SOURCE_LAST_UPDATED_CRON_KEY) or "").strip()
                or global_refresh_cron
                or ""
            )
        else:
            cron = (config.cron_schedule or "").strip()

        if cron:
            job_id = f"{SCHEDULE_PREFIX}{config.id}"
            scheduler.cron(
                cron,
                func=scheduled_run_import,
                args=[config.id, config.created_by],
                id=job_id,
                queue_name=queue.name,
                use_local_timezone=True,
            )
            import_job_count += 1

    log.info("Cron jobs synced: imports=%s", import_job_count)
