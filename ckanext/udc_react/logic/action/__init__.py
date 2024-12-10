import inspect


def get_functions(module):
    return {name: func for name, func in inspect.getmembers(module, inspect.isfunction)}


# Make imported as dict
def get_actions():
    # Read all functions from base.py and organization_access_request.py
    import ckanext.udc_react.logic.action.base as base
    import ckanext.udc_react.logic.action.organization_access_request as org_access

    base_functions = get_functions(base)
    org_access_functions = get_functions(org_access)

    return {**base_functions, **org_access_functions}
