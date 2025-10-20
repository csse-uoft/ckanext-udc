from __future__ import annotations
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
    field_pattern,
    field_type="pfloat",
    indexed=True,
    stored=True,
    multi_valued=False,
    docValues=False,
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
    if docValues:
        payload["add-dynamic-field"]["docValues"] = True

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


def get_field_types():
    """
    Returns a dict {type_name: {...}} of field types defined in the Solr core.
    """
    solr_url, solr_user, solr_password, timeout = get_solr_config()
    try:
        resp = requests.get(
            f"{solr_url}/schema/fieldtypes",
            timeout=timeout,
            auth=HTTPBasicAuth(solr_user, solr_password),
        )
        resp.raise_for_status()
        types = resp.json().get("fieldTypes", [])
        return {t["name"]: t for t in types if "name" in t}
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to fetch field types: {e}")
        return {}


def get_dynamic_fields():
    """
    Returns a dict {pattern: {...}} for dynamic fields.
    """
    solr_url, solr_user, solr_password, timeout = get_solr_config()
    try:
        resp = requests.get(
            f"{solr_url}/schema/dynamicfields",
            timeout=timeout,
            auth=HTTPBasicAuth(solr_user, solr_password),
        )
        resp.raise_for_status()
        dyn = resp.json().get("dynamicFields", [])
        return {d["name"]: d for d in dyn if "name" in d}
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to fetch dynamic fields: {e}")
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


def ensure_language_dynamic_fields(langs):
    """
    Ensure dynamic fields exist for each language:
      *_<lang>_txt  -> text_* analyzer if present, else text_general
      *_<lang>_f    -> string (facets), stored+indexed, multiValued
    """
    types = get_field_types()
    dynamic_fields = get_dynamic_fields()

    # choose analyzer per lang, fallback to text_general
    def analyzer_for(lang):
        tname = f"text_{lang}"
        if tname in types:
            return tname
        return "text_general"

    for lang in langs:
        txt_pat = f"*_{lang}_txt"
        f_pat = f"*_{lang}_f"

        if txt_pat not in dynamic_fields:
            add_dynamic_field(
                txt_pat,
                field_type=analyzer_for(lang),
                indexed=True,
                stored=False,
                multi_valued=True,
            )
        else:
            log.info(f"Dynamic field already present: {txt_pat}")

        if f_pat not in dynamic_fields:
            # facets: exact string, docValues recommended for performance
            add_dynamic_field(
                f_pat,
                field_type="string",
                indexed=True,
                stored=True,
                multi_valued=True,
                docValues=True,
            )
        else:
            log.info(f"Dynamic field already present: {f_pat}")

