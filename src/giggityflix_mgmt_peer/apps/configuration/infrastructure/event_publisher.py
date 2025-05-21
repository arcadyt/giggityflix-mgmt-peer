"""Event publisher implementation for configuration management."""
import logging
from typing import Dict, List, Optional, Callable

from django.utils import timezone

from giggityflix_mgmt_peer.apps.configuration.domain.models import ConfigurationChangeEvent

logger = logging.getLogger(__name__)


class ConfigurationEventPublisher:
    """Event publisher for configuration change events."""

    def __init__(self):
        """Initialize the event publisher."""
        self._callbacks: Dict[str, List[Callable[[ConfigurationChangeEvent], None]]] = {}
        self._global_callbacks: List[Callable[[ConfigurationChangeEvent], None]] = []

    def register_callback(self, callback: Callable[[ConfigurationChangeEvent], None],
                          key: Optional[str] = None) -> None:
        """
        Register a callback for configuration change events.
        
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
        Unregister a callback.
        
        Args:
            callback: The callback to unregister
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

    def publish_event(self, event: ConfigurationChangeEvent) -> None:
        """
        Publish a configuration change event.
        
        Args:
            event: The event to publish
        """
        # Set timestamp
        event.timestamp = timezone.now()

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


# Singleton instance
_event_publisher = None


def get_event_publisher() -> ConfigurationEventPublisher:
    """
    Get or create the event publisher singleton.
    
    Returns:
        ConfigurationEventPublisher instance
    """
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = ConfigurationEventPublisher()
    return _event_publisher
