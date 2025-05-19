# src/peer/app.py
from typing import Dict, Any

from giggityflix_mgmt_peer.v1.api.app import create_fastapi_app
from .config import load_config
from giggityflix_mgmt_peer.v1.core.di import container
from giggityflix_mgmt_peer.v1.core.resource_pool import ResourcePoolManager, MetricsCollector
from giggityflix_mgmt_peer.v1.infrastructure.database import Database
from giggityflix_mgmt_peer.v1.services import ImageProcessor


class ApplicationFactory:
    """Factory for creating and configuring the application."""

    @staticmethod
    def create_app(config_override: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initialize the application.

        Args:
            config_override: Dictionary of configuration overrides

        Returns:
            Dictionary of initialized services
        """
        # Load configuration
        config = load_config()

        # Apply configuration overrides
        ApplicationFactory._apply_config_overrides(config, config_override)

        # Initialize services
        services = ApplicationFactory._initialize_services(config)

        # Register services in DI container
        ApplicationFactory._register_services(services)

        # Create FastAPI app
        services["api"] = create_fastapi_app()

        # Return the application context
        return services

    @staticmethod
    def _apply_config_overrides(config, config_override: Dict[str, Any] = None):
        """Apply configuration overrides."""
        if not config_override:
            return

        for key, value in config_override.items():
            if key == 'process_pool_workers':
                config.process_pool.max_workers = value
            elif key.startswith('drive_'):
                drive = key[6:]  # Remove 'drive_' prefix
                if drive not in config.drive_configs:
                    config.drive_configs[drive] = config.get_drive_config(drive)
                config.drive_configs[drive].concurrent_io = value
            elif key == 'default_io_limit':
                config.default_io_limit = value

    @staticmethod
    def _initialize_services(config):
        """Initialize application services."""
        # Initialize metrics collector
        metrics_collector = MetricsCollector()

        # Initialize resource pools
        resource_manager = ResourcePoolManager(config, metrics_collector)

        # Setup database
        db = Database(config.db_path)

        # Setup services
        image_processor = ImageProcessor()

        return {
            "config": config,
            "resource_manager": resource_manager,
            "database": db,
            "image_processor": image_processor
        }

    @staticmethod
    def _register_services(services):
        """Register services in the DI container."""
        container.register(ResourcePoolManager, services["resource_manager"])
        container.register(Database, services["database"])
        container.register(ImageProcessor, services["image_processor"])


def create_app(config_override: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convenience function to create application."""
    return ApplicationFactory.create_app(config_override)
