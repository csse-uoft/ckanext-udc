from __future__ import annotations

import json
import re

import ckan.plugins.toolkit as tk


# CKAN Config Validator
SUPPORTED_CKAN_FIELDS = [
    "title",
    "description",
    "tags",
    "license_id",
    "organization_and_visibility",
    "source",
    "version",
    "author",
    "author_email",
    "maintainer",
    "maintainer_email",
    "custom_fields",
]
REQUIRED_CKAN_FIELDS = [
    "title",
    "organization_and_visibility",
]
SUPPORTED_FIELD_TYPES = [
    "text",
    "date",
    "datetime",
    "time",
    "number",
    "single_select",
    "multiple_select",
]


def _is_localized_text(val):
    """
    Accept either:
      - a plain string, or
      - a dict of locale -> string (must include 'en'; 'fr' optional)
    """
    if isinstance(val, str):
        return True
    if isinstance(val, dict):
        if "en" not in val:
            return False
        # all provided locale values must be strings (allow empty)
        return all(isinstance(v, str) for v in val.values())
    return False


def _validate_localized_field(field_obj, key, field_path):
    """
    If key exists in field_obj, ensure it's a valid localized text (string or {en:..., fr:...}).
    """
    if key in field_obj and not _is_localized_text(field_obj[key]):
        raise tk.Invalid(
            f"Malformed UDC Config: `{field_path}.{key}` must be a string or an object like "
            f'{{"en": "...", "fr": "..."}} with string values (and must include "en").'
        )


def udc_config_validator(config_str):
    """
    Check whether the UDC config is valid.
    Raise a `tk.Invalid` Error when config is not valid, otherwise return the original config string.
    """
    try:
        config = json.loads(config_str)
    except Exception:
        raise tk.Invalid("UDC Config: Malformed JSON Format.")

    if "maturity_model" not in config:
        raise tk.Invalid("UDC Config: Missing `maturity_model` key.")

    if not isinstance(config["maturity_model"], list):
        raise tk.Invalid(
            f"UDC Config: Expecting `maturity_model` to be a JSON List but got `{config['maturity_model'].__class__.__name__}`"
        )

    used_fields = set()

    for level_idx, level in enumerate(config["maturity_model"], start=1):
        if not ("title" in level and "name" in level and "fields" in level):
            raise tk.Invalid(
                'Malformed UDC Config: "title", "name" and "fields" are required for each level.'
            )

        if not isinstance(level["fields"], list):
            raise tk.Invalid(
                f"Malformed UDC Config: `fields` in level `{level.get('name','?')}` must be a list."
            )

        for field_idx, field in enumerate(level["fields"], start=1):
            field_path = f"maturity_model[{level_idx-1}].fields[{field_idx-1}]"

            # CKAN mapped field
            if "ckanField" in field:
                if field["ckanField"] not in SUPPORTED_CKAN_FIELDS:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided CKAN field `{field['ckanField']}` is not supported."
                    )
                if field["ckanField"] in used_fields:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided CKAN field `{field['ckanField']}` is duplicated."
                    )
                used_fields.add(field["ckanField"])

                # Optional bilingual texts for CKAN fields too
                _validate_localized_field(field, "label", field_path)
                _validate_localized_field(field, "short_description", field_path)
                _validate_localized_field(field, "long_description", field_path)

            # Custom field
            else:
                if not ("name" in field and "label" in field):
                    raise tk.Invalid(
                        "Malformed UDC Config: `name` and `label` is required for custom field."
                    )

                # name must be alphanumeric/underscore
                if re.match(r"^\w+$", field["name"]) is None:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided field name `{field['name']}` is not alpha-numeric."
                    )

                # label must support bilingual (string or {en, fr})
                _validate_localized_field(field, "label", field_path)

                # Optional bilingual descriptions
                _validate_localized_field(field, "short_description", field_path)
                _validate_localized_field(field, "long_description", field_path)

                # type (if present) must be supported
                if (
                    field.get("type") is not None
                    and field["type"] not in SUPPORTED_FIELD_TYPES
                ):
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided field type `{field['type']}` is not supported."
                    )

                # duplicates
                if field["name"] in used_fields:
                    raise tk.Invalid(
                        f"Malformed UDC Config: The provided field `{field['name']}` is duplicated."
                    )
                used_fields.add(field["name"])

                # Non-blocking checks for select options (allow bilingual `text`)
                if field.get("type") in ("single_select", "multiple_select"):
                    if "options" in field:
                        if not isinstance(field["options"], list):
                            raise tk.Invalid(
                                f"Malformed UDC Config: `{field_path}.options` must be a list."
                            )
                        for opt in field["options"]:
                            if not isinstance(opt, dict):
                                raise tk.Invalid(
                                    f"Malformed UDC Config: `{field_path}.options[]` items must be objects."
                                )
                            if "value" not in opt:
                                raise tk.Invalid(
                                    f"Malformed UDC Config: `{field_path}.options[]` missing `value`."
                                )
                            if "text" not in opt:
                                raise tk.Invalid(
                                    f"Malformed UDC Config: `{field_path}.options[]` missing `text`."
                                )
                            # Allow string or localized dict for text
                            if not (_is_localized_text(opt["text"])):
                                raise tk.Invalid(
                                    f"Malformed UDC Config: `{field_path}.options[].text` must be a string or localized object."
                                )
                    if "optionsFromQuery" in field:
                        ofq = field["optionsFromQuery"]
                        if not isinstance(ofq, dict):
                            raise tk.Invalid(
                                f"Malformed UDC Config: `{field_path}.optionsFromQuery` must be an object."
                            )
                        for k in ("text", "value", "query"):
                            if k not in ofq or not isinstance(ofq[k], str):
                                raise tk.Invalid(
                                    f"Malformed UDC Config: `{field_path}.optionsFromQuery.{k}` must be a string."
                                )

            # Boolean sanity check
            if "enable_filter_logic_toggle" in field and not isinstance(
                field["enable_filter_logic_toggle"], bool
            ):
                raise tk.Invalid(
                    "Malformed UDC Config: `enable_filter_logic_toggle` must be a boolean."
                )

    # Check required CKAN fields
    for field_name in REQUIRED_CKAN_FIELDS:
        if field_name not in used_fields:
            raise tk.Invalid(
                f"Malformed UDC Config: Missing the required CKAN field `{field_name}`."
            )

    return config_str


def udc_mapping_validator(mapping_str):
    try:
        mapping = json.loads(mapping_str)
    except:
        raise tk.Invalid("UDC Mapping: Malformed JSON Format.")
    if not isinstance(mapping, dict):
        raise tk.Invalid(
            f"UDC Mapping: Expecting a JSON Object but got `{mapping.__class__.__name__}`"
        )

    if not mapping.get("namespaces"):
        raise tk.Invalid("UDC Mapping: Missing namespaces field.")
    if not mapping.get("mappings"):
        raise tk.Invalid("UDC Mapping: Missing mappings field.")
    return mapping_str
