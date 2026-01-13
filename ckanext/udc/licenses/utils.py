from __future__ import annotations
from ckan.common import _
from ckan.model.license import License as CKANLicense, DefaultLicense
from ckan import model
from ckan.lib.redis import connect_to_redis, is_redis_available
from typing import Any, Callable, Collection, KeysView, Optional, Union, cast

from ckanext.udc.licenses.model import CustomLicense

_CUSTOM_LICENSE_SET_KEY = "udc:licenses:custom_ids"
_LICENSE_VERSION_KEY = "udc:licenses:version"
_local_license_version = None

def create_custom_license(_id, _url, _title):
    class AnonymousCustomLicense(DefaultLicense):
        id = _id
        url = _url

        @property
        def title(self):
            return _(_title)
    return CKANLicense(AnonymousCustomLicense())


def _get_redis_conn():
    if not is_redis_available():
        return None
    try:
        return connect_to_redis()
    except Exception:
        return None


def _get_custom_license_ids():
    return [c.id for c in model.Session.query(CustomLicense)]


def refresh_custom_licenses():
    """
    Sync custom licenses from DB into the in-process license register.
    Uses Redis to track which licenses were added by this extension so we can
    safely remove deleted ones across processes.
    """
    license_register = model.Package.get_license_register()
    custom_ids = set(_get_custom_license_ids())

    redis_conn = _get_redis_conn()
    previous_custom_ids = set()
    if redis_conn:
        previous_custom_ids = set(redis_conn.smembers(_CUSTOM_LICENSE_SET_KEY))

    # Remove deleted custom licenses
    if previous_custom_ids:
        license_register.licenses = [
            l for l in license_register.licenses if l.id not in (previous_custom_ids - custom_ids)
        ]

    # Insert/update current custom licenses
    existing_by_id = {l.id: l for l in license_register.licenses}
    for custom in model.Session.query(CustomLicense):
        new_license = create_custom_license(custom.id, custom.url, custom.title)
        if custom.id in existing_by_id:
            for idx, existing in enumerate(license_register.licenses):
                if existing.id == custom.id:
                    license_register.licenses[idx] = new_license
                    break
        else:
            license_register.licenses.append(new_license)

    if redis_conn:
        pipe = redis_conn.pipeline()
        pipe.delete(_CUSTOM_LICENSE_SET_KEY)
        if custom_ids:
            pipe.sadd(_CUSTOM_LICENSE_SET_KEY, *custom_ids)
        pipe.execute()


def bump_license_version():
    redis_conn = _get_redis_conn()
    if redis_conn:
        redis_conn.incr(_LICENSE_VERSION_KEY)


def refresh_license_register_if_needed():
    global _local_license_version
    redis_conn = _get_redis_conn()
    if not redis_conn:
        return
    version = redis_conn.get(_LICENSE_VERSION_KEY)
    if version != _local_license_version:
        refresh_custom_licenses()
        _local_license_version = version


def license_options_details(
    existing_license_id: Optional[tuple[str, str]] = None
) -> list[tuple[str, str, str]]:
    '''Returns [(l.id, l.title, l.url), ...] for the licenses configured to be
    offered. Always includes the existing_license_id, if supplied.
    '''
    refresh_license_register_if_needed()
    result = []
    register = model.Package.get_license_register()
    sorted_licenses = sorted(register.values(), key=lambda x: x.title)
    license_ids = [license.id for license in sorted_licenses]
    if existing_license_id and existing_license_id not in license_ids:
        license_ids.insert(0, existing_license_id)
    
    for license_id in license_ids:
        license = register[license_id]
        if license:
            result.append((license.id, _(license.title), license.url or ''))
        else:
            result.append((license_id, license_id, ''))
    return result
