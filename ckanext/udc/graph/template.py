import sys
import re
from pyld import jsonld
from copy import deepcopy
from .mapping_helpers import generate_uuid
from .contants import EMPTY_FIELD


def is_all_attrs_starts_with_at(data: dict):
    for k in data:
        if not k.startswith('@'):
            return False
    return True

def filter_out_empty_values(data_list: list):
    def is_not_empty(data_dict: dict):
        if len(data_dict) == 1 and data_dict.get("@id"):
            return True
        elif len(data_dict) == 0:
            return False
        elif is_all_attrs_starts_with_at(data_dict) and not data_dict.get("@value"):
            return False
        return True
    
    return list(filter(is_not_empty, data_list))


def compile_template(template, global_vars, local_vars, nested=False):
    """
    Parse the mapping config into json-ld data.
    Empty fields are removed.
    """
    result = deepcopy(template)
    if not isinstance(result, list):
        result = [result]

    for idx, item in enumerate(result):
        if isinstance(item, str):
            val = eval(f'f"{item}"', global_vars, local_vars)
            if val == '' or val is None:
                result[idx] = EMPTY_FIELD
            else:
                result[idx] = val

        else:
            attrs_to_del = []
            for attr in item:
                if not isinstance(item[attr], str):
                    item[attr] = filter_out_empty_values(compile_template(
                        item[attr], global_vars, local_vars, nested=True))
                    
                    if len(item[attr]) == 0 or (len(item[attr]) == 1 and len(item[attr][0]) == 0):
                        attrs_to_del.append(attr)
                    
                else:
                    try:
                        should_eval = item[attr].startswith('eval(') and item[attr].endswith(')')
                        if should_eval:
                            # eval() syntax
                            val = eval(item[attr][5:-1], global_vars, local_vars)
                           
                            # Remove [{ "@value": '....' }] wrapping
                            if len(result) == 1 and len(item) == 1 and attr == '@value':
                                if val is None or isinstance(val, str) and len(val) == 0:
                                    return []
                                return val
                            
                        else:
                            # Literals
                            val = eval(f'f"{item[attr]}"', global_vars, local_vars)
                        if val == '' or val is None:
                            item[attr] = EMPTY_FIELD
                        else:
                            item[attr] = val

                        if EMPTY_FIELD in item[attr]:
                            attrs_to_del.append(attr)
                    except Exception as e:
                        if not "is not defined" in str(e):
                            print(f'Unable to evaluate: {item[attr]}; {str(e)}', file=sys.stderr)
                        attrs_to_del.append(attr)
            for attr in attrs_to_del:
                del item[attr]

    result = list(filter(lambda x: x != EMPTY_FIELD, filter_out_empty_values(result)))

    if not nested and len(result) == 1:
        return result[0]
    else:
        return result


def compile_with_temp_value(mappings, global_vars, local_vars, nested=False):
    """
    Parse the mapping config into json-ld data.
    Empty fields are preserved and filled with some string "TEMP_VALUE" or EMPTY_FIELD.
    """
    result = deepcopy(mappings)
    if not isinstance(result, list):
        result = [result]
    for idx, item in enumerate(result):
        if not isinstance(item, str):
            for attr in item:
                if not isinstance(item[attr], str):
                    item[attr] = compile_with_temp_value(item[attr], global_vars, local_vars)
                else:
                    try:
                        item[attr] = eval(f'f"{item[attr]}"', global_vars, local_vars)
                    except:
                        item[attr] = re.sub(r"\{.*}", "TEMP_VALUE", item[attr], flags=re.M)

    # Make sure the result is a dict
    if not nested and len(result) == 1:
        return result[0]
    else:
        return result
