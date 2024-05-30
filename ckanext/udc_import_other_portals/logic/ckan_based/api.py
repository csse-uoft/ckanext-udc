import requests


def get_package_ids(base_api):
    res = requests.get(f"{base_api}/3/action/package_list").json()
    return res["result"]


def get_package(package_id, base_api, api_key=None):
    headers = None
    if api_key:
        headers = {"Authorization": api_key}
    try:
        res = requests.get(
            f"{base_api}/3/action/package_show?id={package_id}", headers=headers
        ).json()
    except:
        raise ValueError(f"Cannot find package from UDC with id={package_id}")
    if res.get("error"):
        raise ValueError(f"{res['error'].get('__type')}: {res['error'].get('message')}")
    return res["result"]


def package_delete(package_id, base_api, api_key):
    headers = {"Authorization": api_key}
    try:
        res = requests.post(
            f"{base_api}/3/action/package_delete?id={package_id}", headers=headers
        ).json()
    except:
        raise ValueError(f"Cannot find package from UDC with id={package_id}")
    if res.get("error"):
        raise ValueError(f"{res['error'].get('__type')}: {res['error'].get('message')}")


def import_package(package: dict, base_api, api_key, merge: bool = False):
    """
    :param merge: Merge with the existing package
    """
    headers = {"Authorization": api_key}
    existing_package = {}
    action = "package_create"
    id_or_name = package["id"] or package["name"]
    try:
        existing_package = get_package(package["id"], base_api=base_api)
        # If there is an existing package, we should call 'package_update'
        action = "package_update"
    except:
        pass
    if len(existing_package.keys()) == 0:
        try:
            existing_package = get_package(package["name"], base_api=base_api)
            package_delete(existing_package["id"], base_api=base_api)
        except:
            pass

    if merge:
        existing_package.update(package)
    else:
        existing_package = package

    res = requests.post(
        f"{base_api}/3/action/{action}", headers=headers, json=existing_package
    ).json()

    if isinstance(res, str):
        raise ValueError(f"Failed to import: {package['name']} {res}")

    if not res["success"]:
        # print(existing_package)
        raise ValueError(f"Failed to import: {package['name']} {res['error']}")


def check_existing_package_id_or_name(id_or_name: str, base_api):
    try:
        get_package(id_or_name, base_api=base_api)
        return True
    except:
        pass
    return False
