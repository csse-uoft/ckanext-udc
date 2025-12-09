from copy import deepcopy

# Field name mapping: normalized name -> actual data_dict field name
ckanFieldMapping = {
    "title": "title_translated",
    "description": "description_translated",
    "tags": "tags_translated",

    "source": "url"
}
ckanFieldKeys = [
    "name", "title", "notes", "tags", "id", "pkg_name", "author", "author_email",
    "url", "version"
]


def prepare_data_dict(data_dict: dict) -> dict:
    """
    Prepare data_dict for template compilation by applying field name mappings.
    This replaces the need for CKANField wrapper.
    
    Returns a new dict with normalized field names that can be used directly
    in the mapping templates.
    """
    result = deepcopy(data_dict)
    
    # Apply field mappings
    for normalized_name, actual_field in ckanFieldMapping.items():
        if actual_field in data_dict and data_dict[actual_field] is not None:
            result[normalized_name] = data_dict[actual_field]
    
    # Special handling for 'id': prefer 'pkg_name' on update, 'id' on create
    if 'pkg_name' in data_dict and data_dict['pkg_name']:
        result['id'] = data_dict['pkg_name']
    elif 'id' in data_dict:
        result['id'] = data_dict['id']
    
    return result
