from __future__ import annotations

import cProfile
import pstats
import io
import time
from functools import wraps
from typing import Any


def profile_func(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()

        result = func(*args, **kwargs)

        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
        ps.print_stats(50)  # Top 500 slowest

        print(s.getvalue())  # Or write to file
        return result

    return wrapper


def cache_for(seconds, key_func=None):
    """Cache function results for ``seconds`` based on an optional key."""

    def decorator(func):
        cached: dict[Any, dict[str, Any]] = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                if not args and not kwargs:
                    cache_key = "__default__"
                else:
                    cache_key = repr((args, sorted(kwargs.items())))

            if cache_key is None:
                cache_key = "__default__"

            now = time.time()
            entry = cached.get(cache_key)
            if not entry or now - entry["time"] > seconds:
                cached[cache_key] = {"time": now, "result": func(*args, **kwargs)}
            return cached[cache_key]["result"]

        return wrapper

    return decorator
