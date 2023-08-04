import logging
import ckan
import ckan.plugins.toolkit as tk
import ckan.plugins as plugins

from datetime import datetime
from .sparql_client import SparqlClient

log = logging.getLogger(__name__)


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

def get_num_paths(uri_a: str, uri_b: str):
    """
    Find the number of paths from 'uri_a' to 'uri_b'.
    https://graphdb.ontotext.com/documentation/10.2/graph-path-search.html
    """
    query = f"""
    PREFIX path: <http://www.ontotext.com/path#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?pathIndex ?edgeIndex ?edge
    WHERE {{
        SERVICE path:search {{
            [] path:findPath path:allPaths ;
            path:sourceNode <{uri_a}> ;
            path:destinationNode <{uri_b}> ;
            path:pathIndex ?pathIndex ;
            path:resultBindingIndex ?edgeIndex ;
            path:resultBinding ?edge ;
            .
        }}
    }}
    """
    client = get_client()
    result = client.execute_sparql(query)
    print('num_paths=', len(result["results"]["bindings"]), uri_a, uri_b)
    return len(result["results"]["bindings"])
    