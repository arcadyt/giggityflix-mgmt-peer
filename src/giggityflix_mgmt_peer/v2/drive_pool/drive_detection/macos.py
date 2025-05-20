# giggityflix_mgmt_peer/v2/drive_pool/drive_detection/macos.py
import os
import logging
import subprocess
import re
from typing import Dict, List, Optional

from .models import PhysicalDrive, DriveMapping

# Set up logging
logger = logging.getLogger(__name__)

# Global drive mapping
_drive_mapping = DriveMapping()
_initialized = False


def detect_macos_drive(filepath: str) -> str:
    """Detect physical drive for macOS filepath."""
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
    return f"volume_{os.path.basename(mount_point)}"


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
        # Try diskutil to get drive information
        _initialize_from_diskutil()
    except Exception as e:
        logger.error(f"Drive detection error: {e}")
        _initialize_fallback()

    _initialized = True


def _initialize_from_diskutil() -> None:
    """Initialize drive mapping using diskutil command."""
    try:
        # Get list of disks
        process = subprocess.run(
            ["diskutil", "list", "-plist"],
            capture_output=True, text=True, check=True
        )

        import plistlib
        disks_data = plistlib.loads(process.stdout.encode('utf-8'))

        # Process each disk
        for disk_name in disks_data.get("AllDisksAndPartitions", []):
            if "DeviceIdentifier" in disk_name:
                disk_id = disk_name["DeviceIdentifier"]

                # Get disk info
                disk_info = _get_disk_info(disk_id)

                # Create physical drive
                drive = PhysicalDrive(
                    id=disk_id,
                    model=disk_info.get("model", "Unknown"),
                    size_bytes=int(disk_info.get("size", 0)),
                    filesystem_type=disk_info.get("filesystem", "Unknown")
                )

                _drive_mapping.add_physical_drive(drive)

                # Process volumes
                for volume in disk_info.get("volumes", []):
                    mount_point = volume.get("mount_point")
                    if mount_point:
                        _drive_mapping.add_partition_mapping(mount_point, disk_id)
                        logger.debug(f"Mapped {mount_point} to physical drive {disk_id}")

    except (subprocess.SubprocessError, plistlib.Error) as e:
        logger.error(f"diskutil initialization failed: {e}")
        raise


def _get_disk_info(disk_id: str) -> Dict:
    """Get detailed info for a disk using diskutil."""
    try:
        process = subprocess.run(
            ["diskutil", "info", "-plist", disk_id],
            capture_output=True, text=True, check=True
        )

        import plistlib
        info = plistlib.loads(process.stdout.encode('utf-8'))

        # Extract relevant info
        disk_info = {
            "model": info.get("DeviceModel", "Unknown"),
            "size": info.get("Size", 0),
            "filesystem": info.get("FilesystemType", "Unknown"),
            "volumes": []
        }

        # Get mounted volumes
        if "MountPoint" in info and info["MountPoint"]:
            disk_info["volumes"].append({"mount_point": info["MountPoint"]})

        return disk_info

    except Exception as e:
        logger.error(f"Error getting disk info for {disk_id}: {e}")
        return {"model": "Unknown", "size": 0, "filesystem": "Unknown", "volumes": []}


def _initialize_fallback() -> None:
    """Initialize with basic detection when diskutil is unavailable."""
    # Get mounted volumes
    try:
        process = subprocess.run(
            ["mount"],
            capture_output=True, text=True, check=True
        )

        mount_lines = process.stdout.splitlines()

        for i, line in enumerate(mount_lines):
            parts = line.split(" on ")
            if len(parts) >= 2:
                device = parts[0]
                mount_point = parts[1].split(" (")[0]

                # Create a simple physical drive
                drive = PhysicalDrive(
                    id=f"fallback_{i}",
                    model=f"Volume_{os.path.basename(mount_point)}"
                )

                _drive_mapping.add_physical_drive(drive)
                _drive_mapping.add_partition_mapping(mount_point, drive.id)

    except Exception as e:
        logger.error(f"Fallback initialization failed: {e}")

        # Last resort - just add root
        drive = PhysicalDrive(id="root", model="Root_Volume")
        _drive_mapping.add_physical_drive(drive)
        _drive_mapping.add_partition_mapping("/", "root")