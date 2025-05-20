import platform
import logging
from typing import List, Dict, Any, Optional

from ..drive_pool.drive_api.models import PhysicalDrive as DbPhysicalDrive
from ..drive_pool.drive_api.models import Partition as DbPartition
from ..direct_detect import detect_drives_direct

# Set up logging
logger = logging.getLogger(__name__)

# Set up console handler for debugging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)

class DriveService:
    """Service for detecting and managing drives."""

    @staticmethod
    def detect_and_persist_drives() -> Dict[str, int]:
        """
        Detect all drives and partitions and persist them to the database.
        Returns a summary of changes.
        """
        # Clear existing data
        logger.info("Clearing existing drive data...")
        DbPartition.objects.all().delete()
        DbPhysicalDrive.objects.all().delete()

        # Detect drives using direct method
        logger.info("Detecting drives directly...")
        
        # Initialize pythoncom for WMI if on Windows
        if platform.system() == "Windows":
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except (ImportError, Exception) as e:
                logger.warning(f"Failed to initialize COM: {e}")
        
        result = detect_drives_direct()
        
        # Uninitialize pythoncom if needed
        if platform.system() == "Windows":
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except (ImportError, Exception):
                pass
        
        drives = result.get("drives", [])
        partitions = result.get("partitions", [])
        
        logger.info(f"Found {len(drives)} drives and {len(partitions)} partitions")
        
        # Persist physical drives
        drives_added = 0
        partitions_added = 0
        
        # Create a map of drive IDs to DB drives
        drive_map = {}
        
        # Add all drives to the database
        for drive_data in drives:
            drive_id = drive_data['id']
            logger.info(f"Adding drive {drive_id}")
            
            db_drive = DbPhysicalDrive(
                id=drive_id,
                manufacturer=drive_data.get('manufacturer', 'Unknown'),
                model=drive_data.get('model', 'Unknown'),
                serial=drive_data.get('serial', 'Unknown'),
                size_bytes=drive_data.get('size_bytes', 0),
                filesystem_type=drive_data.get('filesystem_type', 'Unknown')
            )
            # Auto fields aren't being set properly on direct instantiation, so set them explicitly
            from django.utils import timezone
            now = timezone.now()
            db_drive.detected_at = now
            db_drive.updated_at = now
            db_drive.save()
            
            drive_map[drive_id] = db_drive
            drives_added += 1
        
        # Add all partitions to the database
        for partition_data in partitions:
            mount_point = partition_data['mount_point']
            physical_drive_id = partition_data.get('physical_drive_id')
            
            logger.info(f"Adding partition {mount_point}")
            
            if physical_drive_id in drive_map:
                db_partition = DbPartition(
                    mount_point=mount_point,
                    physical_drive=drive_map[physical_drive_id]
                )
                # Auto fields aren't being set properly on direct instantiation, so set them explicitly
                from django.utils import timezone
                now = timezone.now()
                db_partition.created_at = now
                db_partition.updated_at = now
                db_partition.save()
                partitions_added += 1
            else:
                logger.warning(f"Cannot find physical drive {physical_drive_id} for partition {mount_point}")
        
        logger.info(f"Added {drives_added} drives and {partitions_added} partitions")
        
        return {
            "drives_added": drives_added,
            "partitions_added": partitions_added
        }