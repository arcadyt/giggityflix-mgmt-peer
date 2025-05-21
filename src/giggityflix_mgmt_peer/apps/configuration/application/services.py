"""Application services for configuration management."""
import logging
import os
from typing import Any, Dict, Optional

from giggityflix_mgmt_peer.apps.configuration.domain.interfaces import (
    ConfigurationRepositoryInterface,
    ConfigurationEventPublisherInterface
)
from giggityflix_mgmt_peer.apps.configuration.domain.models import ConfigurationValue, ConfigurationChangeEvent

logger = logging.getLogger(__name__)


class ConfigurationService:
    """Application service for managing configuration properties."""

    def __init__(
            self,
            repository: ConfigurationRepositoryInterface,
            event_publisher: ConfigurationEventPublisherInterface
    ):
        """
        Initialize the configuration service.
        
        Args:
            repository: Repository for configuration persistence
            event_publisher: Publisher for configuration change events
        """
        self.repository = repository
        self.event_publisher = event_publisher
        self._cache: Dict[str, Any] = {}

    def initialize(self) -> None:
        """Initialize the service, loading default configurations."""
        # Create default configurations if they don't exist
        self._ensure_defaults()

        # Load environment variables
        self._load_from_environment()

        # Clear cache to ensure fresh values
        self._cache.clear()

        logger.info("Configuration service loaded defaults and environment variables")

    def _ensure_defaults(self) -> None:
        """Ensure default configurations exist in the database."""
        defaults = [
            {
                'key': 'scraping_paths',
                'default_value': '',
                'value_type': ConfigurationValue.TYPE_LIST,
                'description': 'List of paths to scan for media files',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_SCRAPING_PATHS'
            },
            {
                'key': 'api_port',
                'default_value': '8000',
                'value_type': ConfigurationValue.TYPE_INTEGER,
                'description': 'Port for the management REST API',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_API_PORT'
            },
            {
                'key': 'log_level',
                'default_value': 'INFO',
                'value_type': ConfigurationValue.TYPE_STRING,
                'description': 'Logging level for the application',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_LOG_LEVEL'
            },
            {
                'key': 'db_path',
                'default_value': 'db.sqlite3',
                'value_type': ConfigurationValue.TYPE_STRING,
                'description': 'Path to SQLite database file',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_DB_PATH'
            },
            {
                'key': 'scan_interval_minutes',
                'default_value': '60',
                'value_type': ConfigurationValue.TYPE_INTEGER,
                'description': 'Interval in minutes between media scans',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_SCAN_INTERVAL'
            },
            {
                'key': 'enable_auto_discovery',
                'default_value': 'true',
                'value_type': ConfigurationValue.TYPE_BOOLEAN,
                'description': 'Automatically discover drives on startup',
                'is_env_overridable': True,
                'env_variable': 'GIGGITYFLIX_AUTO_DISCOVERY'
            }
        ]

        for config_data in defaults:
            try:
                # Check if config exists
                config = self.repository.get(config_data['key'])
                if not config:
                    # Create new config
                    config = ConfigurationValue(
                        key=config_data['key'],
                        default_value=config_data['default_value'],
                        value_type=config_data['value_type'],
                        description=config_data['description'],
                        is_env_overridable=config_data['is_env_overridable'],
                        env_variable=config_data['env_variable']
                    )
                    self.repository.save(config)
            except Exception as e:
                logger.error(f"Error creating default configuration '{config_data['key']}': {e}")

    def _load_from_environment(self) -> None:
        """Load configuration values from environment variables."""
        # Get all configurations
        configs = self.repository.get_all()

        for key, config in configs.items():
            if not config.is_env_overridable or not config.env_variable:
                continue

            env_value = os.environ.get(config.env_variable)
            if env_value is not None:
                old_value = config.value

                logger.info(f"Loading configuration '{config.key}' from environment variable '{config.env_variable}'")
                config.value = env_value
                self.repository.save(config)

                # Publish event
                event = ConfigurationChangeEvent(
                    key=config.key,
                    old_value=old_value,
                    new_value=config.value,
                    value_type=config.value_type
                )
                self.event_publisher.publish_event(event)

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
        if key in self._cache:
            return self._cache[key]

        # Get from repository
        config = self.repository.get(key)
        if config:
            value = config.value
            # Update cache
            self._cache[key] = value
            return value

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
            # Get existing config or create new one
            config = self.repository.get(key)
            created = False

            if not config:
                created = True
                config = ConfigurationValue(
                    key=key,
                    value_type=value_type or ConfigurationValue.TYPE_STRING
                )

            # Save old value for event
            old_value = None if created else config.value

            # Set new value
            config.value = value

            # If we're setting to the same value, skip save
            if old_value == config.value and not created:
                return True

            # Save to repository
            success = self.repository.save(config)

            # Clear cache
            if key in self._cache:
                del self._cache[key]

            # Publish event
            if success:
                event = ConfigurationChangeEvent(
                    key=key,
                    old_value=old_value,
                    new_value=config.value,
                    value_type=config.value_type
                )
                self.event_publisher.publish_event(event)

            return success

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
            # Get config for event
            config = self.repository.get(key)
            if not config:
                return False

            old_value = config.value

            # Delete from repository
            success = self.repository.delete(key)

            # Clear cache
            if key in self._cache:
                del self._cache[key]

            # Publish event
            if success:
                event = ConfigurationChangeEvent(
                    key=key,
                    old_value=old_value,
                    new_value=None,
                    value_type=config.value_type
                )
                self.event_publisher.publish_event(event)

            return success

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
        configs = self.repository.get_all()

        for key, config in configs.items():
            result[key] = config.value

        return result

    def register_callback(self, callback, key: Optional[str] = None) -> None:
        """Register a callback for configuration changes."""
        self.event_publisher.register_callback(callback, key)

    def unregister_callback(self, callback, key: Optional[str] = None) -> bool:
        """Unregister a callback."""
        return self.event_publisher.unregister_callback(callback, key)


# Singleton instance
_configuration_service = None


def get_configuration_service() -> ConfigurationService:
    """
    Get or create the configuration service singleton.
    
    Returns:
        ConfigurationService instance
    """
    global _configuration_service
    if _configuration_service is None:
        from giggityflix_mgmt_peer.apps.configuration.infrastructure.repositories import get_configuration_repository
        from giggityflix_mgmt_peer.apps.configuration.infrastructure.event_publisher import get_event_publisher

        _configuration_service = ConfigurationService(
            repository=get_configuration_repository(),
            event_publisher=get_event_publisher()
        )
    return _configuration_service
