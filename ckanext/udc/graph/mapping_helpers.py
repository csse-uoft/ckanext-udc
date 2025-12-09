# This file contains the helper functions/variables that are available to the UDC mapping config.

import uuid
import urllib
import urllib.parse
from datetime import datetime
from rdflib import Literal, XSD
from .contants import EMPTY_FIELD
import ckan.model as model
from ckanext.udc.solr.config import get_default_lang

uuidMap = {}
licenseMap = {}


def generate_uuid(key=None):
    """
    Return a random UUID.
    Calling this function with the same key will give you the same UUID.
    """
    if key is None:
        return str(uuid.uuid4())
    elif key in uuidMap:
        return uuidMap[key]
    else:
        newUUID = str(uuid.uuid4())
        uuidMap[key] = newUUID
        return newUUID


def to_integer(val: str):
    return int(val)


def to_float(val: str):
    return float(val)


def to_date(val: str):
    if val == EMPTY_FIELD or val == '':
        return EMPTY_FIELD
    converted_xsd_date = Literal(val + "", datatype=XSD.date)
    if converted_xsd_date:
        return converted_xsd_date
    else:
        return EMPTY_FIELD

def to_bool(val: str):
    if val.lower() == 'yes':
        return "true"
    elif val.lower() == 'no':
        return "false"
    
def mapFromCKANLicense(val: str):
    # val counld be license_id or license_url
    register = model.Package.get_license_register()
    if len(licenseMap) == 0:
        for license_id, license in register.items():
            licenseMap[license_id] = license.url
    if licenseMap.get(val):
        return [{"@id": licenseMap[val]}]
    elif (val.startswith("http")):
        return [{"@id": val}]
    else:
        # CKAN license that does not have url
        return [{"@id": f"http://data.urbandatacentre.ca/licenses/{val}"}]
        


# def to_datetime(val: str):
#     return Literal(val, datatype=XSD.datetTime)


def split_to_uris(val: str, separator=","):
    return [{"@id": uri} for uri in val.split(separator)]


def quote_url(url: str):
    """Encode URL but not encode the prefix http(s):// and preserve query string characters"""
    vals = []
    for item in url.strip().split("://"):
        # Preserve / ? & = in the query string
        vals.append(urllib.parse.quote(item, safe="/?&="))
    return "://".join(vals)


def mapFromCKANTags(tags_str: str):
    tags = []
    
    for tag in tags_str.split(","):
        tags.append({
            "@value": tag.strip()
        })
        
    return tags

def map_from_tags_multiple_languages(tags_dict: dict):
    # For tags_translated field: {lang: [tag, ...], ...} -> json-ld array
    tags = []
    
    for lang, tags_list in tags_dict.items():
        for tag in tags_list:
            tags.append({
                "@language": lang,
                "@value": tag.strip()
            })
        
    return tags

def map_to_multiple_languages(val):
    """Map a string or langs dict to a json-ld array. For custom fields"""
    if isinstance(val, dict):
        # If it's already a dict, convert it to the json-ld array format
        return [{"@language": lang, "@value": value} for lang, value in val.items()]
    elif isinstance(val, str):
        # If it's a string, use the default language
        default_lang = get_default_lang()
        return [{"@language": default_lang, "@value": val}]
    return []

def map_to_single_language(val, lang='en'):
    """Map a string or langs dict to a single string. For custom fields"""
    if isinstance(val, dict):
        # If it's already a dict, get the value for the specified language
        if lang and lang in val:
            return val[lang]
        else:
            # Return the value for the default language
            default_lang = get_default_lang()
            return val.get(default_lang, "")
    elif isinstance(val, str):
        # If it's a string, return it as is
        return val
    return ""

def map_to_multiple_datasets(datasets: list[str]):
    """Map a list of dataset urls to json-ld array for dct:Dataset"""
    result = []
    for ds in datasets:
        ds_id = ds.get("id")
        if ds_id:
            result.append({
                "@id": ds_id,
                "dcat:landingPage": ds_id,
                "dcat:accessURL": ds_id,
                "@type": "dcat:Dataset"
            })
    return result

def map_version_dataset_to_rdf(version_dataset: dict):
    """Map a single version_dataset dict to RDF Dataset reference"""
    if not version_dataset or not isinstance(version_dataset, dict):
        return []
    
    url = version_dataset.get("url", "")
    title = version_dataset.get("title", "")
    description = version_dataset.get("description", "")
    
    if not url:
        return []
    
    result = {
        "@id": url,
        "@type": "dcat:Dataset"
    }
    
    if title:
        result["http://purl.org/dc/terms/title"] = title
    if description:
        result["http://purl.org/dc/terms/description"] = description
    
    return [result]

def map_dataset_versions_to_rdf(dataset_versions: list):
    """Map a list of dataset version dicts to RDF Dataset references"""
    if not dataset_versions or not isinstance(dataset_versions, list):
        return []
    
    result = []
    for ds in dataset_versions:
        if not isinstance(ds, dict):
            continue
            
        url = ds.get("url", "")
        title = ds.get("title", "")
        description = ds.get("description", "")
        
        if not url:
            continue
        
        ds_ref = {
            "@id": url,
            "@type": "dcat:Dataset"
        }
        
        if title:
            ds_ref["http://purl.org/dc/terms/title"] = title
        if description:
            ds_ref["http://purl.org/dc/terms/description"] = description
        
        result.append(ds_ref)
    
    return result

all_helpers = {
    "generate_uuid": generate_uuid,
    "to_integer": to_integer,
    "to_float": to_float,
    "to_date": to_date,
    "to_bool": to_bool,
    "split_to_uris": split_to_uris,
    "mapFromCKANLicense": mapFromCKANLicense,
    "mapFromCKANTags": mapFromCKANTags,
    "quote_url": quote_url,
    "map_to_multiple_languages": map_to_multiple_languages,
    "map_to_single_language": map_to_single_language,
    "map_to_multiple_datasets": map_to_multiple_datasets,
    "map_from_tags_multiple_languages": map_from_tags_multiple_languages,
    "map_version_dataset_to_rdf": map_version_dataset_to_rdf,
    "map_dataset_versions_to_rdf": map_dataset_versions_to_rdf
}
