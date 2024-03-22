from __future__ import annotations
from ckan.common import _
from ckan.model.license import License as CKANLicense, DefaultLicense
from ckan import model
from typing import Any, Callable, Collection, KeysView, Optional, Union, cast

def create_custom_license(_id, _url, _title):
    class AnonymousCustomLicense(DefaultLicense):
        id = _id
        url = _url

        @property
        def title(self):
            return _(_title)
    return CKANLicense(AnonymousCustomLicense())


def license_options_details(
    existing_license_id: Optional[tuple[str, str]] = None
) -> list[tuple[str, str, str]]:
    '''Returns [(l.id, l.title, l.url), ...] for the licenses configured to be
    offered. Always includes the existing_license_id, if supplied.
    '''
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