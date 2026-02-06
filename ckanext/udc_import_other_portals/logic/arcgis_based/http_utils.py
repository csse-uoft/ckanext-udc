import logging

import requests

logger = logging.getLogger(__name__)

_DNS_ERROR_HINTS = (
    "Name or service not known",
    "Temporary failure in name resolution",
    "nodename nor servname provided",
    "No address associated with hostname",
    "getaddrinfo failed",
)


def _is_dns_error(error: Exception) -> bool:
    return any(hint in str(error) for hint in _DNS_ERROR_HINTS)


def get_with_fast_fail(get_fn, url: str, **kwargs):
    try:
        return get_fn(url, **kwargs)
    except requests.exceptions.ConnectionError as e:
        if _is_dns_error(e):
            logger.error(f"DNS resolution failed for {url}: {e}")
            raise ValueError(f"DNS resolution failed for {url}: {e}")
        raise
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL error for {url}: {e}")
        raise ValueError(f"SSL error for {url}: {e}")
