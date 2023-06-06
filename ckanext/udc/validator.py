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


def udc_config_validor(config_str):
    """
    Check whether the UDC config is valid.
    Raise a `tk.Invalid` Error when config is not valid, otherwire return the original config string.
    """
    try:
        config = json.loads(config_str)
    except:
        raise tk.Invalid("UDC Config: Malformed JSON Format.")

    used_fields = set()
    for level in config:
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
                if re.match(r'^\w+$', field['name']) is None:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided field name `{field['name']}` is not alpha-numeric.")
                if field["name"] in used_fields:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided CKAN field `{field['ckanField']}` is duplicated.")
                used_fields.add(field["name"])
    # Check required CKAN fields
    for field_name in REQUIRED_CKAN_FIELDS:
        if field_name not in used_fields:
            raise tk.Invalid(
                f"Malformed UDC Config: Missing the required CKAN field `{field_name}`.")
    return config_str
