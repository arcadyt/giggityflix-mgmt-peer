"""
Configuration application for the Giggityflix Management Peer service.

This package provides configuration management functionality.
"""

from giggityflix_mgmt_peer.apps.configuration.application.services import (
    ConfigurationService,
    get_configuration_service
)

__all__ = [
    'ConfigurationService',
    'get_configuration_service',
]
