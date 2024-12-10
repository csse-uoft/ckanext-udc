import json

from ckanext.udc_react.constants import UDC_REACT_PATH
from ckan import logic
from ckan.plugins.toolkit import mail_user
from ckan.plugins.toolkit import config
from ckan.lib.api_token import encode, decode
from ckan.common import current_user
from datetime import timedelta, timezone, datetime
from ckan.authz import is_sysadmin
from ckan import model
from ckanext.udc_react.model.organization_access_request import OrganizationAccessRequest


@logic.side_effect_free
def get_organizations_and_admins(context, data_dict):
    """
    Get all organizations and their admins.
    """
    # Admin only
    user = context.get("user")
    if current_user.is_anonymous:
        raise logic.NotAuthorized("Not authorized.")

    all_organizations = model.Session.query(model.Group).filter(
        model.Group.type == "organization"
    )

    organizations = []
    for org in all_organizations:

        admin_members = (
            model.Session.query(model.Member)
            .filter_by(group_id=org.id)
            .filter_by(capacity="admin")
            .all()
        )

        admins = []
        for member in admin_members:
            user = model.User.get(member.table_id)
            admins.append(
                {"id": member.table_id, "name": user.name, "fullname": user.fullname}
            )

        organizations.append({"id": org.name, "name": org.title, "admins": admins})

    return organizations


def request_organization_access(context, data_dict):
    """
    Request access to an organization. Send email to the organization's admins.
    """
    if current_user.is_anonymous:
        raise logic.NotAuthorized("Not authorized.")

    user = model.User.get(context.get("user"))

    notes = data_dict.get("notes", '')
    organization_id = data_dict.get("organization_id")
    organization = model.Group.get(organization_id)

    if not organization:
        raise logic.ValidationError("Organization not found.")

    # Check if the user is already a member
    member = (
        model.Session.query(model.Member)
        .filter_by(table_id=user.id, group_id=organization.id)
        .first()
    )

    if member:
        raise logic.ValidationError("You are already a member of this organization.")

    admins = data_dict.get("admin_ids")
    if not admins:
        raise logic.ValidationError("No admins specified.")
    
    # Create the request
    request = OrganizationAccessRequest(user.id, organization.id, notes)
    model.Session.add(request)
    model.Session.commit()

    # Send email to the admins
    for admin in admins:
        admin_user = model.User.get(admin)
        if not admin_user:
            raise logic.ValidationError(f"Admin {admin} not found.")

        # Check if the admin if an admin of the organization
        member = (
            model.Session.query(model.Member)
            .filter_by(
                table_id=admin_user.id, group_id=organization.id, capacity="admin"
            )
            .first()
        )
        if not member:
            raise logic.ValidationError(
                f"User {admin_user.name} is not an admin of the organization."
            )

        # Check if the admin has an email
        if not admin_user.email:
            raise logic.ValidationError(f"Admin {admin_user.name} has no email.")
        
        request.admins.append(admin_user)

        # Create a jwt token for the admin to approve or deny the request
        # Encode the data, expires after 7 days
        encoded = encode(
            {
                "exp": request.expires_at,
                "request_id": request.id,
            }
        )

        # Send email
        requester_message = f"\nA message is left by the user:\n{notes}\n\n" if notes else ""
        requester_message_html = f"\n<p>A message is left by the user:</p>\n<p>{notes}</p>\n\n" if notes else ""
        subject = f"Request for access to organization {organization.title}"
        body = f"""Hi the admin of organization {organization.title},

User {user.name} requested to join your organization.{requester_message}
Please approve or deny the request at {config.get('ckan.site_url')}/{UDC_REACT_PATH}/request-organization-access/token/{encoded}.

Thanks,
CUDC Team
"""
        body_html = f"""<p>Hi the admin of organization {organization.title},</p>
<p>User {user.name} requested to join your organization.</p>{requester_message_html}
<p>Please approve or deny the request at <a href="{config.get('ckan.site_url')}/{UDC_REACT_PATH}/request-organization-access/token/{encoded}">here</a>.</p>
<p>Thanks,<br>CUDC Team</p>
"""

        mail_user(admin_user, subject, body, body_html)
    
    model.Session.commit()
    return {"success": True}


def decode_request_organization_access_token(context, data_dict):
    """
    Decode the request organization access token for admin to approve or deny.
    """
    if current_user.is_anonymous:
        raise logic.NotAuthorized("Not authorized.")

    user = model.User.get(context.get("user"))

    token = data_dict.get("token")
    if not token:
        raise logic.ValidationError("No token specified.")

    # Decode the token
    decoded = decode(token)

    if decoded is None:
        raise logic.ValidationError("Invalid token.")

    request_id = decoded.get("request_id")
    
    request = model.Session.query(OrganizationAccessRequest).get(request_id)
    if not request:
        raise logic.ValidationError("Request not found.")
    
    admin_ids = [admin.id for admin in request.admins]

    # Check if the user is the admin
    if user.id not in admin_ids:
        raise logic.ValidationError(
            "Invalid user, please check if you are logged in as the correct user."
        )

    requester = model.User.get(request.user_id)

    if not requester:
        raise logic.ValidationError("Requester not found.")

    organization = model.Group.get(request.organization_id)
    if not organization:
        raise logic.ValidationError("Organization not found.")

    admin_user = model.User.get(current_user.id)
    if not admin_user:
        raise logic.ValidationError("Admin not found.")
    
    # Check if the current user is still an admin of the organization
    member = (
        model.Session.query(model.Member)
        .filter_by(
            table_id=admin_user.id, group_id=organization.id, capacity="admin"
        )
        .first()
    )
    if not member:
        raise logic.ValidationError(
            f"Sorry, you are no longer an admin of the organization {organization.title}."
        )

    return {
        "requester": {
            "id": requester.id,
            "name": requester.name,
            "fullname": requester.fullname,
            "email": requester.email,
            "picture": requester.image_url,
            "notes": request.notes,
        },
        "organization": {
            "id": organization.id,
            "name": organization.title,
        },
        "status": request.get_status(),
    }


def approve_or_deny_organization_access(context, data_dict):
    """
    Approve or deny a request for organization access.
    """
    if current_user.is_anonymous:
        raise logic.NotAuthorized("Not authorized.")

    user = model.User.get(context.get("user"))

    token = data_dict.get("token")
    if not token:
        raise logic.ValidationError("No token specified.")

    # Decode the token
    decoded = decode(token)

    if decoded is None:
        raise logic.ValidationError("Invalid token.")
    
    request_id = decoded.get("request_id")
    
    request = model.Session.query(OrganizationAccessRequest).get(request_id)
    if not request:
        raise logic.ValidationError("Request not found.")
    
    admin_ids = [admin.id for admin in request.admins]

    # Check if the user is the admin
    if user.id not in admin_ids:
        raise logic.ValidationError(
            "Invalid user, please check if you are logged in as the correct user."
        )

    requester = model.User.get(request.user_id)
    if not requester:
        raise logic.ValidationError("Requester not found.")

    organization = model.Group.get(request.organization_id)
    if not organization:
        raise logic.ValidationError("Organization not found.")

    # Check if the requester is stil not a member
    member = (
        model.Session.query(model.Member)
        .filter_by(table_id=requester.id, group_id=organization.id)
        .first()
    )

    if member:
        raise logic.ValidationError(
            "Requester is already a member of this organization."
        )
        
    if request.is_expired():
        raise logic.ValidationError("Request has expired.")
    
    if request.get_status() != "pending":
        raise logic.ValidationError(f"Request has already been {request.get_status()}.")

    approve = data_dict.get("approve")
    if approve:
        # Add the requester as a member
        member = model.Member(
            table_name="user",
            table_id=requester.id,
            group_id=organization.id,
            capacity="editor",
        )
        model.Session.add(member)
        
        # Update the request status
        request.accept()
        model.Session.add(request)
        
        model.Session.commit()

        # Send email to the requester
        subject = f"Approved request for access to organization {organization.title}"
        body = f"""Hi {requester.name},

Your request to join organization {organization.title} has been approved.

Thanks,
CUDC Team"""
        body_html = f"""<p>Hi {requester.name},</p>
<p>Your request to join organization {organization.title} has been approved.</p>
<p>Thanks,<br>CUDC Team</p>
"""
        mail_user(requester, subject, body, body_html)

    else:
        # Update the request status
        request.reject()
        model.Session.add(request)
        model.Session.commit()
        
        # Send email to the requester
        subject = f"Request for access to organization {organization.title}"
        body = f"""Hi {requester.name},

Your request to join organization {organization.title} has been denied.

Regards,
CUDC Team"""
        body_html = f"""<p>Hi {requester.name},</p>
        <p>Your request to join organization {organization.title} has been denied.</p>
        <p>Thanks,<br>CUDC Team</p>
        """

        mail_user(requester, subject, body, body_html)
    
    return {"success": True}
