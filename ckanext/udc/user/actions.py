"""User management actions for UDC."""
from __future__ import annotations
from typing import Any
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
    tk.check_access('user_list', context, data_dict)
    
    # Only sysadmins can list deleted users
    user = context.get('user')
    if not user:
        raise tk.NotAuthorized('You must be logged in to access deleted users')
    
    user_obj = model.User.get(user)
    if not user_obj or not user_obj.sysadmin:
        raise tk.NotAuthorized('Only sysadmins can list deleted users')
    
    # Query for deleted users
    deleted_users = model.Session.query(model.User).filter(
        model.User.state == 'deleted'
    ).all()
    
    # Convert to dictionaries
    users_list = []
    for user in deleted_users:
        users_list.append({
            'id': user.id,
            'name': user.name,
            'fullname': user.fullname,
            'email': user.email,
            'created': user.created.isoformat() if user.created else None,
            'state': user.state,
        })
    
    return users_list


def purge_deleted_users(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Purge all deleted users from the database.
    
    .. warning:: This action cannot be undone! Users will be permanently removed.
    
    Only sysadmins can purge deleted users.
    
    :returns: Dictionary with count of purged users
    :rtype: dictionary
    """
    # Check authorization
    user = context.get('user')
    if not user:
        raise tk.NotAuthorized('You must be logged in to purge deleted users')
    
    user_obj = model.User.get(user)
    if not user_obj or not user_obj.sysadmin:
        raise tk.NotAuthorized('Only sysadmins can purge deleted users')
    
    # Get all deleted users
    deleted_users = model.Session.query(model.User).filter(
        model.User.state == 'deleted'
    ).all()
    
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
