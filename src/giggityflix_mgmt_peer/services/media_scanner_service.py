import logging
import os
from typing import List

from giggityflix_mgmt_peer.config.service import config_service, ConfigurationChangeEvent

logger = logging.getLogger(__name__)


class MediaScannerService:
    """Example service that uses configuration service for media scanning."""

    def __init__(self):
        """Initialize the media scanner service."""
        self.scraping_paths = []
        self.scan_interval_minutes = 60

        # Load initial configuration
        self._load_configuration()

        # Register for configuration changes
        config_service.register_callback(self._handle_config_change, 'scraping_paths')
        config_service.register_callback(self._handle_config_change, 'scan_interval_minutes')

        logger.info("Media scanner service initialized")

    def _load_configuration(self):
        """Load configuration from the configuration service."""
        self.scraping_paths = config_service.get('scraping_paths', [])
        self.scan_interval_minutes = config_service.get('scan_interval_minutes', 60)

        logger.info(f"Loaded scraping paths: {self.scraping_paths}")
        logger.info(f"Loaded scan interval: {self.scan_interval_minutes} minutes")

    def _handle_config_change(self, event: ConfigurationChangeEvent):
        """Handle configuration change events."""
        logger.info(f"Configuration changed: {event.key} from {event.old_value} to {event.new_value}")

        if event.key == 'scraping_paths':
            self.scraping_paths = event.new_value
            logger.info(f"Updated scraping paths: {self.scraping_paths}")

            # Trigger a new scan with the updated paths
            self.scan_media()

        elif event.key == 'scan_interval_minutes':
            self.scan_interval_minutes = event.new_value
            logger.info(f"Updated scan interval: {self.scan_interval_minutes} minutes")

            # Reschedule scanning with new interval
            self._reschedule_scanning()

    def scan_media(self):
        """Scan media files in the configured paths."""
        logger.info("Starting media scan...")

        # Validate paths
        valid_paths = []
        for path in self.scraping_paths:
            if os.path.exists(path) and os.path.isdir(path):
                valid_paths.append(path)
            else:
                logger.warning(f"Skipping invalid path: {path}")

        if not valid_paths:
            logger.warning("No valid paths to scan")
            return

        # Simulate a scan (this would be a real scan in a real implementation)
        for path in valid_paths:
            logger.info(f"Scanning path: {path}")
            # Actual scanning logic would go here

        logger.info("Media scan completed")

    def _reschedule_scanning(self):
        """Reschedule automatic scanning with the new interval."""
        # In a real implementation, this would cancel any existing scheduling
        # and create a new one with the updated interval
        logger.info(f"Rescheduled automatic scanning for every {self.scan_interval_minutes} minutes")

    def add_scraping_path(self, path: str):
        """Add a new path to scan."""
        paths = list(self.scraping_paths)  # Create a copy

        if path not in paths:
            paths.append(path)
            config_service.set('scraping_paths', paths)
            # No need to update self.scraping_paths as the callback will handle it

    def remove_scraping_path(self, path: str):
        """Remove a path from scanning."""
        paths = list(self.scraping_paths)  # Create a copy

        if path in paths:
            paths.remove(path)
            config_service.set('scraping_paths', paths)
            # No need to update self.scraping_paths as the callback will handle it


# Create a singleton instance
media_scanner_service = MediaScannerService()