"""Authorization functions for user management actions."""
from ckan.types import Context, AuthResult


def deleted_users_list(context: Context, data_dict: dict) -> AuthResult:
    """Only sysadmins can list deleted users."""
    return {'success': False}


def purge_deleted_users(context: Context, data_dict: dict) -> AuthResult:
    """Only sysadmins can purge deleted users."""
    return {'success': False}
