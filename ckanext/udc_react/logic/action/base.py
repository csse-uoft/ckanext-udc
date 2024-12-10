import json

from ckanext.udc.error_handler import clear_and_flash, MESSAGE_NOT_LOGGED_IN_REQUEST_ORGANIZATION_ACCESS
from ckanext.udc_react.constants import UDC_REACT_PATH
from ckan import logic
from ckan.plugins.toolkit import config, h
from ckan.lib.api_token import encode, decode
from ckan.common import current_user
from datetime import timedelta, timezone, datetime
from ckan.authz import is_sysadmin
from flask import session
import ckan.model as model


@logic.side_effect_free
def get_maturity_levels(context, data_dict):
    maturity_levels = config.get("ckanext.udc_react.qa_maturity_levels", "{}")
    return json.loads(maturity_levels)


@logic.side_effect_free
def get_ws_token(context, data_dict):
    # Get a one-time key to make the frontend connect to the socket.io server.
    # This is a walkaround as flask beaker session in CKAN does not work with sockerIO.

    user = context.get("user")

    if not is_sysadmin(user):
        raise logic.NotAuthorized("Not authorized.")

    # Encode the data, expires after 1 hour
    encoded = encode(
        {
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
            "user_id": current_user.id,
        }
    )
    return encoded

@logic.side_effect_free
def get_current_user(context, data_dict):
    if current_user.is_anonymous:
        return {"id": None, "name": None, "fullname": None}
    return {"id": current_user.id, "name": current_user.name, "fullname": current_user.fullname}


# def flash_message(context, data_dict):
#     message_type = data_dict.get("message_type")
    
#     messages = {
#         'MESSAGE_NOT_LOGGED_IN_REQUEST_ORGANIZATION_ACCESS': (
#             MESSAGE_NOT_LOGGED_IN_REQUEST_ORGANIZATION_ACCESS,
#             "alert-warning"
#         )
#     }
    
#     if message_type not in messages:
#         raise logic.ValidationError("Invalid message type.")
#     message = messages[message_type]
    
#     print(context)
#     # # Remove the error flash message
#     # if context.get('session') and "_flashes" in context.get('session'):
#     #     context.get('session')["_flashes"].clear()
#     # # Add a custom error message and type to the redirect
#     # h.flash(**message)
#     clear_and_flash(*message)
 
#     return {"success": True}
    