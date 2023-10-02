import ckan.plugins as plugins

import rdflib
from rdflib import Graph, term
from rdflib.namespace import split_uri
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib.serializer import Serializer
import pyld

from .serializer import *
from .template import compile_template, compile_with_temp_value
from .mapping_helpers import all_helpers
from .ckan_field import CKANField
from .queries import get_uri_as_object_usage, get_client, get_num_paths


def get_mappings():
    print("mappings: ", plugins.get_plugin('udc').mappings)
    return pyld.jsonld.expand(plugins.get_plugin('udc').mappings)


def find_existing_instance_uris(data_dict) -> list:
    """Return a list of URIs"""
    ckanField = CKANField(data_dict)
    g = Graph()
    compiled_template = compile_with_temp_value(get_mappings(), all_helpers,
                                                {**data_dict, "ckanField": ckanField})
    catalogue_uri = compiled_template["@id"]
    print("compiled_template", compiled_template)
    g.parse(data=compiled_template, format='json-ld')

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
    print("s2spo", s2spo)

    # Generate s -> vars mappings
    s2var = {}
    cnt = 0
    for s in subjects:
        if s != catalogue_uri:
            s2var[str(s)] = f'var{cnt}'
            cnt += 1

    print('s2var', s2var)

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
    print('select-query', query)
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
    print("s2uri", s2uri)
    return [*s2uri.values()]


def onUpdateCatalogue(context, data_dict):
    print(f"onUpdateCatalogue Update: ", data_dict)
    ckanField = CKANField(data_dict)

    # Remove empty fields
    for key in [*data_dict.keys()]:
        if data_dict[key] == '':
            del data_dict[key]

    uris_to_del = find_existing_instance_uris(data_dict)

    compiled_template = compile_template(get_mappings(), all_helpers,
                                         {**data_dict, "ckanField": ckanField, })
    print("compiled_template", compiled_template)
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
            num_paths_used_by_catalogue = get_num_paths(catalogue_uri, s)
            if num_paths_used_by_catalogue == 0:
                continue
            # Check if 's' is used by any other triples as an object
            uri_as_object_usage = get_uri_as_object_usage(s)
            print('uri_as_object_usage', uri_as_object_usage, num_paths_used_by_catalogue)
            if uri_as_object_usage == num_paths_used_by_catalogue:
                delete_clause.append(f'{normalize_uri(s)} ?p ?o')
                delete_clause.append(f'?s ?p {normalize_uri(s)}')

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
    print(f"onDeleteCatalogue: ", data_dict)
    ckanField = CKANField(data_dict)

    uris_to_del = find_existing_instance_uris(data_dict)

    compiled_template = compile_with_temp_value(get_mappings(), all_helpers,
                                                {**data_dict, "ckanField": ckanField})
    print("compiled_template", compiled_template)
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
            num_paths_used_by_catalogue = get_num_paths(catalogue_uri, s)
            if num_paths_used_by_catalogue == 0:
                continue
            # Check if 's' is used by any other triples as an object
            uri_as_object_usage = get_uri_as_object_usage(s)
            print('uri_as_object_usage', uri_as_object_usage, num_paths_used_by_catalogue)
            if uri_as_object_usage == num_paths_used_by_catalogue:
                delete_clause.append(f'{normalize_uri(s)} ?p ?o')
                delete_clause.append(f'?s ?p {normalize_uri(s)}')
        
        # Remove all triples direcly linked to the catalogue
        delete_clause.append(f'{normalize_uri(catalogue_uri)} ?p ?o')

        return '\n'.join([f"PREFIX {prefix}: <{ns}>" for prefix, ns in prefixes.items()]) + '\n' \
            + '\n'.join([f"DELETE WHERE {{\n\t{triple}.\n}};" for triple in delete_clause])

    delete_query = generate_delete_sparql()
    print('delete_query')
    print(delete_query)

    client = get_client()
    client.execute_sparql(delete_query)


