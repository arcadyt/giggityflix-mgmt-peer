# giggityflix_mgmt_peer/v2/drive_pool/drive_detection/models.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class PhysicalDrive:
    """Represents a physical storage device."""
    id: str  # Unique identifier for the drive
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    serial: str = "Unknown"
    size_bytes: int = 0
    partitions: List[str] = field(default_factory=list)  # List of partition identifiers
    filesystem_type: str = "Unknown"

    def __str__(self) -> str:
        return f"{self.manufacturer}_{self.model}_{self.id}"

    def get_drive_id(self) -> str:
        """Get a standardized drive ID string."""
        if self.manufacturer != "Unknown" and self.model != "Unknown":
            return f"physical_{self.manufacturer}_{self.model}_{self.id}"
        elif self.model != "Unknown":
            return f"physical_{self.model}_{self.id}"
        else:
            return f"physical_disk_{self.id}"

    def get_formatted_size(self) -> str:
        """Get human-readable size."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
        elif self.size_bytes < 1024 * 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.1f} GB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024 * 1024):.1f} TB"


@dataclass
class DriveMapping:
    """Maps physical drives to their logical volumes/partitions."""
    physical_drives: Dict[str, PhysicalDrive] = field(default_factory=dict)
    logical_to_physical: Dict[str, str] = field(default_factory=dict)  # Maps partition/volume to physical drive ID

    def add_physical_drive(self, drive: PhysicalDrive) -> None:
        """Add a physical drive to the mapping."""
        self.physical_drives[drive.id] = drive

    def add_partition_mapping(self, partition_id: str, physical_drive_id: str) -> None:
        """Map a partition/volume to a physical drive."""
        if physical_drive_id in self.physical_drives:
            drive = self.physical_drives[physical_drive_id]
            if partition_id not in drive.partitions:
                drive.partitions.append(partition_id)
            self.logical_to_physical[partition_id] = physical_drive_id

    def get_physical_drive_for_partition(self, partition_id: str) -> Optional[PhysicalDrive]:
        """Get the physical drive for a partition."""
        physical_id = self.logical_to_physical.get(partition_id)
        if physical_id and physical_id in self.physical_drives:
            return self.physical_drives[physical_id]
        return None

    def get_all_partitions(self) -> Set[str]:
        """Get all known partitions/volumes."""
        return set(self.logical_to_physical.keys())

    def get_all_physical_drives(self) -> List[PhysicalDrive]:
        """Get all physical drives."""
        return list(self.physical_drives.values())