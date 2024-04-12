from graphdb_importer import import_and_wait, set_config
import ckan.plugins.toolkit as tk
import ckan.plugins as plugins
import requests
import os
from .sparql_client import SparqlClient


def preload_ontologies(config, graphdb_endpoint: str, username: str, password: str, sparql_client: SparqlClient):
    # Download and import ontologies
    storage_path = tk.config.get('ckan.storage_path') or './'
    download_path = os.path.join(storage_path, 'preload_ontologies')
    os.makedirs(download_path, exist_ok=True)

    base_api, repo = graphdb_endpoint.split('/repositories/')
    set_config(base_api=base_api, repo=repo, username=username, password=password)

    for item in config["preload_ontologies"]:
        filename = item["ontology_url"].rsplit('/', 1)[1]
        path = os.path.join(download_path, filename)
        r = requests.get(item["ontology_url"], allow_redirects=True)
        with open(path, 'wb') as f:
            f.write(r.content)
        try:
            import_and_wait(path, replace_graph=True, named_graph=item["graph"])
        except Exception as e:
            if 'already scheduled for import' not in str(e):
                raise e

    # Preload options for dropdowns
    dropdown_reload(maturity_model=config["maturity_model"])


def dropdown_reload(name=None, maturity_model=None):
    """
    Reload dropdown options "optionsFromQuery".
    Set `name` to None to reload all dropdown options.
    """
    if plugins.get_plugin('udc').disable_graphdb:
        return
    
    client = plugins.get_plugin('udc').sparql_client
    
    if maturity_model is None:
        maturity_model = plugins.get_plugin('udc').maturity_model
    
    for level in maturity_model:
        for field in level["fields"]:
            if name is not None and field.get("name") != name:
                continue
            if field.get("optionsFromQuery"):
                options = []
                if field["type"] == "single_select":
                    options.append({
                        "text": "Please select",
                        "value": ""
                    })
                textVar = field["optionsFromQuery"]["text"]
                valueVar = field["optionsFromQuery"]["value"]
                result = client.execute_sparql(field["optionsFromQuery"]["query"])
                for item in result["results"]["bindings"]:
                    options.append({
                        "text": item[textVar]["value"],
                        "value": item[valueVar]["value"],
                    })
                field["options"] = options
                