import logging
import ckan
import ckan.plugins.toolkit as tk
import ckan.plugins as plugins

from datetime import datetime
from .sparql_client import SparqlClient

log = logging.getLogger(__name__)


ckanFieldMapping = {
    "title": "name",
    "id": "id",
    "description": "notes",
    "tags": "tags",
    "url": "url",
}


def get_client():
    return plugins.get_plugin('udc').sparql_client


def get_uri_as_object_usage(object_uri):
    """Return the number of occurrence when the uri is used as an object."""
    query = f"""
    select (count(?s) as ?cnt) where {{
        ?s ?p <{object_uri}> .
    }}
    """
    client = get_client()
    result = client.execute_sparql(query)
    
    return len(result["results"]["bindings"])

def get_o_by_sp(s, p):
    query = f"""
    select ?o where {{
        <{s}> <{p}> ?o .
    }} LIMIT 1"""
    client = get_client()
    result = client.execute_sparql(query)
    if len(result["results"]["bindings"]) > 0:
        return result["results"]["bindings"][0]["o"]["value"]
    return None
    
