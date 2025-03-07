from __future__ import annotations

import json
import re

import ckan.plugins.toolkit as tk


# CKAN Config Validator
SUPPORTED_CKAN_FIELDS = [
    "title", "description", "tags", "license_id", "organization_and_visibility", "source", "version",
    "author", "author_email", "maintainer", "maintainer_email", "custom_fields",
]
REQUIRED_CKAN_FIELDS = [
    "title", "organization_and_visibility",
]
SUPPORTED_FIELD_TYPES = [
    "text", "date", "datetime", "time", "number", "single_select", "multiple_select",
]


def udc_config_validator(config_str):
    """
    Check whether the UDC config is valid.
    Raise a `tk.Invalid` Error when config is not valid, otherwire return the original config string.
    """
    try:
        config = json.loads(config_str)
    except:
        raise tk.Invalid("UDC Config: Malformed JSON Format.")
    
    if not isinstance(config["maturity_model"], list):
        raise tk.Invalid(f"UDC Config: Expecting a JSON List but got `{config.__class__.__name__}`")

    used_fields = set()
    for level in config["maturity_model"]:
        if not ("title" in level and "name" in level and "fields" in level):
            raise tk.Invalid(
                f'Malformed UDC Config: "title", "name" and "fields" are required for each level.')
        for field in level["fields"]:
            if "ckanField" in field:
                if field["ckanField"] not in SUPPORTED_CKAN_FIELDS:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided CKAN field `{field['ckanField']}` is not supported.")
                if field["ckanField"] in used_fields:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided CKAN field `{field['ckanField']}` is duplicated.")
                used_fields.add(field["ckanField"])
            else:
                if not ("name" in field and "label" in field):
                    raise tk.Invalid(
                        f"Malformed UDC Config: `name` and `label` is required for custom field.")
                if field.get("type") is not None and field["type"] not in SUPPORTED_FIELD_TYPES:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided field type `{field['type']}` is not supported.")
                if re.match(r'^\w+$', field['name']) is None:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided field name `{field['name']}` is not alpha-numeric.")
                if field["name"] in used_fields:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided CKAN field `{field['ckanField']}` is duplicated.")
                used_fields.add(field["name"])
            if "enable_filter_logic_toggle" in field and not isinstance(field["enable_filter_logic_toggle"], bool):
                raise tk.Invalid(
                    f"Malformed UDC Config: `enable_filter_logic_toggle` must be a boolean.")
    # Check required CKAN fields
    for field_name in REQUIRED_CKAN_FIELDS:
        if field_name not in used_fields:
            raise tk.Invalid(
                f"Malformed UDC Config: Missing the required CKAN field `{field_name}`.")
    return config_str


def udc_mapping_validator(mapping_str):
    try:
        mapping = json.loads(mapping_str)
    except:
        raise tk.Invalid("UDC Mapping: Malformed JSON Format.")
    if not isinstance(mapping, dict):
        raise tk.Invalid(f"UDC Mapping: Expecting a JSON Object but got `{mapping.__class__.__name__}`")

    if not mapping.get("namespaces"):
        raise tk.Invalid("UDC Mapping: Missing namespaces field.")
    if not mapping.get("mappings"):
        raise tk.Invalid("UDC Mapping: Missing mappings field.")
    return mapping_str
