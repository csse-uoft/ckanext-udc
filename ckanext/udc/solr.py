"""
Please note that applying this solr schema changes will require a reindex of the dataset.
Probably also rebooting the solr server after the changes then reindex.

Available Field Types: (Also see <solr_url>/schema/fieldtypes)
----------------------
- string:
    - Exact match only, no tokenization or analysis.
    - Use for IDs, keywords, or non-searchable fields.
    - Used by license (id), tags, organization, title_string, url, version
    - Used for retrieving facets. 

- text
    - Natural language search (e.g., descriptions, long-form text)

- text_general:
    - Tokenized text with lowercase filter and word splitting.
    - Good for full-text search.
    - General text search without stemming (e.g., titles, keywords)

- text_ngram:
    - Tokenized text with lowercase filter, n-gram tokenization.
    - Good for Autocomplete, Fuzzy Matching, Partial-Word Search
    - Used by name_ngram, title_ngram.

- boolean:
    - Stores `true` or `false` values.

- pint:
    - 32-bit signed integer (numeric).

- plong:
    - 64-bit signed integer (for large numbers).

- pfloat:
    - Single-precision floating point number.

- pdouble:
    - Double-precision floating point number.

- date:
    - ISO 8601 format (`YYYY-MM-DDThh:mm:ssZ`).
    - Supports range queries.

"""

import ckan.model as model
import logging
import json
import requests
from requests.auth import HTTPBasicAuth

from ckan.plugins.toolkit import config
from ckan.lib.search.common import SolrSettings

log = logging.getLogger(__name__)


def get_solr_config():
    solr_url, solr_user, solr_password = SolrSettings.get()
    timeout = config.get("ckan.requests.timeout", 10)  # Default timeout is 10 seconds
    url = solr_url.rstrip("/")
    return url, solr_user, solr_password, timeout


def get_extras_fields():
    """
    Fetch all fields from Solr and return those that start with 'extras_'.
    """
    fields = get_fields()
    extras_fields = {k: v for k, v in fields.items() if k.startswith("extras_")}
    return extras_fields


def delete_extras_fields():
    """
    Deletes all fields in Solr that start with 'extras_'.
    """
    extras_fields = get_extras_fields()

    if not extras_fields:
        log.info("No 'extras_*' fields found. Nothing to delete.")
        return

    solr_url, solr_user, solr_password, timeout = get_solr_config()

    for field in extras_fields.keys():
        payload = {"delete-field": {"name": field}}
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                f"{solr_url}/schema",
                data=json.dumps(payload),
                headers=headers,
                auth=HTTPBasicAuth(solr_user, solr_password),
                timeout=timeout,
            )
            response.raise_for_status()
            log.info(f"Deleted field: {field}")

        except requests.exceptions.RequestException as e:
            log.error(f"Error deleting field {field}: {e}")


def delete_field(field_name):
    """
    Deletes a field in Solr.
    """
    solr_url, solr_user, solr_password, timeout = get_solr_config()

    payload = {"delete-field": {"name": field_name}}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{solr_url}/schema",
            data=json.dumps(payload),
            headers=headers,
            auth=HTTPBasicAuth(solr_user, solr_password),
            timeout=timeout,
        )
        response.raise_for_status()
        log.info(f"Deleted field: {field_name}")

    except requests.exceptions.RequestException as e:
        log.error(f"Error deleting field {field_name}: {e}")


def add_field(
    field_name,
    field_type="string",
    indexed=True,
    stored=True,
    multi_valued=False,
    docValues=False,
):
    """
    Adds a new field to Solr dynamically.
    """
    solr_url, solr_user, solr_password, timeout = get_solr_config()

    payload = {
        "add-field": {
            "name": field_name,
            "type": field_type,
            "indexed": indexed,
            "stored": stored,
            "multiValued": multi_valued,
            "docValues": docValues,
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{solr_url}/schema",
            data=json.dumps(payload),
            headers=headers,
            auth=HTTPBasicAuth(solr_user, solr_password),
            timeout=timeout,
        )
        response.raise_for_status()
        log.info(f"Field '{field_name}' added successfully.")

    except requests.exceptions.RequestException as e:
        log.error(f"Error adding field '{field_name}': {e}")


def add_dynamic_field(
    field_pattern, field_type="pfloat", indexed=True, stored=True, multi_valued=False
):
    """
    Adds a new dynamic field to Solr.
    """
    solr_url, solr_user, solr_password, timeout = get_solr_config()

    payload = {
        "add-dynamic-field": {
            "name": field_pattern,
            "type": field_type,
            "indexed": indexed,
            "stored": stored,
            "multiValued": multi_valued,
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{solr_url}/schema",
            data=json.dumps(payload),
            headers=headers,
            auth=HTTPBasicAuth(solr_user, solr_password),
            timeout=timeout,
        )
        response.raise_for_status()
        log.info(f"Dynamic field '{field_pattern}' added successfully.")

    except requests.exceptions.RequestException as e:
        log.error(f"Error adding dynamic field '{field_pattern}': {e}")


def get_fields():
    """
    Fetches all fields from Solr.
    """
    solr_url, solr_user, solr_password, timeout = get_solr_config()

    try:
        response = requests.get(
            f"{solr_url}/schema/fields",
            timeout=timeout,
            auth=HTTPBasicAuth(solr_user, solr_password),
        )
        response.raise_for_status()
        fields = response.json()["fields"]

        res = {}
        for field in fields:
            res[field["name"]] = field

        # for field in fields:
        #     log.info(f"Field: {field['name']} (Type: {field['type']})")
        return res

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to fetch fields: {e}")
        return {}


def add_copy_field(source_field, dest_field):
    """
    Adds a copyField rule to Solr.
    """
    solr_url, solr_user, solr_password, timeout = get_solr_config()

    payload = {"add-copy-field": {"source": source_field, "dest": dest_field}}

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{solr_url}/schema",
            data=json.dumps(payload),
            headers=headers,
            auth=HTTPBasicAuth(solr_user, solr_password),
            timeout=timeout,
        )
        response.raise_for_status()
        log.info(f"Copy field rule added: {source_field} -> {dest_field}")

    except requests.exceptions.RequestException as e:
        log.error(f"Error adding copy field rule: {e}")


def delete_copy_field(field_name, dest_field=None):
    """
    Deletes a copyField rule in Solr.
    """
    solr_url, solr_user, solr_password, timeout = get_solr_config()

    payload = {"delete-copy-field": {"source": field_name, "dest": dest_field}}

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{solr_url}/schema",
            data=json.dumps(payload),
            headers=headers,
            auth=HTTPBasicAuth(solr_user, solr_password),
            timeout=timeout,
        )
        response.raise_for_status()
        log.info(f"Deleted copy field rule: {field_name}")

    except requests.exceptions.RequestException as e:
        log.error(f"Error deleting copy field rule: {e}")


def update_solr_maturity_model_fields(maturity_model: list):
    """
    Update Solr schema to include maturity model fields.
    """
    # Generate new solr fields based on maturity model
    new_fields = {}
    for level in maturity_model:
        for field in level["fields"]:
            if "ckanField" not in field:
                if field.get("type") is None or field["type"] == "text":
                    # Text support partial search, but not exact match
                    # For facet search, use the field name without 'extras_'
                    new_fields[f"extras_{field['name']}"] = {
                        "name": f"extras_{field['name']}",
                        "type": "text_ngram",
                        "multiValued": False,
                        "indexed": True,
                        "stored": True,
                    }
                # boolean is not implemented yet
                # elif field["type"] == "boolean":
                #     new_fields[f"extras_{field['name']}"] = {
                #         "name": f"extras_{field['name']}",
                #         "type": "boolean",
                #         "multiValued": False,
                #         "indexed": True,
                #         "stored": True,
                #     }
                elif (
                    field["type"] == "date"
                    or field["type"] == "datetime"
                    or field["type"] == "time"
                ):
                    new_fields[f"extras_{field['name']}"] = {
                        "name": f"extras_{field['name']}",
                        "type": "date",
                        "multiValued": False,
                        "indexed": True,
                        "stored": True,
                        "docValues": True,
                    }
                    print(new_fields[f"extras_{field['name']}"])
                elif field["type"] == "number":
                    new_fields[f"extras_{field['name']}"] = {
                        "name": f"extras_{field['name']}",
                        "type": "pfloat",
                        "multiValued": False,
                        "indexed": True,
                        "stored": True,
                        "docValues": True,
                    }
                elif field["type"] == "multiple_select":
                    # Does not support partial search
                    new_fields[f"extras_{field['name']}"] = {
                        "name": f"extras_{field['name']}",
                        "type": "string",
                        "multiValued": True,
                        "stored": True,
                        "indexed": True,
                    }
                elif field["type"] == "single_select":
                    # Does not support partial search
                    new_fields[f"extras_{field['name']}"] = {
                        "name": f"extras_{field['name']}",
                        "type": "string",
                        "multiValued": False,
                        "indexed": True,
                        "stored": True,
                    }
                else:
                    raise ValueError(f"Unknown field type: {field['type']}")

    # Fetch existing fields
    current_fields = get_extras_fields()

    # Compare fields and add new fields
    for current_field_name, current_field in current_fields.items():

        if current_field_name not in new_fields:
            # Delete field
            delete_field(current_field_name)
        else:
            # Update field if changed
            new_field = new_fields[current_field_name]
            if (
                new_field["type"] != current_field["type"]
                or new_field["indexed"] != current_field["indexed"]
                or new_field["stored"] != current_field["stored"]
                or new_field["multiValued"] != current_field["multiValued"]
                or new_field.get("docValues", False)
                != current_field.get("docValues", False)
            ):
                print(new_field, current_field)
                delete_field(current_field_name)
                add_field(
                    new_field["name"],
                    new_field["type"],
                    new_field["indexed"],
                    new_field["stored"],
                    new_field["multiValued"],
                    new_field.get("docValues", False),
                )
            new_fields.pop(current_field_name)

    # Add missing fields
    for field_name, field in new_fields.items():
        add_field(
            field["name"],
            field["type"],
            field["indexed"],
            field["stored"],
            field["multiValued"],
            field.get("docValues", False),
        )

    if len(new_fields) == 0:
        log.info("No new fields to add.")
    else:
        log.info(f"Added {len(new_fields)} new fields.")

    # Make tags partial searchable
    all_fields = get_fields()
    if "tags_ngram" not in all_fields:
        add_field(
            "tags_ngram", "text_ngram", indexed=True, stored=True, multi_valued=True
        )
        # delete_copy_field("tags", "tags_ngram")
        add_copy_field("tags", "tags_ngram")
        log.info("Added tags_ngram field.")
    else:
        log.info("tags_ngram field already exists.")
