"""
Configuration models for backwards compatibility.

This file re-exports the ORM models from the infrastructure layer
to maintain backwards compatibility.
"""

from giggityflix_mgmt_peer.apps.configuration.infrastructure.orm import Configuration

__all__ = ['Configuration']
