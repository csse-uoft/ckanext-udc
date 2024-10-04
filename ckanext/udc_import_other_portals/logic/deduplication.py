from ckanext.udc_import_other_portals.logger import ImportLogger
import ckan.plugins.toolkit as toolkit
from ckan.types import Context
import ckan.logic as logic
import ckan.model as model
from ckan.common import current_user
from ckan.lib.search.common import SearchError
import ckan.lib.search as search

from typing import List, Dict, cast
from datetime import datetime

import logging
import time
import ckan
import re

log = logging.getLogger(__name__)


def escape_solr_query(query):
    # List of Solr special characters that need to be escaped
    # (+, -, &, |, !, (, ), {, }, [, ], ^, ", ~, *, ?, :, \, /).
    special_chars = r"[\+\-\&\|\!\(\)\{\}\[\]\^\"\~\*\?\:\\\/]"

    # Use regular expression to find and escape each special character
    escaped_query = re.sub(special_chars, r"\\\g<0>", query)

    return escaped_query


def package_search(context, current_import_config_id, search_filter={}, rows=20):
    # Do not include the package within the same import config id
    fq = f'-cudc_import_config_id:"{current_import_config_id}" -is_unified:"true" '
    for key, value in search_filter.items():
        fq += f'{key}:"{value}" '

    query = {"fq": fq.strip(), "rows": rows}
    logic.check_access("package_search", context, query)
    print(query)
    result = logic.get_action("package_search")(context, query)
    return result


def find_similar_packages(
    context,
    current_import_config_id,
    search_filter={},
    minimun_should_match=80,
    rows=20,
):
    fq = f'-cudc_import_config_id:"{current_import_config_id}" -is_unified:"true" '
    q = []
    qf = ""
    for key, value in search_filter.items():
        q.append(f'{key}:"{value}"')
        qf += key + " "

    query = {
        "defType": "edismax",
        "fq": fq.strip(),
        "q": " AND ".join(q),
        "mm": minimun_should_match,
        "rows": rows,
        "qf": qf.strip(),
    }
    print(query)

    logic.check_access("package_search", context, query)

    result = logic.get_action("package_search")(context, query)
    return result


def find_duplicated_packages(context, package_dict: dict, current_import_config_id):
    # return None, None

    # Exact match with global unique identifier
    global_id = package_dict.get("unique_metadata_identifier")
    if global_id:
        # TODO: How to identify DOI?
        result = package_search(
            context, current_import_config_id, {"unique_metadata_identifier": global_id}
        )
        if result["count"] > 0:
            return result, "global unique identifier"

    # Exact match with title + creation date (This may never works)
    title = package_dict.get("title")
    # metadata_created = package_dict.get("metadata_created")
    # if title and metadata_created:
    #     result = package_search(context, {"title": title, "metadata_created": metadata_created})
    #     if result["count"] > 0:
    #         return result

    # Exact match with title + authors
    author = package_dict.get("author")
    if title and author:
        result = package_search(
            context, current_import_config_id, {"title": title, "author": author}
        )
        if result["count"] > 0:
            return result, "title + authors"

    # Exact match with title + author emails
    author_email = package_dict.get("author_email")
    if title and author:
        result = package_search(
            context,
            current_import_config_id,
            {"title": title, "author_email": author_email},
        )
        if result["count"] > 0:
            return result, "title + author emails"

    # Similarity match with title + description
    description = package_dict.get("notes")
    if title and description:
        result = find_similar_packages(
            context,
            current_import_config_id,
            {"title": title, "notes": description},
        )
        if result["count"] > 0:
            return result, "title + description"

    return None, None


formats = ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]


def parse_date(date_str):
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date format not recognized: {date_str}")


def get_sort_key(item):
    # Prefer 'source_last_updated' if it exists, otherwise use 'metadata_modified'
    if "source_last_updated" in item:
        return parse_date(item["source_last_updated"])
    else:
        return parse_date(item["metadata_modified"])


def create_unified_package(
    context: Context, unified_package_data: dict, linked_packages: list
):
    """
    Create a new unified package, override the existing one if the name collides.

    """
    unified_name = unified_package_data["name"]

    log.info("Create a new unified package " + unified_name)

    unified_package_data = {
        **unified_package_data,
        "type": "catalogue",
        "owner_org": "urban-data-centre",  # hard-coded
        "is_unified": True,
    }

    print("Create", unified_package_data)

    logic.check_access("package_show", context, {"id": unified_name})
    action = "package_create"
    try:
        logic.get_action("package_show")(context, {"id": unified_name})
        action = "package_update"
    except ckan.logic.NotFound:
        pass
    
    logic.check_access("package_show", context, unified_package_data)
    logic.check_access(action, context, unified_package_data)
    result = logic.get_action(action)(context, unified_package_data)

    # Create relations with other linked packages
    relationships_as_subject = [
        {"subject": result["id"], "object": p["id"], "type": "unified_package_of"}
        for p in linked_packages
    ]

    for rel in relationships_as_subject:
        logic.check_access("package_relationship_create", context, rel)
        print("create relation:", rel)
        result = logic.get_action("package_relationship_create")(context, rel)
       
        # notes: solr does not seem to be updated correctly, ignore solr for now
        # solr update here
        # psi = search.PackageSearchIndex()
        # print(result)


def process_duplication(context: Context, linked_packages: list):
    """
    :param merge: Merge with the fields from the existing package
    """

    # Sort based on source_last_updated if available
    sorted_packages = sorted(linked_packages, key=get_sort_key, reverse=True)

    # Find exisiting unified package
    p_has_unified_package = [
        p for p in linked_packages if (p.get("is_unified") == "true")
    ]

    print("p_has_unified_package", p_has_unified_package)

    unified_id = None
    if len(p_has_unified_package) > 1:
        # Merge unified packages
        log.info("Merge unified packages")

        pass
    elif len(p_has_unified_package) == 1:
        # Update the unified package
        log.info("Update the unified package")

        unified_name = p_has_unified_package[0]["name"]

        unified_package_data = {
            "id": p_has_unified_package[0]["id"], # Do not create another unified package
            "title": "Unified: " + p_has_unified_package[0]["title"],
            "name": unified_name,
            "notes": sorted_packages[0]["notes"],
            # "relationships_as_subject": [{"object": p["id"], "type": "unified_package_of"} for p in linked_packages]
        }
        create_unified_package(context, unified_package_data, linked_packages)
        
    else:
        # Create a new unified package
        log.info("Create a new unified package")
        unified_name = "unified-" + sorted_packages[0]["name"]
        unified_package_data = {
            "title": "Unified: " + sorted_packages[0]["title"],
            "name": unified_name,
            "notes": sorted_packages[0]["notes"],
            # "relationships_as_subject": [{"object": p["id"], "type": "unified_package_of"} for p in linked_packages]
        }
        create_unified_package(context, unified_package_data, linked_packages)
