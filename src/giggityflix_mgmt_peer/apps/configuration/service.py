# src/giggityflix_mgmt_peer/services/configuration_service.py
import os
import logging
import threading
from typing import Any, Callable, Dict, List, Optional

from django.utils import timezone
from django.db.models.signals import post_save

from giggityflix_mgmt_peer.apps.configuration.configuration_model import Configuration

logger = logging.getLogger(__name__)


class ConfigurationChangeEvent:
    """Event object passed to callbacks when configuration changes."""

    def __init__(self, key: str, old_value: Any, new_value: Any, value_type: str):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.value_type = value_type
        self.timestamp = timezone.now()


class ConfigurationService:
    """Service for managing configuration properties."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure only one instance exists."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigurationService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the configuration service."""
        if self._initialized:
            return

        self._callbacks: Dict[str, List[Callable[[ConfigurationChangeEvent], None]]] = {}
        self._global_callbacks: List[Callable[[ConfigurationChangeEvent], None]] = []
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._initialized = True

        # Register for Django signals
        post_save.connect(self._handle_configuration_save, sender=Configuration)

        logger.info("Configuration service initialized")

    def initialize(self) -> None:
        """Initialize the service, loading default configurations."""
        # Create default configurations if they don't exist
        self._ensure_defaults()

        # Load environment variables
        self._load_from_environment()

        # Clear cache to ensure fresh values
        with self._cache_lock:
            self._cache.clear()

        logger.info("Configuration service loaded defaults and environment variables")

    def _ensure_defaults(self) -> None:
        """Ensure default configurations exist in the database."""
        defaults = [
            {
                'key': 'scraping_paths',
                'default_value': '',
                'value_type': Configuration.TYPE_LIST,
                'description': 'List of paths to scan for media files',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_SCRAPING_PATHS'
            },
            {
                'key': 'api_port',
                'default_value': '8000',
                'value_type': Configuration.TYPE_INTEGER,
                'description': 'Port for the management REST API',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_API_PORT'
            },
            {
                'key': 'log_level',
                'default_value': 'INFO',
                'value_type': Configuration.TYPE_STRING,
                'description': 'Logging level for the application',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_LOG_LEVEL'
            },
            {
                'key': 'db_path',
                'default_value': 'db.sqlite3',
                'value_type': Configuration.TYPE_STRING,
                'description': 'Path to SQLite database file',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_DB_PATH'
            },
            {
                'key': 'scan_interval_minutes',
                'default_value': '60',
                'value_type': Configuration.TYPE_INTEGER,
                'description': 'Interval in minutes between media scans',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_SCAN_INTERVAL'
            },
            {
                'key': 'enable_auto_discovery',
                'default_value': 'true',
                'value_type': Configuration.TYPE_BOOLEAN,
                'description': 'Automatically discover drives on startup',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_AUTO_DISCOVERY'
            }
        ]

        for config in defaults:
            try:
                Configuration.objects.get_or_create(
                    key=config['key'],
                    defaults={
                        'default_value': config['default_value'],
                        'value_type': config['value_type'],
                        'description': config['description'],
                        'is_env_overridable': config['is_env_overridable'],
                        'env_variable': config['env_variable']
                    }
                )
            except Exception as e:
                logger.error(f"Error creating default configuration '{config['key']}': {e}")

    def _load_from_environment(self) -> None:
        """Load configuration values from environment variables."""
        configurations = Configuration.objects.filter(is_env_overridable=True)

        for config in configurations:
            if not config.env_variable:
                continue

            env_value = os.environ.get(config.env_variable)
            if env_value is not None:
                old_value = config.get_typed_value()

                logger.info(f"Loading configuration '{config.key}' from environment variable '{config.env_variable}'")
                config.set_typed_value(env_value)
                config.save()

                # No need to trigger callbacks here as the save will trigger Django signals

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: The configuration key
            default: Default value if configuration doesn't exist

        Returns:
            The typed configuration value
        """
        # Check cache first
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]

        try:
            config = Configuration.objects.get(key=key)
            value = config.get_typed_value()

            # Cache the value
            with self._cache_lock:
                self._cache[key] = value

            return value
        except Configuration.DoesNotExist:
            return default

    def set(self, key: str, value: Any, value_type: Optional[str] = None) -> bool:
        """
        Set a configuration value.

        Args:
            key: The configuration key
            value: The value to set
            value_type: Override the value type if creating a new configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            config, created = Configuration.objects.get_or_create(
                key=key,
                defaults={
                    'value_type': value_type or Configuration.TYPE_STRING,
                    'default_value': str(value) if value is not None else None
                }
            )

            old_value = config.get_typed_value()
            config.set_typed_value(value)

            # If we're setting to the same value, skip save to avoid triggering callbacks
            new_value = config.get_typed_value()
            if old_value == new_value and not created:
                return True

            config.save()

            # Clear cache
            with self._cache_lock:
                if key in self._cache:
                    del self._cache[key]

            return True
        except Exception as e:
            logger.error(f"Error setting configuration '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a configuration property.

        Args:
            key: The configuration key

        Returns:
            True if successful, False otherwise
        """
        try:
            config = Configuration.objects.get(key=key)
            old_value = config.get_typed_value()
            config.delete()

            # Clear cache
            with self._cache_lock:
                if key in self._cache:
                    del self._cache[key]

            # Trigger callbacks manually since deletion doesn't trigger signals
            event = ConfigurationChangeEvent(key, old_value, None, config.value_type)
            self._notify_callbacks(event)

            return True
        except Configuration.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error deleting configuration '{key}': {e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dictionary of configuration keys and their typed values
        """
        result = {}
        for config in Configuration.objects.all():
            result[config.key] = config.get_typed_value()
        return result

    def register_callback(self, callback: Callable[[ConfigurationChangeEvent], None],
                          key: Optional[str] = None) -> None:
        """
        Register a callback to be notified when configuration changes.

        Args:
            callback: Function to call when configuration changes
            key: Optional key to filter changes for specific property
        """
        if key:
            if key not in self._callbacks:
                self._callbacks[key] = []
            self._callbacks[key].append(callback)
        else:
            self._global_callbacks.append(callback)

        logger.debug(f"Registered {'global' if not key else key} configuration change callback")

    def unregister_callback(self, callback: Callable[[ConfigurationChangeEvent], None],
                            key: Optional[str] = None) -> bool:
        """
        Unregister a previously registered callback.

        Args:
            callback: The callback function to unregister
            key: The key the callback was registered for

        Returns:
            True if callback was removed, False otherwise
        """
        if key:
            if key in self._callbacks and callback in self._callbacks[key]:
                self._callbacks[key].remove(callback)
                return True
        else:
            if callback in self._global_callbacks:
                self._global_callbacks.remove(callback)
                return True
        return False

    def _handle_configuration_save(self, sender, instance, created, **kwargs):
        """Handle Django's post_save signal for Configuration model."""
        # Determine the old value (challenge: we don't have it after save)
        # For now, we'll set old_value to None for created items
        old_value = None if created else instance.get_typed_value()
        new_value = instance.get_typed_value()

        # Clear cache
        with self._cache_lock:
            if instance.key in self._cache:
                old_value = self._cache[instance.key]  # Use cached value as old value
                del self._cache[instance.key]

        # Create event
        event = ConfigurationChangeEvent(
            instance.key, old_value, new_value, instance.value_type
        )

        # Notify callbacks
        self._notify_callbacks(event)

    def _notify_callbacks(self, event: ConfigurationChangeEvent) -> None:
        """Notify all relevant callbacks about a configuration change."""
        # Call key-specific callbacks
        if event.key in self._callbacks:
            for callback in self._callbacks[event.key]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in configuration callback for key '{event.key}': {e}")

        # Call global callbacks
        for callback in self._global_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in global configuration callback: {e}")


# Create a singleton instance
config_service = ConfigurationService()