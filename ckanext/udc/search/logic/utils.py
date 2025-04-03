import cProfile
import pstats
import io
import time
from functools import wraps, lru_cache


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


def cache_for(seconds):
    def decorator(func):
        last_run = {"time": 0}
        cached = {"result": None}

        @wraps(func)
        def wrapper():
            now = time.time()
            if cached["result"] is None or now - last_run["time"] > seconds:
                cached["result"] = func()
                last_run["time"] = now
            return cached["result"]

        return wrapper

    return decorator
