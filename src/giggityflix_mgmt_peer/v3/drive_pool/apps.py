from django.apps import AppConfig
import sys


class DrivePoolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'giggityflix_mgmt_peer.v3.drive_pool'
    label = 'drive_pool'

    def ready(self):
        """Initialize drive detection on startup."""
        # Skip initialization during migrations or when collecting static files
        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic']):
            return
            
        # Import here to avoid app registry not ready error
        try:
            from ..drive_service.drive_service import DriveService
            
            # Detect drives in a background thread to avoid blocking startup
            import threading
            thread = threading.Thread(target=DriveService.detect_and_persist_drives)
            thread.daemon = True
            thread.start()
        except ImportError:
            # Silently fail during testing or when models aren't ready
            pass