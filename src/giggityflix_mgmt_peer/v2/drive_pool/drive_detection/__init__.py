# giggityflix_mgmt_peer/v2/drive_pool/drive_detection/__init__.py
"""
Drive detection module.

Provides cross-platform drive detection for physical drives.
"""

from .detection import get_drive_id_from_filepath, get_all_physical_drives
from .models import PhysicalDrive, DriveMapping

__all__ = [
    "get_drive_id_from_filepath",
    "get_all_physical_drives",
    "PhysicalDrive",
    "DriveMapping"
]