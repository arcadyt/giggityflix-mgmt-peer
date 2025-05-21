"""Domain interfaces for configuration management."""
from typing import Dict, Optional, Protocol, Callable

from giggityflix_mgmt_peer.apps.configuration.domain.models import ConfigurationValue, ConfigurationChangeEvent


class ConfigurationRepositoryInterface(Protocol):
    """Interface for configuration repository."""

    def get(self, key: str) -> Optional[ConfigurationValue]:
        """
        Get a configuration value by key.

        Args:
            key: The configuration key

        Returns:
            Configuration value or None if not found
        """
        ...

    def save(self, config: ConfigurationValue) -> bool:
        """
        Save a configuration value.
        
        Args:
            config: The configuration value to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        ...

    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.
        
        Args:
            key: The configuration key
            
        Returns:
            True if deleted successfully, False otherwise
        """
        ...

    def get_all(self) -> Dict[str, ConfigurationValue]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of configuration keys and values
        """
        ...


class ConfigurationEventPublisherInterface(Protocol):
    """Interface for publishing configuration change events."""

    def register_callback(self, callback: Callable[[ConfigurationChangeEvent], None],
                          key: Optional[str] = None) -> None:
        """
        Register a callback for configuration change events.
        
        Args:
            callback: Function to call when configuration changes
            key: Optional key to filter changes for specific property
        """
        ...

    def unregister_callback(self, callback: Callable[[ConfigurationChangeEvent], None],
                            key: Optional[str] = None) -> bool:
        """
        Unregister a callback.
        
        Args:
            callback: The callback to unregister
            key: The key the callback was registered for
            
        Returns:
            True if callback was removed, False otherwise
        """
        ...

    def publish_event(self, event: ConfigurationChangeEvent) -> None:
        """
        Publish a configuration change event.
        
        Args:
            event: The event to publish
        """
        ...
