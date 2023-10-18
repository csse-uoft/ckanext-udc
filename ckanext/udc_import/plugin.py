import ckan
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.types import Action, AuthFunction, Schema
import ckanext.udc_import.logic.actions as action
import ckanext.udc_import.views as views
import ckanext.udc_import.auth as auth
from ckan.common import CKANConfig
import ckan.plugins.toolkit as tk
from typing import Dict


class UdcImportPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAuthFunctions)

    def configure(self, config: CKANConfig):
        side_panel_text = ckan.model.system_info.get_system_info(
            "ckanext.udc_import.side_panel_text")

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "udc_import")

    # IActions
    def get_actions(self) -> Dict[str, Action]:
        return {
            'udc_import_submit': action.udc_import_submit,
            'udc_import_check_permission': action.check_permission,
        }
    

    # IBlueprint
    def get_blueprint(self):
        return views.get_blueprints()
    
    # IAuthFunctions
    def get_auth_functions(self) -> Dict[str, AuthFunction]:
        return {
            u'udc_import_view': auth.udc_import_auth,
            u'udc_import_submit': auth.udc_import_auth,
        }

    # IConfigurable
    def update_config_schema(self, schema: Schema):

        ignore_missing = tk.get_validator('ignore_missing')
        unicode_safe = tk.get_validator('unicode_safe')

        schema.update({
            # This is a custom configuration option
            'ckanext.udc_import.side_panel_text': [
                ignore_missing, unicode_safe
            ],
        })

        return schema