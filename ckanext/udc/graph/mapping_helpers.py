# This file contains the helper functions/variables that are available to the UDC mapping config.

import uuid
from datetime import datetime
from rdflib import Literal, XSD

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
    return Literal(val + "", datatype=XSD.date)

def to_bool(val: str):
    if val.lower() == 'yes':
        return "true"
    elif val.lower() == 'no':
        return "false"


# def to_datetime(val: str):
#     return Literal(val, datatype=XSD.datetTime)



all_helpers = {
    "generate_uuid": generate_uuid,
    "to_integer": to_integer,
    "to_float": to_float,
    "to_date": to_date,
    "to_bool": to_bool
}
