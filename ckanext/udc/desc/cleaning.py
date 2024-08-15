# Data cleaning functions
def extract_name(resources):
    if isinstance(resources, list) and len(resources) > 0 and 'name' in resources[0]:
        return resources[0]['name']
    return None

def extract_name_dict(dictionary):
    return dictionary.get('name')

def extract_display_name(tags):
    if isinstance(tags, list):
        display_names = [item.get('display_name') for item in tags]
        return ', '.join(display_names)
    return None

def convert_non_str_nan(value, nan_value="Not provided", if_found_value=None):
    value = str(value) if value == value and value is not None else ""
    return if_found_value or value if len(value) > 0 else nan_value
