import threading
from typing import Callable

# Default timeout for skill function execution (in seconds)
# Required unless you have a solution for the halting problem
DEFAULT_SKILL_TIMEOUT = 30


def run_with_timeout(func, timeout_seconds=DEFAULT_SKILL_TIMEOUT, *args, **kwargs):
    """
    Execute a function with a timeout. Returns the result or raises TimeoutError.

    Args:
        func: Function to execute
        timeout_seconds: Maximum execution time in seconds
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Function result

    Raises:
        TimeoutError: If function execution exceeds timeout
    """
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        # Thread is still running, function timed out
        raise TimeoutError(
            f"Skill function execution timed out after {timeout_seconds} seconds"
        )

    if exception[0]:
        raise exception[0]

    return result[0]


def skill_function(func: Callable) -> Callable:
    """Decorator that marks a function as a skill function."""
    func.is_skill_function = True
    return func


def sandbox_skill_function(func: Callable) -> Callable:
    """
    Decorator that marks a function as a skill function with automatic sandbox execution.

    Functions decorated with this will automatically execute their entire code
    in a secure sandbox environment instead of the host system.

    Example:
        @sandbox_skill_function
        def process_data(data):
            import pandas as pd
            df = pd.DataFrame(data)
            return df.describe().to_dict()
    """
    func.is_skill_function = True
    func.auto_sandbox = True
    return func
