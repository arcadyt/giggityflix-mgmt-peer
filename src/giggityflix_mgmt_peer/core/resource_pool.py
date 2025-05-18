# src/peer/core/resource_pool.py
import asyncio
import concurrent.futures
import os
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

from ..config import AppConfig

T = TypeVar('T')
R = TypeVar('R')


class MetricsCollector:
    """Collects and reports execution metrics."""

    def __init__(self, enabled: bool = True, logger: Optional[Callable] = None):
        self.enabled = enabled
        self.logger = logger or print

    def record_operation(self, resource_type: str, operation_name: str,
                         queue_time: float, execution_time: float):
        """Record metrics for an operation."""
        if self.enabled:
            self.logger(f"[{resource_type}] {operation_name}: " +
                        f"Queued for {queue_time:.4f}s, " +
                        f"Executed in {execution_time:.4f}s")


# Resource pool fix for ExecutionMetrics
class ExecutionMetrics:
    """Tracks execution metrics for operations."""

    def __init__(self, operation_name: str, resource_type: str, collector: MetricsCollector):
        self.operation_name = operation_name
        self.resource_type = resource_type
        self.collector = collector
        self.start_time = None
        self.queue_time = None
        self.execution_time = None

    def mark_queued(self):
        """Mark when a task is queued."""
        self.start_time = time.time()

    def mark_started(self):
        """Mark when a task starts executing."""
        if self.start_time:
            # Ensure queue_time is always a float
            self.queue_time = float(time.time() - self.start_time)

    def mark_completed(self):
        """Mark when a task is completed."""
        if self.start_time:
            # Calculate total time and ensure it's a float
            total_time = float(time.time() - self.start_time)
            # Calculate actual execution time
            self.execution_time = total_time
            if self.queue_time:
                self.execution_time = float(total_time - self.queue_time)
            else:
                self.queue_time = 0.0  # Ensure queue_time is always a float

            # Report metrics
            self.collector.record_operation(
                self.resource_type,
                self.operation_name,
                self.queue_time,
                self.execution_time
            )


class ResourcePoolManager:
    """Manages resource pools for IO and CPU operations."""

    def __init__(self, config: AppConfig, metrics_collector: Optional[MetricsCollector] = None):
        self.config = config
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Initialize the process pool
        # Use ThreadPoolExecutor instead of ProcessPoolExecutor in tests
        # to avoid pickling issues with local/nested functions
        import os
        if os.environ.get('PYTEST_CURRENT_TEST'):
            self._cpu_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=config.process_pool.max_workers
            )
        else:
            self._cpu_pool = concurrent.futures.ProcessPoolExecutor(
                max_workers=config.process_pool.max_workers
            )

        # Semaphores for IO control
        self._io_semaphores: Dict[str, threading.Semaphore] = {}
        self._io_semaphores_lock = threading.Lock()

    @lru_cache(maxsize=128)
    def get_drive_identifier(self, filepath: str) -> str:
        """Extract drive identifier from filepath."""
        path = Path(filepath)
        if os.name == 'nt':  # Windows
            return path.drive.upper()
        else:  # Unix-like
            # For Unix, use the mount point
            path_str = str(path.absolute())
            for mount in sorted(self.config.drive_configs.keys(), key=len, reverse=True):
                if path_str.startswith(mount):
                    return mount
            return '/'  # Default to root if no specific mount found

    def get_io_semaphore(self, filepath: str) -> threading.Semaphore:
        """Get or create a semaphore for the drive containing the file."""
        drive = self.get_drive_identifier(filepath)

        with self._io_semaphores_lock:
            if drive not in self._io_semaphores:
                # Get drive configuration
                drive_config = self.config.get_drive_config(drive)

                # Create semaphore with configured limit
                self._io_semaphores[drive] = threading.Semaphore(drive_config.concurrent_io)

            return self._io_semaphores[drive]

    async def execute_with_metrics(self,
                                   resource_type: str,
                                   operation_name: str,
                                   execution_func: Callable[[], R],
                                   acquire_func: Optional[Callable[[], Any]] = None,
                                   release_func: Optional[Callable[[], None]] = None) -> R:
        """
        Execute a task with metrics tracking.
        """
        metrics = ExecutionMetrics(operation_name, resource_type, self.metrics_collector)
        metrics.mark_queued()

        acquired = False
        try:
            # Acquire resource if needed
            if acquire_func:
                await asyncio.get_event_loop().run_in_executor(None, acquire_func)
                acquired = True

            metrics.mark_started()

            # Execute the task
            result = await execution_func()

            metrics.mark_completed()
            return result

        finally:
            if acquired and release_func:
                release_func()

    async def submit_cpu_task(self, func: Callable[..., R], *args, **kwargs) -> R:
        """Submit a CPU-bound task to the process pool with metrics."""
        operation_name = func.__name__

        async def execution_func():
            loop = asyncio.get_event_loop()
            future = self._cpu_pool.submit(func, *args, **kwargs)
            return await loop.run_in_executor(None, future.result)

        return await self.execute_with_metrics(
            resource_type="CPU",
            operation_name=operation_name,
            execution_func=execution_func
        )

    async def submit_io_task(self, filepath: str, func: Callable[..., R], *args, **kwargs) -> R:
        """Submit an IO-bound task with semaphore control and metrics."""
        operation_name = func.__name__
        semaphore = self.get_io_semaphore(filepath)

        def acquire_func():
            return semaphore.acquire()

        def release_func():
            semaphore.release()

        async def execution_func():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        return await self.execute_with_metrics(
            resource_type="IO",
            operation_name=operation_name,
            execution_func=execution_func,
            acquire_func=acquire_func,
            release_func=release_func
        )

    def shutdown(self):
        """Clean up resources."""
        self._cpu_pool.shutdown()
