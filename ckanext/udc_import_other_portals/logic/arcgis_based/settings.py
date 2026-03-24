import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ckan.model.system_info import get_system_info, set_system_info

ARCGIS_AUTO_IMPORT_SETTINGS_KEY = "ckanext.udc_import_other_portals.arcgis_auto_import_settings"
SOURCE_LAST_UPDATED_GLOBAL_CRON_KEY = "source_last_updated_cron_schedule"


def _normalize_cron(value: Any) -> Optional[str]:
    """Normalize cron-like settings so blank or invalid values become None."""
    if not isinstance(value, str):
        return None
    return value.strip() or None


def load_arcgis_auto_import_settings() -> Dict[str, Any]:
    """Load persisted ArcGIS auto-import settings from system_info."""
    cached = get_system_info(ARCGIS_AUTO_IMPORT_SETTINGS_KEY)
    if not cached:
        return {
            SOURCE_LAST_UPDATED_GLOBAL_CRON_KEY: None,
            "updated_at": None,
        }

    try:
        payload = json.loads(cached)
    except ValueError:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    return {
        SOURCE_LAST_UPDATED_GLOBAL_CRON_KEY: _normalize_cron(
            payload.get(SOURCE_LAST_UPDATED_GLOBAL_CRON_KEY)
        ),
        "updated_at": payload.get("updated_at"),
    }


def get_global_source_last_updated_cron() -> Optional[str]:
    """Return the global fallback schedule for lightweight ArcGIS refresh jobs."""
    return load_arcgis_auto_import_settings().get(SOURCE_LAST_UPDATED_GLOBAL_CRON_KEY)


def save_arcgis_auto_import_settings(source_last_updated_cron_schedule: Optional[str]) -> Dict[str, Any]:
    """Persist ArcGIS auto-import settings and return the normalized payload."""
    normalized_cron = _normalize_cron(source_last_updated_cron_schedule)
    payload = {
        SOURCE_LAST_UPDATED_GLOBAL_CRON_KEY: normalized_cron,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    set_system_info(ARCGIS_AUTO_IMPORT_SETTINGS_KEY, json.dumps(payload, ensure_ascii=True))
    return payload