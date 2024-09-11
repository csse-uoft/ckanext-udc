import json
from ckan import logic
from ckan.plugins.toolkit import config
from ckan.lib.api_token import encode
from ckan.common import current_user
from datetime import timedelta, timezone, datetime
from ckan.authz import is_sysadmin


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
