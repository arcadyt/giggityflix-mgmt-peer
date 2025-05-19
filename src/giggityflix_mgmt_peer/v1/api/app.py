# src/giggityflix_mgmt_peer/api/app.py
from fastapi import FastAPI
from .router import api_router


def create_fastapi_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Giggityflix Management Peer",
        description="Resource management microservice with AOP",
        version="0.1.0",
    )

    # Include the API router
    app.include_router(api_router)

    return app