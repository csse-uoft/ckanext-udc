import ckan.model as model
import logging
import requests
from requests.auth import HTTPBasicAuth

from ckan.plugins.toolkit import config
from ckan.lib.search.common import SolrSettings

log = logging.getLogger(__name__)


def init_relationships():
    """
    Initialize custom 'relationship type' in PackageRelationship.
    """

    # List of (type, corresponding_reverse_type)
    # e.g. (A "depends_on" B, B has a "dependency_of" A)
    cutsom_relationships = [("unified_package_of", "has_unified_package")]
    cutsom_relationships_printable = [
        ("is a unified package of", "has unified package")
    ]

    already_loaded = False
    for fwd, rev in model.PackageRelationship.types:
        if fwd == cutsom_relationships[0][0]:
            already_loaded = True
            break

    if already_loaded:
        log.info("Custom relationship types already loaded!")
        return

    model.PackageRelationship.types.append(*cutsom_relationships)
    model.PackageRelationship.types_printable.append(*cutsom_relationships_printable)

    # Remove caches
    if hasattr(model.PackageRelationship, "all_types"):
        del model.PackageRelationship.all_types
    if hasattr(model.PackageRelationship, "fwd_types"):
        del model.PackageRelationship.fwd_types
    if hasattr(model.PackageRelationship, "rev_types"):
        del model.PackageRelationship.rev_types

    # Load/Ensure Solr Schema
    solr_url, solr_user, solr_password = SolrSettings.get()

    for relationships in cutsom_relationships:
        for relationship in relationships:
            schema = {
                "name": relationship,
                "type": "text",
                "multiValued": True,
                "indexed": True,
                "stored": True,
            }
            url = solr_url.strip("/")

            timeout = config.get("ckan.requests.timeout")
            response = requests.get(
                url + f"/schema/fields/{relationship}",
                timeout=timeout,
                auth=(
                    HTTPBasicAuth(solr_user, solr_password)
                    if solr_user is not None and solr_password is not None
                    else None
                ),
            )

            # Update solr schema if requried
            if response.json().get("error"):

                headers = {"Content-type": "application/json"}
                response = requests.post(
                    url + "/schema",
                    timeout=timeout,
                    auth=(
                        HTTPBasicAuth(solr_user, solr_password)
                        if solr_user is not None and solr_password is not None
                        else None
                    ),
                    headers=headers,
                    json={"add-field": schema},
                )
                if response.status_code >= 400:
                    log.error(
                        f"Failed to update solr scheme for '{relationship}': {response.json()}"
                    )
                    exit(-1)

                log.info(f"Updated solr scheme for {relationship}: {response.json()}")
            else:
                # Compare schema, update if different
                existing_schema = response.json()["field"]
                schema_diff = {
                    key: value
                    for key, value in schema.items()
                    if existing_schema.get(key) != value
                }
                print(schema_diff)
                if schema_diff:
                    headers = {"Content-type": "application/json"}
                    response = requests.post(
                        url + "/schema",
                        timeout=timeout,
                        auth=(
                            HTTPBasicAuth(solr_user, solr_password)
                            if solr_user is not None and solr_password is not None
                            else None
                        ),
                        headers=headers,
                        json={"replace-field": schema},
                    )
                    if response.status_code >= 400:
                        log.error(
                            f"Failed to update solr schema for '{relationship}': {response.json()}"
                        )
                        exit(-1)

                    log.info(
                        f"Updated solr schema for {relationship} with changes: {schema_diff}"
                    )
                else:
                    log.info(
                        f"Schema for {relationship} is up-to-date: {existing_schema}"
                    )
                
                # log.info(
                #     f"Skipped updated solr scheme for {relationship}: {response.json()}"
                # )

    log.info("Loaded custom relationship types!")
