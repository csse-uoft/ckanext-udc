from ckan.types import Context
import ckan.logic as logic
from ckan.types import Context


from typing import List, Dict, cast

import logging
from openai import OpenAI


from .cleaning import extract_name, extract_name_dict, extract_display_name, convert_non_str_nan
from .utils import gen_mapping, get_config, get_package

logger = logging.getLogger(__name__)


# Function to generate catalogue summary
def generate_catalogue_summary(row, column_to_ignore=None):
    formatted_text = ''
    for column, value in row.items():
        if column not in column_to_ignore:
            formatted_text += f"{column}: {value}\n"
    return formatted_text

# Function to generate field descriptions
def generate_field_desc(mapping, column_to_ignore=None):
    field_desc_map = ''
    for field in mapping:
        if field['display_name'] not in column_to_ignore:
            field_desc_map += f"{field['display_name']}: {field['short_description']}\n"
    return field_desc_map


# Function to get catalogue summary from OpenAI
def get_catalogue_summary_from_openai(row, mapping, config):
    client = OpenAI(
        api_key=config["openai_key"],
    )
    
    catalogue_summary = generate_catalogue_summary(row, column_to_ignore=['Organization', 'chatgpt_summary'])
    field_desc = generate_field_desc(mapping, column_to_ignore=['Organization'])
    prompt = (
        f"These are the descriptions of the fields: \"{field_desc}\" and these are the catalogue field values: "
        f"\"{catalogue_summary}\". Reset previous sessions, do not hallucinate, and create a two paragraph summary for "
        f"this catalogue's fields values, ensuring uniqueness and distinct meanings for each field. Do not summarize "
        f"the names of the fields available but describe their values. Skip the fields that have a value of \"Not provided\"."
    )
    model = 'gpt-4'
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=config["max_tokens"],
        temperature=config["temperature"],
    )
    print(res)
    return prompt, [choice.message.content for choice in res.choices]


def summary_generate(context: Context, package_id: str):
    config = get_config()
    
    # Get a single catalogue entry
    package = get_package(context, package_id)
    metadata = {**package}
   
    # Data cleaning and transformation
    metadata['resources'] = extract_name(metadata.get('resources', []))
    metadata['organization'] = extract_name_dict(metadata.get('organization', {}))
    metadata['tags'] = extract_display_name(metadata.get('tags', []))

    exclude_columns = ['resources', 'organization', 'tags']
    to_suppress_if_found = ['location', 'description_document', 'url']

    for key in metadata.keys():
        if key not in exclude_columns:
            if key in to_suppress_if_found:
                metadata[key] = convert_non_str_nan(metadata[key], nan_value="Not provided", if_found_value='Is provided')
            else:
                metadata[key] = convert_non_str_nan(metadata[key], nan_value="Not provided")

    # Mapping and renaming columns
   
    mapping = gen_mapping(config["maturity_model"])

    remapping = {
        'organization_and_visibility': 'organization',
        'source': 'url',
        'notes': 'description'
    }

    for field in mapping:
        if field['internal_name'] in metadata:
            metadata[field['display_name']] = metadata.pop(field['internal_name'])

    for old_key, new_key in remapping.items():
        if old_key in metadata:
            metadata[new_key] = metadata.pop(old_key)

    metadata = {key.replace('_', ' ').capitalize(): value for key, value in metadata.items()}

    try:
        prompt, results = get_catalogue_summary_from_openai(metadata, mapping, config)

        print(prompt)
        print(results)
        
        return {"prompt": prompt, "results": results}

    except Exception as e:
        raise logic.ActionError(f"\nError while generating summary using OpenAI. Exited with error: {str(e)}")
    
