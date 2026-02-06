"""Authorization functions for organization management actions."""
from ckan.types import Context, AuthResult
from ckan import model


def _is_sysadmin(context: Context) -> bool:
    user = context.get("user")
    if not user:
        return False
    user_obj = model.User.get(user)
    return bool(user_obj and user_obj.sysadmin)


def udc_organization_list(context: Context, data_dict: dict) -> AuthResult:
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can list organizations."}


def udc_organization_packages_list(context: Context, data_dict: dict) -> AuthResult:
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can list organization packages."}


def udc_organization_packages_ids(context: Context, data_dict: dict) -> AuthResult:
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can list organization package ids."}


def udc_organization_packages_delete(context: Context, data_dict: dict) -> AuthResult:
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can delete organization packages."}

