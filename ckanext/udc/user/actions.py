"""User management actions for UDC."""
from __future__ import annotations
from typing import Any
from sqlalchemy import or_
import ckan.plugins.toolkit as tk
from ckan.types import Context
from ckan import model
from ckan.logic import NotFound


@tk.side_effect_free
def deleted_users_list(context: Context, data_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Get a list of deleted users.
    
    Only sysadmins can access this endpoint.
    
    :returns: List of deleted user dictionaries
    :rtype: list of dictionaries
    """
    tk.check_access('deleted_users_list', context, data_dict)

    page = int(data_dict.get("page", 1) or 1)
    page_size = int(data_dict.get("page_size", 25) or 25)
    filters = data_dict.get("filters") or {}

    query = _apply_user_filters(
        model.Session.query(model.User).filter(model.User.state == "deleted"),
        filters,
    )
    total = query.count()
    deleted_users = (
        query.order_by(model.User.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "results": [_user_to_dict(user) for user in deleted_users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def purge_deleted_users(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Purge all deleted users from the database.
    
    .. warning:: This action cannot be undone! Users will be permanently removed.
    
    Only sysadmins can purge deleted users.
    
    :returns: Dictionary with count of purged users
    :rtype: dictionary
    """
    tk.check_access('purge_deleted_users', context, data_dict)

    selected_ids = data_dict.get("ids") or []
    query = model.Session.query(model.User).filter(model.User.state == "deleted")
    if selected_ids:
        query = query.filter(model.User.id.in_(selected_ids))
    deleted_users = query.all()
    
    count = 0
    for user_to_purge in deleted_users:
        # Remove user memberships
        user_memberships = model.Session.query(model.Member).filter(
            model.Member.table_id == user_to_purge.id
        ).all()
        for membership in user_memberships:
            membership.purge()
        
        # Remove package collaborations
        collaborations = model.Session.query(model.PackageMember).filter(
            model.PackageMember.user_id == user_to_purge.id
        ).all()
        for collab in collaborations:
            collab.purge()
        
        # Purge the user
        user_to_purge.purge()
        count += 1
    
    model.Session.commit()
    
    return {
        'success': True,
        'count': count,
        'message': f'{count} deleted user(s) have been purged'
    }


@tk.side_effect_free
def udc_user_list(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """List active users with pagination and column filters."""
    tk.check_access("udc_user_list", context, data_dict)

    page = int(data_dict.get("page", 1) or 1)
    page_size = int(data_dict.get("page_size", 25) or 25)
    filters = data_dict.get("filters") or {}

    query = _apply_user_filters(
        model.Session.query(model.User).filter(model.User.state != "deleted"),
        filters,
    )
    total = query.count()
    users = (
        query.order_by(model.User.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "results": [_user_to_dict(user) for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def udc_user_reset_password(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Reset a user's password (sysadmin only)."""
    tk.check_access("udc_user_reset_password", context, data_dict)

    user_id = data_dict.get("id") or data_dict.get("name")
    new_password = data_dict.get("new_password")
    if not user_id or not new_password:
        raise tk.ValidationError({"new_password": ["Password is required."]})

    user_obj = model.User.get(user_id)
    if not user_obj:
        raise NotFound("User not found")

    user_obj.set_password(new_password)
    model.Session.commit()

    return {"success": True, "id": user_obj.id, "name": user_obj.name}


def udc_user_delete(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Soft-delete a user (sysadmin only)."""
    tk.check_access("udc_user_delete", context, data_dict)

    user_id = data_dict.get("id") or data_dict.get("name")
    if not user_id:
        raise tk.ValidationError({"id": ["User id or name is required."]})

    user_obj = model.User.get(user_id)
    if not user_obj:
        raise NotFound("User not found")

    user_obj.state = "deleted"
    model.Session.commit()

    return {"success": True, "id": user_obj.id, "name": user_obj.name}


def _user_to_dict(user: model.User) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "fullname": user.fullname,
        "email": user.email,
        "created": user.created.isoformat() if user.created else None,
        "state": user.state,
        "sysadmin": bool(user.sysadmin),
        "about": user.about,
    }


def _apply_user_filters(query, filters: dict[str, Any]):
    search = (filters.get("q") or "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                model.User.name.ilike(pattern),
                model.User.fullname.ilike(pattern),
                model.User.email.ilike(pattern),
                model.User.about.ilike(pattern),
            )
        )

    name = (filters.get("name") or "").strip()
    if name:
        query = query.filter(model.User.name.ilike(f"%{name}%"))

    fullname = (filters.get("fullname") or "").strip()
    if fullname:
        query = query.filter(model.User.fullname.ilike(f"%{fullname}%"))

    email = (filters.get("email") or "").strip()
    if email:
        query = query.filter(model.User.email.ilike(f"%{email}%"))

    about = (filters.get("about") or "").strip()
    if about:
        query = query.filter(model.User.about.ilike(f"%{about}%"))

    sysadmin = filters.get("sysadmin")
    if sysadmin in (True, False):
        query = query.filter(model.User.sysadmin == sysadmin)

    return query
