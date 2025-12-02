import ckan.plugins.toolkit as tk
from ckan.types import Context
import ckan.logic as logic
from ckan.plugins import get_plugin
from ckan.common import _


import json

default_config = {
    "openai_key": "",
    "openai_model": "gpt-4",
    "max_tokens": 500,
    "temperature": 0.0,
}

def init_plugin():
    config = tk.config.get("ckanext.udc.desc.config")
    if not config:
        tk.config["ckanext.udc.desc.config"] = json.dumps(default_config)
        
        
def get_package(context: Context, package_id: str):
    data_dict = {"id": package_id}
    logic.check_access("package_show", context, data_dict=data_dict)
    package_dict = logic.get_action("package_show")(context, data_dict)
    return package_dict

def get_config():
    config = tk.config.get("ckanext.udc.desc.config")
    if not config:
        raise logic.ActionError(_("ckanext.udc.desc config is not set"))
    config = json.loads(config)
    
    return {**default_config, **config, "maturity_model": get_plugin('udc').maturity_model}

# Function to generate mapping names for all maturity levels
def gen_mapping(maturity_model):
    """
    This function maps the internal and external display names for all fields using the udc config.
    :param mapping_json: udc config json string
    :return: List of mappings between the internal and external display names
    """
    mm_mapping = {}
    for mm in maturity_model:
        for f in mm['fields']:
            external_name = f.get('ckanField') or f.get('label')
            internal_name = f.get('ckanField') or f.get('name')
            short_desc = f.get('short_description')
            mm_mapping[external_name] = ({'maturity_level': mm['name'], 'internal_name': internal_name, 'display_name': external_name, 'short_description': short_desc})
    return mm_mapping
