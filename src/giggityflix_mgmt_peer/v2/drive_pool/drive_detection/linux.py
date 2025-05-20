# giggityflix_mgmt_peer/v2/drive_pool/drive_detection/linux.py
import os
import logging
import subprocess
import re
from typing import Dict, List, Optional, Tuple

from .models import PhysicalDrive, DriveMapping

# Set up logging
logger = logging.getLogger(__name__)

# Global drive mapping
_drive_mapping = DriveMapping()
_initialized = False


def detect_linux_drive(filepath: str) -> str:
    """Detect physical drive for Linux filepath."""
    global _initialized

    # Initialize mapping if needed
    if not _initialized:
        _initialize_drive_mapping()

    # Get mount point for the file
    mount_point = _get_mount_point(filepath)
    if not mount_point:
        return f"unknown_{os.path.dirname(filepath)}"

    # Look up physical drive
    drive = _drive_mapping.get_physical_drive_for_partition(mount_point)
    if drive:
        return drive.get_drive_id()

    # Fallback to mount point
    return f"mount_{mount_point.replace('/', '_')}"


def _get_mount_point(filepath: str) -> Optional[str]:
    """Find the mount point for a given file path."""
    filepath = os.path.abspath(filepath)

    while not os.path.ismount(filepath):
        parent = os.path.dirname(filepath)
        if parent == filepath:
            # We've reached the root without finding a mount point
            return None
        filepath = parent

    return filepath


def _initialize_drive_mapping() -> None:
    """Initialize the drive mapping by discovering all physical drives and partitions."""
    global _initialized

    try:
        # Use lsblk to get drive information
        _initialize_from_lsblk()
    except Exception as e:
        logger.error(f"Drive detection error: {e}")
        _initialize_fallback()

    _initialized = True


def _initialize_from_lsblk() -> None:
    """Initialize drive mapping using lsblk command."""
    try:
        # Run lsblk to get JSON output of all block devices
        process = subprocess.run(
            ["lsblk", "-Jbo", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL,FSTYPE"],
            capture_output=True, text=True, check=True
        )

        import json
        data = json.loads(process.stdout)

        # Process the block devices
        for device in data.get("blockdevices", []):
            if device.get("type") == "disk":
                # This is a physical disk
                drive_id = device.get("name", "unknown")

                # Create physical drive object
                drive = PhysicalDrive(
                    id=drive_id,
                    model=device.get("model", "Unknown").strip(),
                    serial=device.get("serial", "Unknown").strip(),
                    size_bytes=int(device.get("size", 0))
                )

                _drive_mapping.add_physical_drive(drive)
                logger.debug(f"Found physical drive: {drive}")

                # Process partitions
                _process_partitions(device, drive_id)

    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"lsblk initialization failed: {e}")
        raise


def _process_partitions(device: Dict, drive_id: str) -> None:
    """Process partitions of a physical drive."""
    for child in device.get("children", []):
        if child.get("mountpoint"):
            mount_point = child.get("mountpoint")
            partition_name = child.get("name", "unknown")

            _drive_mapping.add_partition_mapping(mount_point, drive_id)
            logger.debug(f"Mapped {mount_point} to physical drive {drive_id}")


def _initialize_fallback() -> None:
    """Initialize with basic detection when lsblk is unavailable."""
    # Just map mount points with unique IDs
    mount_points = _get_mount_points_fallback()

    for i, mount_point in enumerate(mount_points):
        # Create a simple physical drive for each mount point
        drive = PhysicalDrive(
            id=f"fallback_{i}",
            model=f"Mount_{mount_point.replace('/', '_')}"
        )
        _drive_mapping.add_physical_drive(drive)
        _drive_mapping.add_partition_mapping(mount_point, drive.id)


def _get_mount_points_fallback() -> List[str]:
    """Get a list of mount points as fallback."""
    try:
        with open("/proc/mounts", "r") as f:
            mounts = f.readlines()

        return [line.split()[1] for line in mounts if line.startswith('/')]
    except Exception:
        # Last resort fallback
        return ["/"]