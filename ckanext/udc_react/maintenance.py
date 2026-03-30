from __future__ import annotations

from typing import Optional

MAINTENANCE_MODE_CONFIG_KEY = "ckanext.udc.maintenance_mode"

_EXACT_EXEMPT_PATHS = frozenset(
    {
        "/favicon.ico",
        "/robots.txt",
        "/user/login",
        "/user/logout",
    }
)

_PREFIX_EXEMPT_PATHS = (
    "/udrc",
    "/api/",
    "/base/",
    "/fanstatic/",
    "/webassets/",
    "/socket.io",
    "/admin-dashboard",
    "/_debug_toolbar",
)


def is_maintenance_mode_enabled(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False

    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def is_maintenance_exempt_path(path: Optional[str]) -> bool:
    normalized_path = path or "/"
    if normalized_path in _EXACT_EXEMPT_PATHS:
        return True

    for prefix in _PREFIX_EXEMPT_PATHS:
        if normalized_path == prefix or normalized_path.startswith(prefix):
            return True

    return False


def should_render_maintenance(
    path: Optional[str],
    enabled: bool,
    method: str = "GET",
    accept_header: Optional[str] = None,
    user_is_admin: bool = False,
) -> bool:
    if not enabled:
        return False

    if user_is_admin:
        return False

    if (method or "GET").upper() not in {"GET", "HEAD"}:
        return False

    if is_maintenance_exempt_path(path):
        return False

    accept_value = (accept_header or "").lower()
    if not accept_value:
        return True

    return "text/html" in accept_value or "application/xhtml+xml" in accept_value