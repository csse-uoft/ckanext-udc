"""
ArcGIS Hub API client utilities
"""
import requests
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


def get_site_scope_group_ids(base_api):
    """
    Get the group IDs that define the Hub site scope.
    
    This retrieves the group IDs from the catalog API which define what datasets
    belong to this specific Hub site (and not other organizations).
    
    :param base_api: The base URL of the ArcGIS Hub instance
    :return: List of group IDs that define the site scope
    """
    session = requests.Session()
    retries = Retry(
        total=10, 
        backoff_factor=1, 
        status_forcelist=[104, 502, 503, 504]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    
    url = f"{base_api}/api/search/v1/catalog"
    
    try:
        logger.info(f"Fetching site scope from catalog: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        catalog = response.json()
        
        # Extract group IDs from scopes.item.filters[].predicates[].group
        group_ids = []
        scopes = catalog.get('scopes', {})
        item_scope = scopes.get('item', {})
        filters = item_scope.get('filters', [])
        
        for filter_obj in filters:
            predicates = filter_obj.get('predicates', [])
            for predicate in predicates:
                groups = predicate.get('group', [])
                group_ids.extend(groups)
        
        # Remove duplicates while preserving order
        group_ids = list(dict.fromkeys(group_ids))
        
        logger.info(f"Found {len(group_ids)} group IDs defining site scope")
        return group_ids
        
    except requests.RequestException as e:
        logger.error(f"Failed to get site scope group IDs: {e}")
        logger.warning("Falling back to unfiltered dataset retrieval (may include other organizations)")
        return []


def get_all_datasets(base_api, page_size=100, max_results=None, cb=None):
    """
    Retrieve all datasets from an ArcGIS Hub API within the site scope.
    
    This correctly filters datasets using the site's group IDs to avoid
    fetching datasets from other organizations.
    
    :param base_api: The base URL of the ArcGIS Hub instance (e.g., "https://geohub.lio.gov.on.ca")
    :param page_size: Number of results per page (default: 100)
    :param max_results: Maximum number of datasets to retrieve (None for all)
    :param cb: Callback function for progress updates
    :return: A list of all datasets within the site scope
    """
    session = requests.Session()
    retries = Retry(
        total=10, 
        backoff_factor=1, 
        status_forcelist=[104, 502, 503, 504]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    
    # First, get the site scope group IDs
    group_ids = get_site_scope_group_ids(base_api)
    
    datasets = []
    page_number = 1
    
    # Build filter parameter for group IDs
    filter_param = None
    if group_ids:
        # Use filter[groupIds]=any(id1,id2,id3,...) to filter by site scope
        group_ids_str = ','.join(group_ids)
        filter_param = f"any({group_ids_str})"
        logger.info(f"Filtering datasets by {len(group_ids)} group IDs (site scope)")
    
    while True:
        # Construct the API request URL
        url = f"{base_api}/api/v3/datasets"
        params = {
            'page[size]': page_size,
            'page[number]': page_number
        }
        
        # Add group ID filter if available
        if filter_param:
            params['filter[groupIds]'] = filter_param
        
        logger.info(f"Fetching datasets page {page_number}, size={page_size}")
        if cb:
            cb(f"Fetching datasets: page {page_number} (total so far: {len(datasets)})")
        
        try:
            # Make the API request
            response = session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Log total count if available
            total_count = data.get('meta', {}).get('stats', {}).get('totalCount') or data.get('meta', {}).get('total')
            if total_count and page_number == 1:
                logger.info(f"Total datasets in site scope: {total_count}")
                if cb:
                    cb(f"Total datasets in site scope: {total_count}")
            
            # Extract the results
            result_datasets = data.get('data', [])
            
            if not result_datasets:
                break  # Stop if no more datasets are returned
            
            datasets.extend(result_datasets)
            
            # Check if we've reached the maximum
            if max_results and len(datasets) >= max_results:
                datasets = datasets[:max_results]
                break
            
            # Check if there's a next page (recommended way)
            next_link = data.get('links', {}).get('next')
            if not next_link:
                break
            
            # Follow the next link (already has all parameters encoded)
            # Use urljoin to handle both absolute and relative URLs
            url = urljoin(base_api, next_link)
            page_number += 1
            # Clear params since next_link already contains them
            params = {}
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            break
    
    logger.info(f"Retrieved {len(datasets)} datasets total from site scope")
    return datasets


def get_dataset(dataset_id, base_api):
    """
    Get a single dataset by ID from ArcGIS Hub API.
    
    :param dataset_id: The dataset ID
    :param base_api: The base URL of the ArcGIS Hub instance
    :return: Dataset details
    """
    session = requests.Session()
    retries = Retry(
        total=10, 
        backoff_factor=1, 
        status_forcelist=[104, 502, 503, 504]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    
    url = f"{base_api}/api/v3/datasets/{dataset_id}"
    
    try:
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('data')
    except requests.RequestException as e:
        logger.error(f"Failed to get dataset {dataset_id}: {e}")
        raise ValueError(f"Cannot find dataset with id={dataset_id}")


def check_site_alive(base_api):
    """
    Check if an ArcGIS Hub site is accessible.
    
    :param base_api: The base URL of the ArcGIS Hub instance
    :return: True if accessible, False otherwise
    """
    try:
        # Check catalog endpoint first (more reliable)
        response = requests.get(f"{base_api}/api/search/v1/catalog", timeout=10)
        if response.status_code == 200:
            return True
        # Fallback to datasets endpoint
        response = requests.get(f"{base_api}/api/v3/datasets?page[size]=1", timeout=10)
        return response.status_code == 200
    except:
        return False
