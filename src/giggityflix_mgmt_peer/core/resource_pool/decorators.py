"""Decorators for resource management."""
import asyncio
import functools
import inspect
import os
import threading
from typing import Callable, TypeVar, cast

from giggityflix_mgmt_peer.core.resource_pool.manager import get_resource_pool_manager

# Thread local storage for tracking recursion
_local = threading.local()
T = TypeVar('T')


def io_bound(param_name: str = 'filepath'):
    """
    Decorator for IO-bound operations.
    
    Limits concurrent IO operations to a specific drive using semaphores.
    
    Args:
        param_name: Name of the parameter containing the file path
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get function signature
        sig = inspect.signature(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get path from arguments
            path = None
            bound_args = sig.bind(*args, **kwargs)

            if param_name in bound_args.arguments:
                path = bound_args.arguments[param_name]

            if not path:
                # No path parameter, execute normally
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            # Get semaphore for the drive
            semaphore = get_resource_pool_manager().get_drive_semaphore(path)

            # Execute with semaphore
            async with semaphore:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get path from arguments
            path = None
            bound_args = sig.bind(*args, **kwargs)

            if param_name in bound_args.arguments:
                path = bound_args.arguments[param_name]

            if not path:
                # No path parameter, execute normally
                return func(*args, **kwargs)

            # For synchronous functions, we need to get a different kind of semaphore
            # since asyncio semaphores won't work
            # This is a simplified approach that throttles at process level

            # Use sleep as a crude rate limiter based on drive ID
            drive_id = get_resource_pool_manager()._get_drive_id_for_path(path)
            limit = int(os.environ.get(f'PEER_DRIVE_{drive_id}_IO', get_resource_pool_manager().default_io_limit))

            # Use thread pool to limit concurrent operations
            thread_pool = get_resource_pool_manager().get_thread_pool()
            return thread_pool.submit(func, *args, **kwargs).result()

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        return cast(Callable[..., T], sync_wrapper)

    return decorator


def cpu_bound():
    """
    Decorator for CPU-bound operations.
    
    Executes operations in a process pool to prevent CPU saturation.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Setup thread-local state
        if not hasattr(_local, 'in_cpu_bound'):
            _local.in_cpu_bound = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get the function's qualified name to use as key
            func_key = f"{func.__module__}.{func.__qualname__}"

            # Check if we're already running in the process pool
            if _local.in_cpu_bound.get(func_key, False):
                # Already in process pool, execute directly to avoid deadlocks
                return func(*args, **kwargs)

            # Get process pool
            process_pool = get_resource_pool_manager().get_process_pool()

            # Mark function as running in process pool
            _local.in_cpu_bound[func_key] = True

            try:
                # Execute in process pool
                return process_pool.submit(_cpu_bound_helper, func, args, kwargs).result()
            finally:
                # Reset state
                _local.in_cpu_bound[func_key] = False

        return cast(Callable[..., T], wrapper)

    return decorator


def _cpu_bound_helper(func, args, kwargs):
    """Helper function to execute CPU-bound operations in a process pool."""
    return func(*args, **kwargs)
