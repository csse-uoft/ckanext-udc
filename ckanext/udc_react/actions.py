import json
from ckan import logic
from ckan.plugins.toolkit import config

@logic.side_effect_free
def get_maturity_levels(context, data_dict):
    maturity_levels = config.get('ckanext.udc_react.qa_maturity_levels', '{}')
    return json.loads(maturity_levels)
