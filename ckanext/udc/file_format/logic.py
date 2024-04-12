from ckan import model, authz, logic
import ckan.plugins as plugins
import logging
import re
import json

from ckanext.udc.graph.queries import get_client
from ckanext.udc.graph.preload import dropdown_reload

log = logging.getLogger(__name__)

GRAPH = "http://data.urbandatacentre.ca/custom-file-format"
PREFIX = GRAPH + "#"


def file_format_create(context, data_dict):
    """
    Any user can create a custom file format.
    """
    
    if plugins.get_plugin('udc').disable_graphdb:
        raise logic.ValidationError("GraphDB integration is not enabled")
    
    user = context.get("user")
    id = data_dict.get('id')
    label = data_dict.get('label')
    
    if not user:
        raise logic.ValidationError("You are not logged in")

    if not label:
        raise logic.ValidationError("file format label is required")
    
    if not id:
        # Replace whitespaces
        id = re.sub('\s', '-', label)
        # Remove unsafe characters in URL
        id = re.sub(r'[<>#%\{\}|\^~\[\]]/', '', id)
        
    query = f"""
    PREFIX cff: <{PREFIX}>
    PREFIX term: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    INSERT DATA {{
        GRAPH <{GRAPH}> {{
            cff:{id} a term:MediaType, owl:NamedIndividual;
                     rdfs:label {json.dumps(label)}
        }}
    }}
    """
    client = get_client()
    try:
        client.execute_sparql(query)
    except Exception as e:
        raise logic.ActionError("Error in KG:" + str(e))
    
    dropdown_reload("file_format")

    return {"success": True, "id": PREFIX + id}


@logic.side_effect_free
def file_formats_get(context):
    """
    Any user can get all custom file formats.
    """
    
    if plugins.get_plugin('udc').disable_graphdb:
        raise logic.ValidationError("GraphDB integration is not enabled")
        
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?uri ?label FROM <{GRAPH}> WHERE {{
        ?uri a term:MediaType;
             rdfs:label ?label.
    }}
    """
    client = get_client()
    try:
        data = client.execute_sparql(query)
    except Exception as e:
        raise logic.ActionError("Error in KG:" + str(e))
    
    result = []
    for item in result["results"]["bindings"]:
        result.append({
            "id": item["uri"]["value"],
            "label": item["label"]["value"]
        })
    return {"success": True, "data": data}


def file_format_delete(context, data_dict):
    """
    Admin can delete a custom file format.
    """
    if plugins.get_plugin('udc').disable_graphdb:
        raise logic.ValidationError("GraphDB integration is not enabled")
    
    user = context.get("user")
    id = data_dict.get('id')
    
    if not user:
        raise logic.ValidationError("You are not logged in")
    
    if not id:
        raise logic.ValidationError("file format id is required")

    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized("You are not authorized to delete this file format")
    
    query = f"""
    PREFIX cff: <{PREFIX}>
    PREFIX term: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    DELETE WHERE {{
        GRAPH <{GRAPH}> {{
            <{id}> a term:MediaType, owl:NamedIndividual;
                     rdfs:label ?label.
            
        }}
    }}
    """
    client = get_client()
    try:
        client.execute_sparql(query)
    except Exception as e:
        raise logic.ActionError("Error in KG:" + str(e))
    
    dropdown_reload("file_format")

    return {"success": True}


def before_package_update(context, data_dict):
    # Pre-process custom file format
    # If the provided file_format is not an URI (starts with http), create the custom file format
    if data_dict.get('file_format'):
        file_formats = data_dict.get('file_format').split(",")
        file_formats_list = []
        for file_format in file_formats:
            if not file_format.startswith("http"):
                file_format_result = file_format_create(context, {"label": file_format})
                file_formats_list.append(file_format_result["id"])
            else:
                file_formats_list.append(file_format)
        data_dict['file_format'] = ','.join(file_formats_list)
