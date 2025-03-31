import ckan.authz as authz
from ckan.types import Context
import ckan.logic as logic
from ckan.types import Context


from typing import List, Dict, cast

import logging
from openai import OpenAI


from .cleaning import (
    extract_display_name,
    convert_non_str_nan,
    covert_datetime,
)
from .utils import gen_mapping, get_config, get_package

logger = logging.getLogger(__name__)


default_prompt = (
    f'Reset previous sessions, do not hallucinate, and create a two paragraph summary for '
    f"this catalogue's fields values, ensuring uniqueness and distinct meanings for each field. Do not summarize "
    f'the names of the fields available but describe their values.'
)

default_config = {
    "openai_key": "",
    "openai_model": "gpt-4",
    "max_tokens": 500,
    "temperature": 0.0,
    "use_custom_prompt": False,
    "custom_prompt": default_prompt,
    "use_markdown": False,
}


# Function to generate catalogue summary
def generate_catalogue_summary(row, mapping, column_to_ignore=None):
    formatted_text = ""
    field_desc_text = ""
    for column, value in row.items():
        # if column not in mapping:
            # print(f"Column {column} not found in mapping")
        
        if (column not in column_to_ignore) and (column in mapping):
            
            # print(column, value)
            # print(mapping[column]['display_name'], mapping[column]['short_description'])
            formatted_text += f"{column}: {value}\n"
            field_desc_text += f"{mapping[column]['display_name']}: {mapping[column]['short_description']}\n"
    return formatted_text, field_desc_text


# Function to get catalogue summary from OpenAI
def get_catalogue_summary_from_openai(row, mapping, config):
    client = OpenAI(
        api_key=config["openai_key"],
    )
    
    catalogue_summary, field_desc_text = generate_catalogue_summary(
        row, mapping, column_to_ignore=["summary"]
    )
    
    prompt = (
        f'These are the descriptions of the fields: \n```{field_desc_text}```\n And these are the catalogue field values:\n```'
        f'{catalogue_summary}```\n'
    )

    if config.get("use_custom_prompt") and config.get("custom_prompt"):
        prompt += config.get("custom_prompt")
    else:
        prompt += default_prompt
        
        if config.get("use_markdown"):
            prompt += " Markdown is supported and preferred. Please use links and lists where appropriate."
   
        
    res = client.chat.completions.create(
        model=config["openai_model"],
        messages=[{"role": "system", "content": prompt}],
        max_tokens=config["max_tokens"],
        temperature=config["temperature"],
    )
    print(res)
    
    return prompt, [choice.message.content for choice in res.choices]


def summary_generate(context: Context, package_id: str):
    # Check admin
    if not authz.is_sysadmin(context.get('user')):
        raise logic.NotAuthorized("You are not authorized to view this page")
    
    config = get_config()

    # Get a single catalogue entry
    package = get_package(context, package_id)

    properties_to_ignore = [
        
        "cudc_import_config_id", # udc-import-other-portals internal field
        "related_packages", # udc-import-other-portals internal field
        "relationships_as_object", # udc-import-other-portals internal field
        "relationships_as_subject", # udc-import-other-portals internal field
        
        "isopen", # CKAN field, Not used
        "private", # Private dataset
        "maintainer_email", # CKAN field, Not used in the maturity model
        "license_id", # We only care about the license title and url
        "num_resources", # doesn't matter
        "num_tags", # doesn't matter
        "state", # CKAN field, Not used in the maturity model, used for the state of the dataset (active, deleted, etc.)
        "type", # (catalogue) CKAN field, Not used in the maturity model, used for the type of the dataset (dataset, catalogue, etc.)
        "id", # not interested in the package id
        "name", # not interested in the package name
        "summary", # Previous summary
        
    ]
    metadata = {}
    for key in package:
        if key in properties_to_ignore:
            continue
        if (
            package[key] is None
            or package[key] == ""
            or (type(package[key]) == list and len(package[key]) == 0)
        ):
            continue
        metadata[key] = package[key]

    # Data cleaning and transformation

    # Get all resources names
    resources_name = []
    for resource in metadata.get("resources", []):
        if resource.get("name"):
            resources_name.append(resource.get("name"))
    metadata["resources"] = repr(resources_name)

    # Get organization name
    metadata["organization"] = metadata.get("organization", {}).get("title")
    del metadata["owner_org"]
    
    metadata["tags"] = extract_display_name(metadata.get("tags", []))

    # License
    metadata["license"] = metadata.get("license_title", "")
    if "license_title" in metadata:
        del metadata["license_title"]
    if metadata.get("license_url"):
        metadata["license"] += f" ({metadata['license_url']})"
        del metadata["license_url"]
        
    # Convert datetime to date
    metadata["metadata_created"] = covert_datetime(metadata.get("metadata_created"))
    metadata["metadata_modified"] = covert_datetime(metadata.get("metadata_modified"))
    
    to_suppress_if_found = ["location", "description_document", "url"]
    for key in metadata.keys():
        if key in to_suppress_if_found:
            metadata[key] = convert_non_str_nan(
                metadata[key],
                nan_value="Not provided",
                if_found_value="Is provided",
            )


    # Maturity Model Mapping and Renamings
    mapping = gen_mapping(config["maturity_model"])

    # Additional description for the ckan fields
    mapping["Organization"] = {
        "internal_name": "organization",
        "display_name": "Organization",
        "short_description": "The dataset's owning organization in CUDC",
    }
    
    # CKAN uses `notes` for the description field
    mapping["Description"] = {
        "internal_name": "notes",
        "display_name": "Description",
        "short_description": mapping.get("description", {}).get("short_description", "The description of the dataset."),
    }
    
    # CKAN uses `url` for the source field
    mapping["Source"] = {
        "internal_name": "url",
        "display_name": "Source",
        "short_description": mapping.get("source", {}).get("short_description", "The source of the dataset."),
    }
    
    # License
    mapping["License"] = {
        "internal_name": "license",
        "display_name": "License",
        "short_description": mapping.get("license_id", {}).get("short_description", "License used to access the dataset."),
    }
    if "license_id" in mapping:
        del mapping["license_id"]
    
    # Resources
    mapping["Resources"] = {
        "internal_name": "resources",
        "display_name": "Resources",
        "short_description": "The resources available in the dataset. (In Python repr() format)",
    }
    
    # Metadata created/modified
    mapping["Metadata Created"] = {
        "internal_name": "metadata_created",
        "display_name": "Metadata Created",
        "short_description": "The date and time the metadata was created.",
    }
    mapping["Metadata Modified"] = {
        "internal_name": "metadata_modified",
        "display_name": "Metadata Modified",
        "short_description": "The date and time the metadata was last modified.",
    }

    for field in mapping.values():
        if field["internal_name"] in metadata:
            metadata[field["display_name"]] = metadata.pop(field["internal_name"])

    try:
        prompt, results = get_catalogue_summary_from_openai(metadata, mapping, config)

        return {"prompt": prompt, "results": results}
        # return {"prompt": "", "results": []}

    except Exception as e:
        raise logic.ActionError(
            f"\nError while generating summary using OpenAI. Exited with error: {str(e)}"
        )

def update_summary(context: Context, data: dict):
    # Check admin
    if not authz.is_sysadmin(context.get('user')):
        raise logic.NotAuthorized("You are not authorized to view this page")
    
    package_id = data.get("package_id")
    summary = data.get("summary")
    
    if not package_id:
        raise logic.ValidationError("package_id is required")
    if not summary:
        raise logic.ValidationError("summary is required")
    
    package = get_package(context, package_id)
    
    if not package:
        raise logic.ValidationError("Package not found")
    
    package["summary"] = summary
    
    logic.check_access("package_update", context, data_dict=package)
    # print(action, existing_package)

    logic.get_action("package_update")(context, package)
    
    return {"package_id": package_id, "summary": summary}


@logic.side_effect_free
def default_ai_summary_config(context: Context, data: dict):
    # Check admin
    if not authz.is_sysadmin(context.get('user')):
        raise logic.NotAuthorized("You are not authorized to view this page")
    
    return default_config
