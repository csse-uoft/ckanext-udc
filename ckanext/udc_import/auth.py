from __future__ import annotations

from typing import Any, Dict
from ckan.types import AuthResult, Context
import ckan.plugins as p


def udc_import_auth(
        context: Context, data_dict: Dict[str, Any]) -> AuthResult:
    user = context.get('user')
    authorized = p.toolkit.check_access("package_create", context, data_dict)

    if not authorized:
        return {
            'success': False,
            'msg': p.toolkit._(
                'User {0} not authorized to create package'
                    .format(str(user))
            )
        }
    else:
        return {'success': True}
