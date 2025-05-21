import sys

from django.apps import AppConfig


class DriveDetectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'giggityflix_mgmt_peer.apps.drive_detection'
    label = 'drive_detection'

    def ready(self):
        """Initialize drive detection on startup."""
        # Skip initialization during migrations or when collecting static files
        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'test']):
            return

        # Import here to avoid app registry not ready error
        try:
            from giggityflix_mgmt_peer.apps.drive_detection.service import DriveService

            # Detect drives in a background thread to avoid blocking startup
            import threading
            thread = threading.Thread(target=DriveService.detect_and_persist_drives)
            thread.daemon = True
            thread.start()
        except ImportError:
            # Silently fail during testing or when models aren't ready
            pass
