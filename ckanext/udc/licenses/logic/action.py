from ckan import model, authz, logic
from ckan.model.license import DefaultLicense, License as CKANLicense
from ckan.common import _
import logging

from ckanext.udc.licenses.model import CustomLicense, init_tables
from ckanext.udc.licenses.utils import create_custom_license
from psycopg2.errors import UndefinedTable

log = logging.getLogger(__name__)


def license_create(context, data_dict):
    """
    Any user can create a custom license.
    """
    
    user = context.get("user")
    id = data_dict.get('id')
    title = data_dict.get('title')
    url = data_dict.get('url')
    
    if not user:
        raise logic.ValidationError("You are not logged in")

    # Validate that we have the required fields.
    if not id:
        raise logic.ValidationError("licencse id is required")
    
    if not title:
        raise logic.ValidationError("licencse title is required")
    
    if not url:
        raise logic.ValidationError("licencse url is required")
    
    license_register = model.Package.get_license_register()
    registered_ids = set([license.id for license in license_register.licenses])
    
    if data_dict['id'] in registered_ids:
        raise logic.ValidationError("licencse id existed")

    # Create the object
    userobj = model.User.get(user)
    model.Session.add(CustomLicense(id=id, title=title, url=url, user_id=userobj.id))

    # Add to registered license
    # Create License Class dynamically
    license_register.licenses.append(create_custom_license(id, url, title))
    
    model.Session.commit()
    return {"success": True}


def license_delete(context, data_dict):
    """
    The user who created the license, or the admin can delete the license.
    The license can only be deleted when it is not used by other packages.
    """
    if not data_dict.get('id'):
        raise logic.ValidationError("license id is required")
    
    user = context.get("user")
    if not user:
        raise logic.NotAuthorized("You are not logged in")
    
    userobj = model.User.get(user)
    license = CustomLicense.get(data_dict["id"]).one()
    
    if not authz.is_sysadmin(user) and not license.user_id == userobj.id:
        raise logic.NotAuthorized("You are not authorized to delete this license")
    
    # Check if any package uses the license
    cnt = model.Session.query(model.Package) \
            .filter(model.Package.licensce_id == data_dict['id']) \
            .count()
        
    if cnt > 0:
        raise logic.ValidationError("The license is in use and cannot be deleted")
    
    model.Session.delete(license)
    model.Session.commit()
    
    return {'success': True}


@logic.side_effect_free
def licenses_get(context, data_dict):
    """
    Get all custom licenses and predefined CKAN licenses.
    """
    licenses = []
    
    custom_licenses = model.Session.query(CustomLicense)
    for custom_license in custom_licenses:
        custom_license = custom_license.as_dict()
        userObj = model.User.get(custom_license.get('user_id'))
        user = {'id': custom_license.get('user_id'), 'name': userObj.name, 'fullname': userObj.fullname}
        
        licenses.append({
            **custom_license,
            "user": user
        })
    
    return licenses


@logic.side_effect_free
def test_long_task(context, data_dict):
    """
    A test action to simulate a long running task.
    """
    import time
    time.sleep(10)
    return {"success": True}
    
    

def init_licenses():
    """
    This is not an action call, this initialize all custom licenses from the custom_license table into CKAN.
    """
    license_register = model.Package.get_license_register()
    registered_ids = set([license.id for license in license_register.licenses])
    
    if model.meta.engine.dialect.has_table(model.meta.engine.connect(), 'custom_license'):
        custom_licenses = model.Session.query(CustomLicense)
        for custom_license in custom_licenses:
            if custom_license.id not in registered_ids:
                # Add to registered license
                # Create License Class dynamically
                license_register.licenses.append(create_custom_license(custom_license.id, custom_license.url, custom_license.title))
        log.info("Loaded custom licenses")