import ckan.plugins as plugins
import ckan.plugins.toolkit as tk

import rdflib
from rdflib import Graph, term
from rdflib.namespace import split_uri
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib.serializer import Serializer
import pyld
import logging
import json

from .serializer import *
from .template import compile_template, compile_with_temp_value
from .mapping_helpers import all_helpers
from .ckan_field import prepare_data_dict
from .queries import get_uri_as_object_usage, get_client, get_num_paths


def get_mappings():
    # print("mappings: ", plugins.get_plugin('udc').mappings)
    return pyld.jsonld.expand(plugins.get_plugin('udc').mappings)


def find_existing_instance_uris(data_dict) -> list:
    """Return a list of URIs"""
    prepared_dict = prepare_data_dict(data_dict)
    g = Graph()
    compiled_template = compile_with_temp_value(get_mappings(), all_helpers,
                                                prepared_dict)
    catalogue_uri = compiled_template["@id"]
    # print("compiled_template", compiled_template)
    
    # Ignore warnings from rdflib.term when parsing the template with temp values
    logging.getLogger("rdflib.term").setLevel(logging.ERROR)
    g.parse(data=compiled_template, format='json-ld')
    logging.getLogger("rdflib.term").setLevel(logging.WARNING)

    # Get all uris that is used as subject (s, any, any)
    subjects = set(g.subjects(None, None))

    # Find all (s1, p, s2) triples and generate mappings: s -> tuple(s, p, o)
    s2spo = {}
    for s1 in subjects:
        for s2 in subjects:
            if s1 == s2:
                continue
            for p in g.predicates(s1, s2):
                if s1 in s2spo:
                    s2spo[s1].append((s1, p, s2))
                else:
                    s2spo[s1] = [(s1, p, s2)]
    # print("s2spo", s2spo)

    # Generate s -> vars mappings
    s2var = {}
    cnt = 0
    for s in subjects:
        if s != catalogue_uri:
            s2var[str(s)] = f'var{cnt}'
            cnt += 1

    # print('s2var', s2var)

    # o -> (s, sparql part)
    query_parts = {}

    # Generate select query
    triples = ''
    for spos in s2spo.values():
        for s, p, o in spos:
            # First level
            if s == rdflib.term.URIRef(catalogue_uri):
                query_parts[str(o)] = (str(s), f"<{s}> <{p}> ?{s2var[str(o)]}")
                # triples += f"\tOPTIONAL {{ <{s}> <{p}> ?{s2var[str(o)]} }}\n"
            else:
                query_parts[str(o)] = (str(s), f"?{s2var[str(s)]} <{p}> ?{s2var[str(o)]}")
                # triples += f"\tOPTIONAL {{ ?{s2var[str(s)]} <{p}> ?{s2var[str(o)]} }}\n"
    for o, (s, part) in query_parts.items():
        if s == catalogue_uri:
            triples += f"\tOPTIONAL {{ {part} }}\n"
        else:
            path = [part]
            curr = s
            max_iteration = 100
            i = 0
            while curr != catalogue_uri:
                upper_level = query_parts.get(curr)
                if not upper_level: 
                    raise ValueError("Cannot find path to the catalogue entry")
                path.append(upper_level[1])
                curr = upper_level[0]
                i += 1
                if max_iteration < i:
                    raise ValueError("Reached max iteration to find the path to the catalogue entry")
            inner_query = ''
            for step in path:
                inner_query = f"\tOPTIONAL {{ {step} {inner_query} }}\n"
            triples += inner_query


    query = f'SELECT DISTINCT * WHERE {{\n{triples}}}'
    # print('select-query', query)
    client = get_client()
    result = client.execute_sparql(query)
    if len(result["results"]["bindings"]) == 0:
        return {}
    elif len(result["results"]["bindings"]) > 1:
        raise ValueError("KG may not be consistent.")
    
    s2uri = {}
    results = result["results"]["bindings"][0]
    for s, var in s2var.items():
        if results.get(var) and results[var]["type"] != "bnode": # Skip blank nodes
            s2uri[s] = results[var]["value"]
    # print("s2uri", s2uri)
    return [*s2uri.values()]


def onUpdateCatalogue(context, data_dict):
    # print(f"onUpdateCatalogue Update: ", data_dict)
    
    # Remove empty fields
    for key in [*data_dict.keys()]:
        if data_dict[key] == '':
            del data_dict[key]

    uris_to_del = find_existing_instance_uris(data_dict)
    
    # print("data_dict", json.dumps(data_dict, indent=2))
    prepared_dict = prepare_data_dict(data_dict)
    # print("prepared_dict", json.dumps(prepared_dict, indent=2))
    compiled_template = compile_template(get_mappings(), all_helpers,
                                         prepared_dict)
    # print("compiled_template", json.dumps(compiled_template, indent=2))
    catalogue_uri = compiled_template["@id"]

    g = Graph()
    g.parse(data=compiled_template, format='json-ld')

    prefixes = {}

    def normalize_uri(uri):
        """Normalize a URI into a QName(short name) and store the prefix."""
        prefix, uri, val = g.compute_qname(uri)
        prefixes[prefix] = str(uri)
        return f"{prefix}:{val}"

    def generate_delete_sparql():
        subjects = set(uris_to_del)
        subjects.add(catalogue_uri)
        # for s, p, o in g:
        #     subjects.add(s)
        #     print(s, p, o)

        delete_clause = []

        # Find the occurrences of the `s` is used as an object
        for s in subjects:
            # If 's' is not used by the current catalogue, skip it
            paths_used_by_catalogue = get_num_paths(catalogue_uri, s)
            num_paths_used_by_catalogue = len(paths_used_by_catalogue)
            if num_paths_used_by_catalogue == 0:
                continue
            # Check if 's' is used by any other triples as an object
            uri_as_object_usage = get_uri_as_object_usage(s)
            # print('uri_as_object_usage', uri_as_object_usage, num_paths_used_by_catalogue)

            if uri_as_object_usage == num_paths_used_by_catalogue:
                # Remove this instance if it is only used by this catalogue
                delete_clause.append(f'{normalize_uri(s)} ?p ?o')
                delete_clause.append(f'?s ?p {normalize_uri(s)}')
            elif uri_as_object_usage > num_paths_used_by_catalogue:
                # Remove this instance in this catalogue only
                for spos in paths_used_by_catalogue.values():
                    for _s, p, o in spos:
                        # Remove the last link only
                        if o == rdflib.term.URIRef(s):
                            delete_clause.append(f'{normalize_uri(_s)} {normalize_uri(p)} {normalize_uri(o)}')
        
        # Remove all triples direcly linked to the catalogue
        delete_clause.append(f'{normalize_uri(catalogue_uri)} ?p ?o')


        return '\n'.join([f"PREFIX {prefix}: <{ns}>" for prefix, ns in prefixes.items()]) + '\n' \
            + '\n'.join([f"DELETE WHERE {{\n\t{triple}.\n}};" for triple in delete_clause])

    delete_query = generate_delete_sparql()
    print('delete_query')
    print(delete_query)
    print(g.serialize(format="sparql-insert"))

    client = get_client()
    client.execute_sparql(delete_query)
    client.execute_sparql(g.serialize(format="sparql-insert"))


def onDeleteCatalogue(context, data_dict):
    # print(f"onDeleteCatalogue: ", data_dict)
    
    uris_to_del = find_existing_instance_uris(data_dict)
    
    prepared_dict = prepare_data_dict(data_dict)
    compiled_template = compile_with_temp_value(get_mappings(), all_helpers,
                                                prepared_dict)
    # print("compiled_template", compiled_template)
    catalogue_uri = compiled_template["@id"]

    g = Graph()
    logging.getLogger("rdflib.term").setLevel(logging.ERROR)
    g.parse(data=compiled_template, format='json-ld')
    logging.getLogger("rdflib.term").setLevel(logging.WARNING)

    prefixes = {}

    def normalize_uri(uri):
        """Normalize a URI into a QName(short name) and store the prefix."""
        prefix, uri, val = g.compute_qname(uri)
        prefixes[prefix] = str(uri)
        
        # Sometimes the uri ends with a dot, this will result in a wrong prefix when using the prefixed name
        if val.endswith('.'): 
            return f"<{uri}>"
        
        return f"{prefix}:{val}"

    def generate_delete_sparql():
        subjects = set(uris_to_del)
        subjects.add(catalogue_uri)
        # for s, p, o in g:
        #     subjects.add(s)
        #     print(s, p, o)

        delete_clause = []
        # Find the occurrences of the `s` is used as an object
        for s in subjects:
            # If 's' is not used by the current catalogue, skip it
            paths_used_by_catalogue = get_num_paths(catalogue_uri, s)
            num_paths_used_by_catalogue = len(paths_used_by_catalogue)
            if num_paths_used_by_catalogue == 0:
                continue
            # Check if 's' is used by any other triples as an object
            uri_as_object_usage = get_uri_as_object_usage(s)
            # print('uri_as_object_usage', uri_as_object_usage, num_paths_used_by_catalogue)
            if uri_as_object_usage == num_paths_used_by_catalogue:
                delete_clause.append(f'{normalize_uri(s)} ?p ?o')
                delete_clause.append(f'?s ?p {normalize_uri(s)}')
            elif uri_as_object_usage > num_paths_used_by_catalogue:
                # Remove this instance in this catalogue only
                for spos in paths_used_by_catalogue.values():
                    for s, p, o in spos:
                        delete_clause.append(f'{normalize_uri(s)} {normalize_uri(p)} {normalize_uri(o)}')
        
        # Remove all triples direcly linked to the catalogue
        delete_clause.append(f'{normalize_uri(catalogue_uri)} ?p ?o')

        return '\n'.join([f"PREFIX {prefix}: <{ns}>" for prefix, ns in prefixes.items()]) + '\n' \
            + '\n'.join([f"DELETE WHERE {{\n\t{triple}.\n}};" for triple in delete_clause])

    delete_query = generate_delete_sparql()
    print('delete_query')
    print(delete_query)

    client = get_client()
    client.execute_sparql(delete_query)


def get_catalogue_graph(package_id_or_name: str, format: str = "turtle") -> str:
    """
    Retrieve the knowledge graph for a specific catalogue entry.
    
    Args:
        package_id_or_name: The package ID or name
        format: Output format - 'turtle', 'json-ld', 'xml', 'n3', 'nt' (default: 'turtle')
    
    Returns:
        str: Serialized RDF graph in the requested format
    
    Raises:
        ValueError: If package not found or invalid format
    """
    # Get the package to ensure it exists and get its ID
    try:
        package = tk.get_action('package_show')({}, {'id': package_id_or_name})
    except tk.ObjectNotFound:
        raise ValueError(f"Package '{package_id_or_name}' not found")
    
    package_id = package.get('id')
    if not package_id:
        raise ValueError("Package ID not found")
    
    # Get the catalogue URI by compiling the template with the package data
    prepared_dict = prepare_data_dict(package)
    compiled_template = compile_with_temp_value(get_mappings(), all_helpers, prepared_dict)
    catalogue_uri = compiled_template["@id"]
    
    # Validate format
    valid_formats = {'turtle', 'json-ld', 'xml', 'n3', 'nt', 'pretty-xml'}
    if format not in valid_formats:
        raise ValueError(f"Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}")
    
    # Build SPARQL CONSTRUCT query to retrieve all triples related to this catalogue entry
    # We retrieve:
    # 1. All triples where the catalogue URI is the subject
    # 2. All triples from objects (both blank nodes and URIs)
    # 3. Nested blank nodes up to 3 levels deep
    query = f"""
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX cudr: <http://data.urbandatacentre.ca/>
    PREFIX cudrc: <http://data.urbandatacentre.ca/catalogue/>
    PREFIX fair: <http://ontology.eil.utoronto.ca/fair#>
    PREFIX adms: <http://www.w3.org/ns/adms#>
    PREFIX locn: <http://www.w3.org/ns/locn#>
    PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX oa: <http://www.w3.org/ns/oa#>
    PREFIX vcard: <http://www.w3.org/2006/vcard/ns#>
    PREFIX dqv: <http://www.w3.org/ns/dqv#>
    PREFIX sc: <http://schema.org/>
    
    CONSTRUCT {{
        <{catalogue_uri}> ?p ?o .
        ?o ?p2 ?o2 .
        ?o2 ?p3 ?o3 .
        ?o3 ?p4 ?o4 .
    }}
    WHERE {{
        {{
            # Level 1: Direct properties of catalogue
            <{catalogue_uri}> ?p ?o .
        }}
        UNION
        {{
            # Level 2: Properties of objects (expand both URIs and blank nodes)
            <{catalogue_uri}> ?p ?o .
            ?o ?p2 ?o2 .
        }}
        UNION
        {{
            # Level 3: Properties of nested objects
            <{catalogue_uri}> ?p ?o .
            ?o ?p2 ?o2 .
            ?o2 ?p3 ?o3 .
        }}
        UNION
        {{
            # Level 4: Properties of deeply nested objects
            <{catalogue_uri}> ?p ?o .
            ?o ?p2 ?o2 .
            ?o2 ?p3 ?o3 .
            ?o3 ?p4 ?o4 .
        }}
    }}
    """
    
    # Execute query - execute_sparql will automatically detect CONSTRUCT and return Turtle text
    client = get_client()
    try:
        result = client.execute_sparql(query)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error executing SPARQL query for package {package_id}: {str(e)}")
        raise ValueError(f"Failed to retrieve graph: {str(e)}")
    
    # Parse the result into an RDF graph
    g = Graph()
    
    # Bind namespace prefixes to the graph for better serialization
    g.bind('xsd', 'http://www.w3.org/2001/XMLSchema#')
    g.bind('owl', 'http://www.w3.org/2002/07/owl#')
    g.bind('dcat', 'http://www.w3.org/ns/dcat#')
    g.bind('skos', 'http://www.w3.org/2004/02/skos/core#')
    g.bind('rdfs', 'http://www.w3.org/2000/01/rdf-schema#')
    g.bind('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    g.bind('dct', 'http://purl.org/dc/terms/')
    g.bind('dcterms', 'http://purl.org/dc/terms/')
    g.bind('foaf', 'http://xmlns.com/foaf/0.1/')
    g.bind('cudr', 'http://data.urbandatacentre.ca/')
    g.bind('cudrc', 'http://data.urbandatacentre.ca/catalogue/')
    g.bind('fair', 'http://ontology.eil.utoronto.ca/fair#')
    g.bind('adms', 'http://www.w3.org/ns/adms#')
    g.bind('locn', 'http://www.w3.org/ns/locn#')
    g.bind('odrl', 'http://www.w3.org/ns/odrl/2/')
    g.bind('prov', 'http://www.w3.org/ns/prov#')
    g.bind('oa', 'http://www.w3.org/ns/oa#')
    g.bind('vcard', 'http://www.w3.org/2006/vcard/ns#')
    g.bind('dqv', 'http://www.w3.org/ns/dqv#')
    g.bind('sc', 'http://schema.org/')
    
    # Result is now a Turtle string from the SPARQL endpoint
    if result and isinstance(result, str) and result.strip():
        try:
            # Parse as Turtle (the default format returned by GraphDB for CONSTRUCT)
            g.parse(data=result, format='turtle')
        except Exception as e:
            logging.getLogger(__name__).error(f"Error parsing SPARQL result: {str(e)}")
            # Return empty graph if parsing fails
            pass
    else:
        # Empty result
        logging.getLogger(__name__).warning(f"No triples found for catalogue {package_id}")
    
    # Serialize to requested format
    try:
        return g.serialize(format=format)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error serializing graph to {format}: {str(e)}")
        raise ValueError(f"Failed to serialize graph to {format}: {str(e)}")
