# tests/conftest.py
import os
import json
import tempfile
import shutil
import pytest
from unittest.mock import MagicMock

from giggityflix_mgmt_peer.config import AppConfig, ProcessPoolConfig
from giggityflix_mgmt_peer.core.resource_pool import ResourcePoolManager, MetricsCollector
from giggityflix_mgmt_peer.services.image_processor import ImageProcessor
from giggityflix_mgmt_peer.core.di import container


# Custom MetricsCollector for testing
class TestMetricsCollector(MetricsCollector):
    def __init__(self, enabled=True):
        super().__init__(enabled=enabled)
        self.records = []

    def record_operation(self, resource_type, operation_name, queue_time, execution_time):
        self.records.append({
            'resource_type': resource_type,
            'operation_name': operation_name,
            'queue_time': queue_time,
            'execution_time': execution_time
        })


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def json_file(temp_dir):
    """Create a test JSON file."""
    file_path = os.path.join(temp_dir, 'test.json')
    data = {'test': 'data', 'nested': {'value': 42}}

    with open(file_path, 'w') as f:
        json.dump(data, f)

    return file_path


@pytest.fixture
def resource_manager():
    """Create a ResourcePoolManager for testing."""
    config = AppConfig(
        db_path=':memory:',
        process_pool=ProcessPoolConfig(max_workers=2),
        default_io_limit=4
    )

    metrics = MetricsCollector(enabled=True, logger=lambda x: None)
    manager = ResourcePoolManager(config, metrics)

    yield manager

    # Clean up
    manager.shutdown()


@pytest.fixture
def custom_resource_manager():
    """Create a ResourcePoolManager with test metrics for assertions."""
    config = AppConfig(
        db_path=':memory:',
        process_pool=ProcessPoolConfig(max_workers=2),
        default_io_limit=4
    )

    metrics = TestMetricsCollector(enabled=True)
    manager = ResourcePoolManager(config, metrics)

    yield manager

    # Clean up
    manager.shutdown()


@pytest.fixture
def config_override():
    """Fixture for configuration overrides."""
    return {
        'process_pool_workers': 2,
        'default_io_limit': 3,
        'drive_C': 4 if os.name == 'nt' else None,
        'drive_/': 2 if os.name != 'nt' else None
    }


@pytest.fixture
def image_processor():
    """Create an ImageProcessor instance for testing."""
    return ImageProcessor()


@pytest.fixture
def cleanup_container():
    """Clean up the DI container after test."""
    yield None
    container._services = {}
    container._factories = {}