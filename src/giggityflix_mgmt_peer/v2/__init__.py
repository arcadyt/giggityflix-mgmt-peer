# giggityflix_mgmt_peer/v2/__init__.py
"""
Giggityflix Management Peer v2 Module.

This module provides drive pool management and physical drive detection
with a neobrutalist UI for visualization.
"""

from .app import app, start_app

__all__ = ["app", "start_app"]
