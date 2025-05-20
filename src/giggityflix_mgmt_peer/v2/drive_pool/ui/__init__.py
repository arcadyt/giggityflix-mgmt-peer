# giggityflix_mgmt_peer/v2/drive_pool/ui/__init__.py
"""
UI components for drive pool management.

Provides web-based UI for drive visualization.
"""

from .drive_dashboard import router as dashboard_router

__all__ = ["dashboard_router"]