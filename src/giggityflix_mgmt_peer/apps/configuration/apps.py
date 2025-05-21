import sys

from django.apps import AppConfig


class DrivePoolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'giggityflix_mgmt_peer.drive_pool'
    label = 'drive_pool'

    def ready(self):

        try:
          pass
        except ImportError:
            # Silently fail during testing or when models aren't ready
            pass
