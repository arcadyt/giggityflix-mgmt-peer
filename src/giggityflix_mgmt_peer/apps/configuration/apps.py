from django.apps import AppConfig


class ConfigurationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'giggityflix_mgmt_peer.apps.configuration'
    label = 'configuration'

    def ready(self):
        """Initialize configuration on startup."""
        # Skip initialization if we're running tests or migrations
        import sys
        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'test']):
            return

        try:
            # Avoid circular imports by importing here
            from giggityflix_mgmt_peer.apps.configuration.service import config_service
            # Initialize configuration service
            config_service.initialize()
        except ImportError:
            # Silently fail during testing or when models aren't ready
            pass
