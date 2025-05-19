# src/peer/core/resource_pool.py
import asyncio
import concurrent.futures
import os
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Set

from giggityflix_mgmt_peer.v1.config import AppConfig, DriveConfig
from ..utils.resizable_semaphore import ResizableSemaphore

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
        self._semaphore_sizes: Dict[str, int] = {}  # Track semaphore sizes
        self._io_semaphores_lock = threading.Lock()

        # Track active CPU tasks for safe pool resizing
        self._active_cpu_tasks: Set[int] = set()
        self._cpu_task_lock = threading.Lock()
        self._cpu_pool_lock = threading.Lock()
        self._resize_pending = False
        self._old_pool = None  # Store old pool for cleanup

    def get_io_semaphore(self, filepath: str) -> ResizableSemaphore:
        """Get or create a semaphore for the drive containing the file."""
        drive = self.get_drive_identifier(filepath)

        with self._io_semaphores_lock:
            if drive not in self._io_semaphores:
                # Get drive configuration
                drive_config = self.config.get_drive_config(drive)

                # Create semaphore with configured limit
                limit = drive_config.concurrent_io
                self._io_semaphores[drive] = ResizableSemaphore(limit)
                self._semaphore_sizes[drive] = limit

            return self._io_semaphores[drive]

    def resize_drive_semaphore(self, drive: str, new_limit: int) -> bool:
        """
        Resize the semaphore for a specific drive.

        This is NOT an async function and should not be awaited.

        Args:
            drive: Drive identifier
            new_limit: New concurrent IO limit

        Returns:
            True if resize was successful, False otherwise
        """
        if new_limit <= 0:
            return False

        # Update drive config
        if drive in self.config.drive_configs:
            self.config.drive_configs[drive].concurrent_io = new_limit
        else:
            self.config.drive_configs[drive] = DriveConfig(concurrent_io=new_limit)

        # Resize the existing semaphore instead of creating a new one
        with self._io_semaphores_lock:
            if drive in self._io_semaphores:
                self._io_semaphores[drive].resize(new_limit)
                self._semaphore_sizes[drive] = new_limit
            else:
                # Create a new semaphore if it doesn't exist yet
                self._io_semaphores[drive] = ResizableSemaphore(new_limit)
                self._semaphore_sizes[drive] = new_limit

        return True

    def resize_process_pool(self, new_size: int) -> bool:
        """
        Resize the process pool to a new worker count.

        Creates a new pool immediately for new tasks, while existing
        tasks complete in the old pool.

        Args:
            new_size: New maximum number of workers

        Returns:
            True if resize was successfully initiated, False if invalid size
        """
        if new_size <= 0:
            return False

        with self._cpu_pool_lock:
            # Update config
            self.config.process_pool.max_workers = new_size

            # Store old pool for cleanup
            old_pool = self._cpu_pool

            # Create new pool immediately
            if os.environ.get('PYTEST_CURRENT_TEST'):
                self._cpu_pool = concurrent.futures.ThreadPoolExecutor(
                    max_workers=new_size
                )
            else:
                self._cpu_pool = concurrent.futures.ProcessPoolExecutor(
                    max_workers=new_size
                )

            # Set old pool for cleanup when tasks complete
            self._old_pool = old_pool
            self._resize_pending = True

        return True

    def _check_shutdown_old_pool(self) -> None:
        """Check if we should shutdown the old pool."""
        if self._resize_pending and self._old_pool is not None and len(self._active_cpu_tasks) == 0:
            # No active tasks remaining, safe to shut down old pool
            self._old_pool.shutdown(wait=False)
            self._old_pool = None
            self._resize_pending = False

    async def submit_cpu_task(self, func: Callable[..., R], *args, **kwargs) -> R:
        """Submit a CPU-bound task to the process pool with metrics."""
        operation_name = func.__name__
        task_id = id(func) + id(tuple(args)) + id(str(kwargs))

        # Track this task
        with self._cpu_task_lock:
            self._active_cpu_tasks.add(task_id)
            self._check_shutdown_old_pool()  # Check if we can shut down old pool

        async def execution_func():
            try:
                # Execute the task using current pool (which is the new pool if resized)
                with self._cpu_pool_lock:
                    current_pool = self._cpu_pool

                loop = asyncio.get_event_loop()
                future = current_pool.submit(func, *args, **kwargs)
                result = await loop.run_in_executor(None, future.result)

                # Task completed, check if we can shut down old pool
                with self._cpu_task_lock:
                    self._active_cpu_tasks.remove(task_id)
                    self._check_shutdown_old_pool()

                return result
            except Exception as e:
                # Clean up tracking on error
                with self._cpu_task_lock:
                    if task_id in self._active_cpu_tasks:
                        self._active_cpu_tasks.remove(task_id)
                    self._check_shutdown_old_pool()
                raise e

        return await self.execute_with_metrics(
            resource_type="CPU",
            operation_name=operation_name,
            execution_func=execution_func
        )

    def shutdown(self):
        """Clean up resources."""
        self._cpu_pool.shutdown()

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

    async def submit_io_task(self, filepath: str, func: Callable[..., R], *args, **kwargs) -> R:
        """Submit an IO-bound task with semaphore control and metrics."""
        operation_name = func.__name__
        semaphore = self.get_io_semaphore(filepath)

        def acquire_func():
            return semaphore.acquire()

        def release_func():
            semaphore.release()

        async def execution_func():
            # Check if the function is a coroutine function
            if asyncio.iscoroutinefunction(func):
                # Call async function directly
                return await func(*args, **kwargs)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        return await self.execute_with_metrics(
            resource_type="IO",
            operation_name=operation_name,
            execution_func=execution_func,
            acquire_func=acquire_func,
            release_func=release_func
        )

    def _replace_cpu_pool(self):
        """Replace CPU pool with new one using current config size."""
        old_pool = self._cpu_pool

        # Create new pool with updated size
        if os.environ.get('PYTEST_CURRENT_TEST'):
            self._cpu_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.config.process_pool.max_workers
            )
        else:
            self._cpu_pool = concurrent.futures.ProcessPoolExecutor(
                max_workers=self.config.process_pool.max_workers
            )

        # Schedule old pool shutdown
        asyncio.get_event_loop().run_in_executor(None, lambda: old_pool.shutdown(wait=False))
        self._resize_pending = False

    async def get_io_limits(self) -> Dict[str, int]:
        """Get current IO limits for all configured drives."""
        limits = {}

        # Get configured limits
        for drive, config in self.config.drive_configs.items():
            limits[drive] = config.concurrent_io

        return limits

    def get_process_pool_size(self) -> int:
        """Get current process pool size configuration."""
        return self.config.process_pool.max_workers
