from django.apps import AppConfig
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .signals import configuration_changed

class ConfigurationConfig(AppConfig):
    name = 'giggityflix_mgmt_peer.apps.configuration'

    def ready(self):
        # import receivers so they are registered          # one-liner
        from . import receivers  # noqa


# receivers.py (optional separate file) -------------------------
from .signals import configuration_changed

@receiver(configuration_changed)
def invalidate_local_cache(sender, key, value, **kwargs):
    from . import services
    services._CACHE.pop(key, None)          # one-liner
