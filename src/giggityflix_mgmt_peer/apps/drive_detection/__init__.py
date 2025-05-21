"""Drive detection package for Giggityflix Management Peer service.

This package is responsible for detecting physical drives and their partitions
on the system using domain-driven design principles.
"""

# Import key interfaces and factories for simplified access
from giggityflix_mgmt_peer.apps.drive_detection.detection import DriveDetector, DriveDetectorFactory
from giggityflix_mgmt_peer.apps.drive_detection.application.drive_service import (
    DriveApplicationService, get_drive_service
)


__all__ = [
    'DriveDetector',
    'DriveDetectorFactory',
    'DriveApplicationService',
    'get_drive_service',
]
