"""
Direct drive detection script for Windows.
This file can be run as a standalone script to test drive detection.
"""
import os
import platform
import subprocess
import string
import logging
import re
import json
import time
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("direct_detect")

def _is_wmi_available() -> bool:
    """Check if WMI is available."""
    try:
        import wmi
        return True
    except ImportError:
        return False

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

def detect_windows_drives_direct():
    """Directly detect Windows drives using WMI if available, or fallback to simpler methods."""
    if _is_wmi_available():
        try:
            # Try WMI detection first
            import pythoncom
            pythoncom.CoInitialize()  # Initialize COM for the thread
            result = _detect_windows_drives_wmi()
            pythoncom.CoUninitialize()  # Clean up
            return result
        except Exception as e:
            logger.error(f"WMI detection failed: {e}")
    
    return _detect_windows_drives_fallback()

def _detect_windows_drives_wmi():
    """Detect Windows drives using WMI."""
    logger.info("Detecting Windows drives using WMI...")
    drives = []
    partitions = []
    
    try:
        import wmi
        c = wmi.WMI()
        
        # First get all physical disks
        for physical_disk in c.Win32_DiskDrive():
            drive_id = str(physical_disk.Index)
            
            # Collect drive info
            drive = {
                "id": drive_id,
                "manufacturer": _clean_string(physical_disk.Manufacturer),
                "model": _clean_string(physical_disk.Model),
                "serial": _clean_string(physical_disk.SerialNumber),
                "size_bytes": int(physical_disk.Size) if physical_disk.Size else 0,
                "filesystem_type": "Unknown"  # Will be determined from partitions
            }
            
            # Add to drives list
            drives.append(drive)
            logger.info(f"Found physical drive: {drive['id']} - {drive['manufacturer']} {drive['model']}")
        
        # Now map partitions to physical drives
        for partition in c.Win32_DiskPartition():
            disk_id = _extract_disk_number(partition.DeviceID)
            if disk_id is None:
                logger.warning(f"Couldn't extract disk ID from {partition.DeviceID}")
                continue
            
            # Map logical disks (drive letters) to this partition
            for logical_disk_mapping in c.Win32_LogicalDiskToPartition():
                try:
                    # Get Antecedent DeviceID safely
                    partition_deviceid = None
                    if hasattr(logical_disk_mapping, 'Antecedent'):
                        antecedent = logical_disk_mapping.Antecedent
                        if hasattr(antecedent, 'DeviceID'):
                            partition_deviceid = antecedent.DeviceID
                    
                    if partition_deviceid and partition.DeviceID in partition_deviceid:
                        # Get drive letter safely
                        logical_deviceid = None
                        if hasattr(logical_disk_mapping, 'Dependent'):
                            dependent = logical_disk_mapping.Dependent
                            if hasattr(dependent, 'DeviceID'):
                                logical_deviceid = dependent.DeviceID
                        
                        if logical_deviceid:
                            # Add partition mapping
                            partition_entry = {
                                "mount_point": logical_deviceid,
                                "physical_drive_id": disk_id
                            }
                            partitions.append(partition_entry)
                            logger.info(f"Mapped {logical_deviceid} to physical drive {disk_id}")
                            
                            # Try to get filesystem type
                            for logical_disk in c.Win32_LogicalDisk():
                                if logical_disk.DeviceID == logical_deviceid and logical_disk.FileSystem:
                                    fs_type = logical_disk.FileSystem
                                    # Find the corresponding drive and update filesystem type
                                    for drive in drives:
                                        if drive["id"] == disk_id and drive["filesystem_type"] == "Unknown":
                                            drive["filesystem_type"] = fs_type
                                            logger.info(f"Found filesystem type: {fs_type} for drive {disk_id}")
                                            break
                except Exception as e:
                    logger.warning(f"Error processing partition mapping: {e}")
        
        return {
            "drives": drives,
            "partitions": partitions
        }
    
    except Exception as e:
        logger.error(f"WMI drive detection error: {e}")
        raise

def _detect_windows_drives_fallback():
    """Fallback method for Windows drive detection when WMI is unavailable."""
    logger.info("Using fallback drive detection for Windows...")
    drives = []
    partitions = []
    
    # Use simple drive letter detection
    for letter in string.ascii_uppercase:
        drive_letter = f"{letter}:"
        if os.path.exists(drive_letter):
            # Try to get some basic drive info
            try:
                # Get filesystem type using fsutil
                filesystem_type = "Unknown"
                try:
                    import subprocess
                    result = subprocess.run(
                        ["fsutil", "fsinfo", "volumeinfo", drive_letter],
                        capture_output=True, text=True, check=False
                    )
                    
                    if result.returncode == 0:
                        for line in result.stdout.splitlines():
                            if "File System Name" in line:
                                filesystem_type = line.split(":", 1)[1].strip()
                                break
                except Exception as e:
                    logger.warning(f"fsutil failed: {e}")
                
                # Try to get volume information
                import ctypes
                kernel32 = ctypes.windll.kernel32
                volume_name_buffer = ctypes.create_unicode_buffer(1024)
                volume_serial = ctypes.c_ulong(0)
                max_component_length = ctypes.c_ulong(0)
                file_system_flags = ctypes.c_ulong(0)
                file_system_name_buffer = ctypes.create_unicode_buffer(1024)
                
                model = f"Drive_{letter}"
                
                if kernel32.GetVolumeInformationW(
                    ctypes.c_wchar_p(f"{drive_letter}\\"),
                    volume_name_buffer,
                    1024,
                    ctypes.byref(volume_serial),
                    ctypes.byref(max_component_length),
                    ctypes.byref(file_system_flags),
                    file_system_name_buffer,
                    1024
                ):
                    if volume_name_buffer.value:
                        model = volume_name_buffer.value
                    if file_system_name_buffer.value and filesystem_type == "Unknown":
                        filesystem_type = file_system_name_buffer.value
                
                # Try to get drive size
                size = 0
                try:
                    free_bytes = ctypes.c_ulonglong(0)
                    total_bytes = ctypes.c_ulonglong(0)
                    total_free_bytes = ctypes.c_ulonglong(0)
                    
                    if kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(f"{drive_letter}\\"),
                        ctypes.byref(free_bytes),
                        ctypes.byref(total_bytes),
                        ctypes.byref(total_free_bytes)
                    ):
                        size = total_bytes.value
                except Exception as e:
                    logger.warning(f"Failed to get drive size: {e}")
                
                # Create drive entry 
                drive_id = f"win_{letter.lower()}"
                drive = {
                    "id": drive_id,
                    "manufacturer": "Unknown",  # Can't get from fallback
                    "model": model,
                    "serial": str(volume_serial.value) if volume_serial.value else "Unknown",
                    "size_bytes": size,
                    "filesystem_type": filesystem_type
                }
                
                drives.append(drive)
                logger.info(f"Added drive: {drive['id']} - {drive['model']} ({drive['size_bytes']} bytes)")
                
                # Add partition mapping
                partition = {
                    "mount_point": drive_letter,
                    "physical_drive_id": drive_id
                }
                
                partitions.append(partition)
                logger.info(f"Added partition: {drive_letter} -> {drive_id}")
                
            except Exception as e:
                logger.error(f"Error processing drive {drive_letter}: {e}")
                
                # Create minimal entries
                drive_id = f"win_{letter.lower()}"
                drives.append({
                    "id": drive_id,
                    "model": f"Drive_{letter}",
                    "size_bytes": 0
                })
                
                partitions.append({
                    "mount_point": drive_letter,
                    "physical_drive_id": drive_id
                })
    
    return {
        "drives": drives,
        "partitions": partitions
    }

def detect_linux_drives_direct():
    """Directly detect Linux drives."""
    drives = []
    partitions = []
    
    try:
        # Try using lsblk for detection
        logger.info("Running lsblk command...")
        process = subprocess.run(
            ["lsblk", "-Jbo", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL,FSTYPE"],
            capture_output=True, text=True, check=True
        )
        
        data = json.loads(process.stdout)
        
        for device in data.get("blockdevices", []):
            if device.get("type") == "disk":
                drive_id = device.get("name", "unknown")
                
                drive = {
                    "id": drive_id,
                    "model": device.get("model", "Unknown").strip(),
                    "serial": device.get("serial", "Unknown").strip(),
                    "size_bytes": int(device.get("size", 0)),
                    "filesystem_type": device.get("fstype", "Unknown").strip()
                }
                
                drives.append(drive)
                
                # Process partitions
                for child in device.get("children", []):
                    if child.get("mountpoint"):
                        partition = {
                            "mount_point": child.get("mountpoint"),
                            "physical_drive_id": drive_id
                        }
                        partitions.append(partition)
    
    except Exception as e:
        logger.error(f"lsblk detection failed: {e}")
        
        # Fall back to mount points
        try:
            logger.info("Falling back to /proc/mounts...")
            with open("/proc/mounts", "r") as f:
                mounts = f.readlines()
            
            for i, line in enumerate(mounts):
                parts = line.split()
                if len(parts) >= 2 and parts[0].startswith('/'):
                    device = parts[0]
                    mount_point = parts[1]
                    
                    drive = {
                        "id": f"linux_{i}",
                        "model": f"Mount_{mount_point.replace('/', '_')}",
                        "size_bytes": 0
                    }
                    
                    drives.append(drive)
                    
                    partition = {
                        "mount_point": mount_point,
                        "physical_drive_id": f"linux_{i}"
                    }
                    
                    partitions.append(partition)
                    
        except Exception as e:
            logger.error(f"Mount detection failed: {e}")
            
            # Last resort - add root
            drives.append({
                "id": "root",
                "model": "Root_Volume",
                "size_bytes": 0
            })
            
            partitions.append({
                "mount_point": "/",
                "physical_drive_id": "root"
            })
    
    return {
        "drives": drives,
        "partitions": partitions
    }

def detect_macos_drives_direct():
    """Directly detect macOS drives."""
    drives = []
    partitions = []
    
    try:
        # Try using diskutil
        logger.info("Running diskutil command...")
        process = subprocess.run(
            ["diskutil", "list", "-plist"],
            capture_output=True, text=True, check=True
        )
        
        import plistlib
        disks_data = plistlib.loads(process.stdout.encode('utf-8'))
        
        for disk_name in disks_data.get("AllDisksAndPartitions", []):
            if "DeviceIdentifier" in disk_name:
                disk_id = disk_name["DeviceIdentifier"]
                
                # Get disk info
                info_process = subprocess.run(
                    ["diskutil", "info", "-plist", disk_id],
                    capture_output=True, text=True, check=True
                )
                
                info = plistlib.loads(info_process.stdout.encode('utf-8'))
                
                drive = {
                    "id": disk_id,
                    "model": info.get("DeviceModel", "Unknown"),
                    "size_bytes": info.get("Size", 0),
                    "filesystem_type": info.get("FilesystemType", "Unknown")
                }
                
                drives.append(drive)
                
                # Add mount point if available
                if "MountPoint" in info and info["MountPoint"]:
                    partition = {
                        "mount_point": info["MountPoint"],
                        "physical_drive_id": disk_id
                    }
                    partitions.append(partition)
    
    except Exception as e:
        logger.error(f"diskutil detection failed: {e}")
        
        # Fall back to mount command
        try:
            logger.info("Falling back to mount command...")
            process = subprocess.run(
                ["mount"],
                capture_output=True, text=True, check=True
            )
            
            mount_lines = process.stdout.splitlines()
            
            for i, line in enumerate(mount_lines):
                parts = line.split(" on ")
                if len(parts) >= 2:
                    device = parts[0]
                    mount_parts = parts[1].split(" (")
                    if len(mount_parts) >= 1:
                        mount_point = mount_parts[0]
                        
                        drive = {
                            "id": f"macos_{i}",
                            "model": f"Volume_{os.path.basename(mount_point)}",
                            "size_bytes": 0
                        }
                        
                        drives.append(drive)
                        
                        partition = {
                            "mount_point": mount_point,
                            "physical_drive_id": f"macos_{i}"
                        }
                        
                        partitions.append(partition)
        
        except Exception as e:
            logger.error(f"Mount detection failed: {e}")
            
            # Last resort - add root
            drives.append({
                "id": "root",
                "model": "Root_Volume",
                "size_bytes": 0
            })
            
            partitions.append({
                "mount_point": "/",
                "physical_drive_id": "root"
            })
    
    return {
        "drives": drives,
        "partitions": partitions
    }

def detect_drives_direct():
    """Detect drives using the direct detection method based on platform."""
    platform_name = platform.system()
    
    if platform_name == "Windows":
        return detect_windows_drives_direct()
    elif platform_name == "Linux":
        return detect_linux_drives_direct()
    elif platform_name == "Darwin":
        return detect_macos_drives_direct()
    else:
        logger.error(f"Unsupported platform: {platform_name}")
        return {
            "drives": [],
            "partitions": []
        }

if __name__ == "__main__":
    """Run as standalone script for testing."""
    platform_name = platform.system()
    logger.info(f"Detecting drives on {platform_name}...")
    
    result = detect_drives_direct()
    
    drives = result["drives"]
    partitions = result["partitions"]
    
    logger.info(f"Found {len(drives)} drives and {len(partitions)} partitions")
    
    # Print detailed info
    for drive in drives:
        logger.info(f"Drive: {drive['id']} - {drive['manufacturer']} {drive['model']} ({drive['size_bytes']} bytes)")
    
    for partition in partitions:
        logger.info(f"Partition: {partition['mount_point']} -> {partition['physical_drive_id']}")
