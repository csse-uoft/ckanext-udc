import requests
from requests.adapters import HTTPAdapter, Retry

def get_package_ids(base_api):
    res = requests.get(f"{base_api}/3/action/package_list").json()
    return res["result"]


def get_package(package_id, base_api, api_key=None):
    session = requests.Session()
    retries = Retry(total=10, backoff_factor=1, status_forcelist=[ 104, 502, 503, 504 ])
    headers = None
    if api_key:
        headers = {"Authorization": api_key}
    try:
        session.mount('https://', HTTPAdapter(max_retries=retries))
        res = session.get(
            f"{base_api}/3/action/package_show?id={package_id}", headers=headers
        ).json()
    except:
        raise ValueError(f"Cannot find package with id={package_id}")
    if res.get("error"):
        raise ValueError(f"{res['error'].get('__type')}: {res['error'].get('message')}")
    return res["result"]


def get_all_packages(base_api, size=None, api_key=None, cb=None):
    """
    Retrieve all packages from the CKAN API using the package_search endpoint.
    
    :param base_url: The base URL of the CKAN instance (e.g., "https://demo.ckan.org")
    :param api_key: Optional API key for authorization, if required
    :return: A list of all packages
    """
    session = requests.Session()
    retries = Retry(total=10, backoff_factor=1, status_forcelist=[ 104, 502, 503, 504 ])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    packages = []
    rows = 500
    offset = 0
    headers = {'Authorization': api_key} if api_key else {}

    while True:
        # Construct the API request URL
        url = f"{base_api}/3/action/package_search?rows={rows}&start={offset}"
        print(f"getting package rows={rows} offset={offset}")
        if cb:
            cb(f"Got {offset} packages")
        
        try:
            # Make the API request
            response = session.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data['success']:
                raise Exception(f"API request failed: {data['error']}")

            # Extract the results
            result_packages = data['result']['results']
            if not result_packages:
                break  # Stop if no more packages are returned

            packages.extend(result_packages)
            offset += rows  # Increase the offset for the next request
            
            if size and len(packages) >= size:
                break
            
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            break

    return packages


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


def check_site_alive(base_api):
    try:
        res = requests.get(f"{base_api}/3/action/site_read").json()
        return res["result"]
    except:
        return False

def get_organization(base_api, organization_id=None):
    res = requests.get(f"{base_api}/3/action/organization_show?id={organization_id}").json()
    return res["result"]

def get_organization_ids(base_api):
    res = requests.get(f"{base_api}/3/action/organization_list").json()
    return res["result"]

def get_organizations(base_api):
    """
    Example response:
    [
        {
            "approval_status": "approved",
            "created": "2018-07-27T18:51:10.451359",
            "description": "",
            "display_name": "Argentia Private Investments Inc. | Argentia Private Investments Inc.",
            "id": "76287b5c-ceb0-44fb-a62f-3cd4ee5de656",
            "image_display_url": "",
            "image_url": "",
            "is_organization": true,
            "name": "api",
            "num_followers": 0,
            "package_count": 0,
            "state": "active",
            "title": "Argentia Private Investments Inc. | Argentia Private Investments Inc.",
            "type": "organization"
        },
    ]
    """
    res = requests.get(f"{base_api}/3/action/organization_list?all_fields=true&limit=1000").json()
    return res["result"]
