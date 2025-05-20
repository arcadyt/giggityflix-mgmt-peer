# giggityflix_mgmt_peer/v2/drive_pool/drive_detection/windows.py
import os
import re
import logging
from typing import Optional, Dict, List

from .models import PhysicalDrive, DriveMapping

# Set up logging
logger = logging.getLogger(__name__)

# Global drive mapping
_drive_mapping = DriveMapping()
_initialized = False
_wmi_available = None  # We'll check this once


def detect_windows_drive(filepath: str) -> str:
    """Detect physical drive for Windows filepath."""
    global _initialized

    # Initialize mapping if needed
    if not _initialized:
        _initialize_drive_mapping()

    # Extract drive letter
    drive_letter = os.path.splitdrive(filepath)[0].upper()
    if not drive_letter:
        return f"unknown_{os.path.dirname(filepath)}"

    # Look up physical drive
    drive = _drive_mapping.get_physical_drive_for_partition(drive_letter)
    if drive:
        return drive.get_drive_id()

    # Fallback to drive letter
    return f"logical_{drive_letter}"


def _is_wmi_available() -> bool:
    """Check if WMI is available."""
    global _wmi_available
    if _wmi_available is None:
        try:
            import wmi
            _wmi_available = True
        except ImportError:
            _wmi_available = False
    return _wmi_available


def _initialize_drive_mapping() -> None:
    """Initialize the drive mapping by discovering all physical drives and partitions."""
    global _initialized

    # Try WMI if available
    if _is_wmi_available():
        try:
            _initialize_from_wmi()
        except Exception as e:
            logger.error(f"WMI initialization failed: {e}")
            _initialize_fallback()
    else:
        _initialize_fallback()

    _initialized = True


def _initialize_from_wmi() -> None:
    """Initialize drive mapping using WMI."""
    import wmi
    c = wmi.WMI()

    # First get all physical disks
    for physical_disk in c.Win32_DiskDrive():
        drive_id = str(physical_disk.Index)

        # Create physical drive object
        drive = PhysicalDrive(
            id=drive_id,
            manufacturer=_clean_string(physical_disk.Manufacturer),
            model=_clean_string(physical_disk.Model),
            serial=_clean_string(physical_disk.SerialNumber),
            size_bytes=int(physical_disk.Size) if physical_disk.Size else 0,
            filesystem_type=_get_filesystem_type(physical_disk)
        )

        _drive_mapping.add_physical_drive(drive)

        # Debug output
        logger.debug(f"Found physical drive: {drive}")

    # Now map partitions to physical drives
    for partition in c.Win32_DiskPartition():
        # Extract disk ID from DeviceID
        disk_id = _extract_disk_number(partition.DeviceID)
        if disk_id is None:
            continue

        # Map logical disks (drive letters) to this partition
        for logical_disk_mapping in c.Win32_LogicalDiskToPartition():
            # Check if this mapping is for our partition
            partition_deviceid = logical_disk_mapping.Antecedent.DeviceID if hasattr(logical_disk_mapping.Antecedent,
                                                                                     'DeviceID') else None
            if partition_deviceid and partition.DeviceID in partition_deviceid:
                # Get drive letter
                logical_deviceid = logical_disk_mapping.Dependent.DeviceID if hasattr(logical_disk_mapping.Dependent,
                                                                                      'DeviceID') else None
                if logical_deviceid:
                    # Add mapping
                    _drive_mapping.add_partition_mapping(logical_deviceid, disk_id)
                    logger.debug(f"Mapped {logical_deviceid} to physical drive {disk_id}")


def _get_filesystem_type(physical_disk) -> str:
    """Get filesystem type for a physical disk."""
    try:
        import wmi
        c = wmi.WMI()

        # Try to find logical disks for this physical drive
        disk_id = str(physical_disk.Index)

        # First get partitions for this disk
        partitions = []
        for partition in c.Win32_DiskPartition():
            if _extract_disk_number(partition.DeviceID) == disk_id:
                partitions.append(partition.DeviceID)

        # Then get logical disks for these partitions
        for logical_disk_mapping in c.Win32_LogicalDiskToPartition():
            antecedent = logical_disk_mapping.Antecedent.DeviceID if hasattr(logical_disk_mapping.Antecedent,
                                                                             'DeviceID') else ""
            if any(partition in antecedent for partition in partitions):
                # Find the logical disk
                dependent = logical_disk_mapping.Dependent.DeviceID if hasattr(logical_disk_mapping.Dependent,
                                                                               'DeviceID') else ""
                if dependent:
                    for logical_disk in c.Win32_LogicalDisk():
                        if logical_disk.DeviceID == dependent:
                            return logical_disk.FileSystem or "Unknown"

        return "Unknown"
    except Exception as e:
        logger.error(f"Error getting filesystem type: {e}")
        return "Unknown"


def _initialize_fallback() -> None:
    """Initialize with basic detection when WMI is unavailable."""
    # Get all drive letters
    import string
    for letter in string.ascii_uppercase:
        drive_letter = f"{letter}:"
        if os.path.exists(drive_letter):
            # Try to get some basic drive info
            try:
                # Get filesystem type
                import subprocess
                result = subprocess.run(
                    ["fsutil", "fsinfo", "volumeinfo", drive_letter],
                    capture_output=True, text=True, check=False
                )

                filesystem_type = "Unknown"
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "File System Name" in line:
                            filesystem_type = line.split(":", 1)[1].strip()
                            break

                # Create a simple physical drive for each letter
                drive = PhysicalDrive(
                    id=letter.lower(),
                    model=f"Drive_{letter}",
                    filesystem_type=filesystem_type
                )

                # Try to get volume information
                try:
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    volume_name_buffer = ctypes.create_unicode_buffer(1024)
                    if kernel32.GetVolumeInformationW(drive_letter + "\\", volume_name_buffer,
                                                      1024, None, None, None, None, 0):
                        if volume_name_buffer.value:
                            drive.model = volume_name_buffer.value
                except Exception:
                    pass

                # Try to get drive size
                try:
                    import ctypes
                    size = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(drive_letter + "\\"),
                        None, ctypes.pointer(size), None
                    )
                    drive.size_bytes = size.value
                except Exception:
                    pass

                # Add the drive and partition mapping
                _drive_mapping.add_physical_drive(drive)
                _drive_mapping.add_partition_mapping(drive_letter, letter.lower())

            except Exception as e:
                logger.error(f"Error getting drive info for {drive_letter}: {e}")

                # Create a minimal drive entry
                drive = PhysicalDrive(
                    id=letter.lower(),
                    model=f"Drive_{letter}"
                )
                _drive_mapping.add_physical_drive(drive)
                _drive_mapping.add_partition_mapping(drive_letter, letter.lower())


def _extract_disk_number(partition_id: str) -> Optional[str]:
    """Extract disk number from partition device ID."""
    patterns = [
        r'Disk #(\d+),\s+Partition',  # Common format
        r'disk\s+#(\d+)',  # Alternative format (case insensitive)
        r'disk(\d+)',  # Simple format
    ]

    for pattern in patterns:
        match = re.search(pattern, partition_id, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def _clean_string(value: Optional[str]) -> str:
    """Clean and normalize a string value."""
    if not value:
        return "Unknown"

    # Replace spaces and special characters
    cleaned = re.sub(r'[^\w]', '_', value.strip())
    # Remove multiple underscores
    cleaned = re.sub(r'_+', '_', cleaned)
    # Remove trailing underscores
    cleaned = cleaned.strip('_')

    return cleaned or "Unknown"