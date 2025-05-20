# giggityflix_mgmt_peer/v2/drive_pool/cache/drive_cache.py
import os
from typing import Dict, Optional
import time


class DriveInfoCache:
    """Cache for mapping file paths to drive IDs."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._cache: Dict[str, tuple[str, float]] = {}  # filepath -> (drive_id, timestamp)
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

    def get(self, filepath: str) -> Optional[str]:
        """Get drive ID for a filepath if in cache and not expired."""
        # Normalize path for consistent caching
        filepath = os.path.abspath(filepath)

        if filepath in self._cache:
            drive_id, timestamp = self._cache[filepath]
            if time.time() - timestamp < self._ttl_seconds:
                return drive_id

            # Expired, remove from cache
            del self._cache[filepath]

        return None

    def set(self, filepath: str, drive_id: str) -> None:
        """Store drive ID for a filepath."""
        # Normalize path for consistent caching
        filepath = os.path.abspath(filepath)

        # Check if cache is full and needs cleanup
        if len(self._cache) >= self._max_size:
            self._cleanup()

        self._cache[filepath] = (drive_id, time.time())

    def _cleanup(self) -> None:
        """Remove oldest or expired entries when cache is full."""
        # First pass: remove expired entries
        now = time.time()
        expired_keys = [
            k for k, (_, timestamp) in self._cache.items()
            if now - timestamp >= self._ttl_seconds
        ]

        for key in expired_keys:
            del self._cache[key]

        # If still too many entries, remove oldest
        if len(self._cache) >= self._max_size:
            # Sort by timestamp (oldest first)
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            # Remove oldest 25% of entries
            to_remove = max(1, len(sorted_items) // 4)
            for k, _ in sorted_items[:to_remove]:
                del self._cache[k]