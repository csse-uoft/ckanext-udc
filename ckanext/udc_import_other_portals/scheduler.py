import logging
import uuid
from datetime import datetime

import ckan.lib.jobs as jobs
import ckan.model as model
from rq_scheduler import Scheduler

from ckanext.udc_import_other_portals.jobs import job_run_import
from ckanext.udc_import_other_portals.model import CUDCImportConfig, CUDCImportJob

log = logging.getLogger(__name__)

SCHEDULE_PREFIX = "udc-import:"


def scheduled_run_import(import_config_id: str, run_by: str) -> None:
    config = CUDCImportConfig.get(import_config_id)
    if not config:
        log.warning("Cron import skipped: config not found %s", import_config_id)
        return
    if not config.code:
        log.warning("Cron import skipped: empty code for %s", import_config_id)
        return
    if config.is_running:
        log.info("Cron import skipped: already running %s", import_config_id)
        return

    job_uuid = str(uuid.uuid4())
    config.is_running = True
    model.Session.add(config)

    import_log = CUDCImportJob(
        import_config_id=import_config_id,
        run_at=datetime.utcnow(),
        run_by=run_by,
        id=job_uuid,
        is_running=True,
    )
    model.Session.add(import_log)
    model.Session.commit()

    job_run_import(import_config_id, run_by, job_uuid)


def sync_cron_jobs() -> None:
    queue = jobs.get_queue()
    scheduler = Scheduler(queue=queue, connection=queue.connection)

    for job in scheduler.get_jobs():
        if job.id and job.id.startswith(SCHEDULE_PREFIX):
            scheduler.cancel(job)

    configs = CUDCImportConfig.get_all_configs()
    for config in configs:
        cron = (config.cron_schedule or "").strip()
        if not cron:
            continue
        job_id = f"{SCHEDULE_PREFIX}{config.id}"
        scheduler.cron(
            cron,
            func=scheduled_run_import,
            args=[config.id, config.created_by],
            id=job_id,
            queue_name=queue.name,
            use_local_timezone=True,
        )

    log.info("Cron jobs synced: %s", len([c for c in configs if c.cron_schedule]))
