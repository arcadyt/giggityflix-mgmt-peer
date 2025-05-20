# giggityflix_mgmt_peer/v2/drive_pool/drive_detection/detection.py
import os
import platform
from typing import Dict, Callable, List

from ..cache.drive_cache import DriveInfoCache
from .models import PhysicalDrive, DriveMapping
from . import windows, linux, macos

# Global cache
drive_cache = DriveInfoCache()
drive_mapping = None
_PLATFORM = platform.system()  # Cache OS once

# Type for detector functions
DriveDetectorFunc = Callable[[str], str]

# Map of platform name to detector function
_DETECTORS: Dict[str, DriveDetectorFunc] = {
    "Windows": windows.detect_windows_drive,
    "Linux": linux.detect_linux_drive,
    "Darwin": macos.detect_macos_drive  # macOS
}


def get_drive_id_from_filepath(filepath: str) -> str:
    """Resolves a filepath to a physical drive identifier."""
    # Check cache first
    cached_id = drive_cache.get(filepath)
    if cached_id:
        return cached_id

    # Normalize path
    filepath = os.path.abspath(filepath)

    # Use the appropriate detector based on platform
    detector = _DETECTORS.get(_PLATFORM)
    if detector:
        physical_id = detector(filepath)
    else:
        physical_id = f"unknown_{os.path.dirname(filepath)}"

    # Cache the result
    drive_cache.set(filepath, physical_id)
    return physical_id


def get_drive_mapping() -> DriveMapping:
    """Get the global drive mapping for the current platform."""
    global drive_mapping

    if drive_mapping is None:
        # Initialize the mapping based on platform
        if _PLATFORM == "Windows":
            windows._initialize_drive_mapping()
            drive_mapping = windows._drive_mapping
        elif _PLATFORM == "Linux":
            linux._initialize_drive_mapping()
            drive_mapping = linux._drive_mapping
        elif _PLATFORM == "Darwin":
            macos._initialize_drive_mapping()
            drive_mapping = macos._drive_mapping
        else:
            # Fallback to empty mapping
            drive_mapping = DriveMapping()

    return drive_mapping


def get_all_physical_drives() -> List[PhysicalDrive]:
    """Get all detected physical drives."""
    mapping = get_drive_mapping()
    return mapping.get_all_physical_drives()