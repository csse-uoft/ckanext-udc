# This file contains the helper functions/variables that are available to the UDC mapping config.

import uuid
import urllib
import urllib.parse
from datetime import datetime
from rdflib import Literal, XSD
from .contants import EMPTY_FIELD
import ckan.model as model

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
    """Encode URL but not encode the prefix http(s):// """
    vals = []
    for item in url.strip().split("://"):
        vals.append(urllib.parse.quote(item, safe="/"))
    return "://".join(vals)


def mapFromCKANTags(tags_str: str):
    tags = []
    
    for tag in tags_str.split(","):
        tags.append({
            "@value": tag.strip()
        })
        
    return tags


all_helpers = {
    "generate_uuid": generate_uuid,
    "to_integer": to_integer,
    "to_float": to_float,
    "to_date": to_date,
    "to_bool": to_bool,
    "split_to_uris": split_to_uris,
    "mapFromCKANLicense": mapFromCKANLicense,
    "mapFromCKANTags": mapFromCKANTags,
    "quote_url": quote_url
}
