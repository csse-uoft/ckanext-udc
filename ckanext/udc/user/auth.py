"""Authorization functions for user management actions."""
from ckan.types import Context, AuthResult
from ckan import model


def _is_sysadmin(context: Context) -> bool:
    user = context.get("user")
    if not user:
        return False
    user_obj = model.User.get(user)
    return bool(user_obj and user_obj.sysadmin)


def deleted_users_list(context: Context, data_dict: dict) -> AuthResult:
    """Only sysadmins can list deleted users."""
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can list deleted users."}


def purge_deleted_users(context: Context, data_dict: dict) -> AuthResult:
    """Only sysadmins can purge deleted users."""
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can purge deleted users."}


def udc_user_list(context: Context, data_dict: dict) -> AuthResult:
    """Only sysadmins can list users."""
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can list users."}


def udc_user_reset_password(context: Context, data_dict: dict) -> AuthResult:
    """Only sysadmins can reset passwords."""
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can reset passwords."}


def udc_user_delete(context: Context, data_dict: dict) -> AuthResult:
    """Only sysadmins can delete users."""
    if _is_sysadmin(context):
        return {"success": True}
    return {"success": False, "msg": "Only sysadmins can delete users."}
