# src/giggityflix_mgmt_peer/api/router.py
from fastapi import APIRouter

from .resource_api import router as resource_router
# Import other routers as needed

# Main API router that includes all sub-routers
api_router = APIRouter()

# Include resource management endpoints
api_router.include_router(resource_router)

# Include other routers as needed
# api_router.include_router(other_router)