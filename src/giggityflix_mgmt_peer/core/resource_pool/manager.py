"""Resource pool manager for controlling IO and CPU resources."""
import asyncio
import multiprocessing
import os
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import lru_cache
from typing import Dict, Optional

from giggityflix_mgmt_peer.apps.drive_detection import get_drive_service


class ResourcePoolManager:
    """Manager for IO and CPU resource allocation."""

    def __init__(self, cpu_workers: Optional[int] = None, default_io_limit: int = 2):
        """
        Initialize the resource pool manager.
        
        Args:
            cpu_workers: Number of CPU workers (defaults to CPU count)
            default_io_limit: Default IO operations per drive
        """
        self.default_io_limit = int(os.environ.get('PEER_DEFAULT_IO_LIMIT', default_io_limit))
        self.cpu_workers = int(os.environ.get('PEER_CPU_WORKERS', cpu_workers or multiprocessing.cpu_count()))

        # Initialize resource pools
        self._drive_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._drive_semaphores_lock = threading.Lock()

        # Initialize process pool for CPU-bound tasks
        self._process_pool = ProcessPoolExecutor(max_workers=self.cpu_workers)

        # Initialize thread pool for IO-bound tasks
        self._thread_pool = ThreadPoolExecutor(max_workers=self.cpu_workers * 2)

    def get_drive_semaphore(self, drive_path: str) -> asyncio.Semaphore:
        """
        Get a semaphore for controlling access to a specific drive.
        
        Args:
            drive_path: Path to the drive
            
        Returns:
            Semaphore for the drive
        """
        drive_id = self._get_drive_id_for_path(drive_path)

        with self._drive_semaphores_lock:
            if drive_id not in self._drive_semaphores:
                # Get custom limit for this drive if configured
                limit = int(os.environ.get(f'PEER_DRIVE_{drive_id}_IO', self.default_io_limit))
                self._drive_semaphores[drive_id] = asyncio.Semaphore(limit)

            return self._drive_semaphores[drive_id]

    @lru_cache(maxsize=1024)
    def _get_drive_id_for_path(self, path: str) -> str:
        """
        Get the drive ID for a path.
        
        Args:
            path: File system path
            
        Returns:
            Drive ID
        """
        # Get drive mapping from drive detection service
        drive_mapping = get_drive_service().get_drive_mapping()

        # Normalize path
        normalized_path = os.path.abspath(path)

        # Find the partition that contains this path
        for physical_drive in drive_mapping.get_all_physical_drives():
            partitions = drive_mapping.get_partitions_for_drive(physical_drive.id)

            for partition in partitions:
                if normalized_path.startswith(partition):
                    return physical_drive.id

        # If no mapping found, use first directory component as fallback
        path_parts = normalized_path.split(os.sep)
        drive_id = path_parts[0] if path_parts else "unknown"

        # For Windows, handle drive letters
        if len(drive_id) == 2 and drive_id[1] == ':':
            drive_id = drive_id[0].lower()

        return f"drive_{drive_id}"

    def get_process_pool(self) -> ProcessPoolExecutor:
        """Get the process pool for CPU-bound tasks."""
        return self._process_pool

    def get_thread_pool(self) -> ThreadPoolExecutor:
        """Get the thread pool for IO-bound tasks."""
        return self._thread_pool

    async def shutdown(self):
        """Shutdown all pools."""
        self._process_pool.shutdown(wait=True)
        self._thread_pool.shutdown(wait=True)


# Singleton instance
_resource_pool_manager = None


def get_resource_pool_manager() -> ResourcePoolManager:
    """
    Get or create the resource pool manager singleton.
    
    Returns:
        ResourcePoolManager instance
    """
    global _resource_pool_manager
    if _resource_pool_manager is None:
        _resource_pool_manager = ResourcePoolManager()
    return _resource_pool_manager
