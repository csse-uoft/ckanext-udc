# This file contains the helper functions/variables that are available to the UDC mapping config.

import uuid
from datetime import datetime
from rdflib import Literal, XSD
from .contants import EMPTY_FIELD

uuidMap = {}


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


# def to_datetime(val: str):
#     return Literal(val, datatype=XSD.datetTime)


def split_to_uris(val: str, separator=","):
    return [{"@id": uri} for uri in val.split(separator)]


all_helpers = {
    "generate_uuid": generate_uuid,
    "to_integer": to_integer,
    "to_float": to_float,
    "to_date": to_date,
    "to_bool": to_bool,
    "split_to_uris": split_to_uris,
}
