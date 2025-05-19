# src/giggityflix_mgmt_peer/api/resource_api.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..core.di import container
from ..core.resource_pool import ResourcePoolManager

# Create router with prefix
router = APIRouter(
    prefix="/api/resources",
    tags=["resources"],
    responses={404: {"description": "Not found"}},
)


class ProcessPoolUpdate(BaseModel):
    size: int = Field(..., gt=0, description="New process pool size")


class DriveLimitUpdate(BaseModel):
    drive: str = Field(..., description="Drive identifier (e.g., 'C:' or '/')")
    limit: int = Field(..., gt=0, description="New IO operation limit")


def get_resource_manager():
    """Dependency to get resource manager."""
    return container.resolve(ResourcePoolManager)


@router.get("/pool")
async def get_process_pool_size(
        resource_manager: ResourcePoolManager = Depends(get_resource_manager)
):
    """Get current process pool size."""
    return {"size": resource_manager.get_process_pool_size()}


@router.put("/pool")
async def update_process_pool_size(
        update: ProcessPoolUpdate,
        resource_manager: ResourcePoolManager = Depends(get_resource_manager)
):
    """Update process pool size."""
    success = resource_manager.resize_process_pool(update.size)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to resize process pool")

    return {"status": "success", "new_size": update.size}


@router.get("/io-limits")
async def get_io_limits(
        resource_manager: ResourcePoolManager = Depends(get_resource_manager)
):
    """Get current IO limits for all drives."""
    limits = await resource_manager.get_io_limits()
    return {"limits": limits}


@router.put("/io-limits")
async def update_io_limit(
        update: DriveLimitUpdate,
        resource_manager: ResourcePoolManager = Depends(get_resource_manager)
):
    """Update IO limit for a specific drive."""
    success = resource_manager.resize_drive_semaphore(update.drive, update.limit)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to update IO limit")

    return {"status": "success", "drive": update.drive, "limit": update.limit}