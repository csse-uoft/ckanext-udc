"""Config parsing helpers with safe fallbacks."""
from __future__ import annotations

from typing import Optional

import ckan.plugins.toolkit as tk
from ckan.common import asbool


def get_bool(name: str, default: bool) -> bool:
    raw = tk.config.get(name, None)
    if raw is None:
        return default
    if isinstance(raw, str) and not raw.strip():
        return default
    try:
        return asbool(raw)
    except ValueError:
        return default


def get_int(name: str, default: int, min_value: Optional[int] = None) -> int:
    raw = tk.config.get(name, None)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        value = default
    else:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = default

    if min_value is not None and value < min_value:
        return min_value
    return value

