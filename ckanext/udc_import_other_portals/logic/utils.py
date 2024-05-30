import functools
import contextlib

# https://stackoverflow.com/a/57124418/5531152
def with_exit_stack(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with contextlib.ExitStack() as stack:
            return func(*args, **kwargs, stack=stack)

    return wrapper