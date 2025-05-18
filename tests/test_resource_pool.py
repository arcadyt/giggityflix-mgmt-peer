# tests/test_resource_pool.py
import os
import pytest
import asyncio
from unittest.mock import patch

from giggityflix_mgmt_peer.config import AppConfig, ProcessPoolConfig, DriveConfig
from giggityflix_mgmt_peer.core.resource_pool import ResourcePoolManager, MetricsCollector


# Test functions
def read_file(filepath: str) -> str:
    """Read a file contents."""
    with open(filepath, 'r') as f:
        return f.read()


def compute_factorial(n: int) -> int:
    """Compute factorial - CPU intensive."""
    if n <= 1:
        return 1
    return n * compute_factorial(n - 1)


@pytest.mark.asyncio
async def test_submit_io_task(json_file, custom_resource_manager):
    """Test submitting an IO task with metrics collection."""
    # Submit IO task
    result = await custom_resource_manager.submit_io_task(json_file, read_file, json_file)

    # Verify result and metrics
    with open(json_file, 'r') as f:
        expected_content = f.read()

    assert result == expected_content
    assert len(custom_resource_manager.metrics_collector.records) == 1
    assert custom_resource_manager.metrics_collector.records[0]['resource_type'] == 'IO'
    assert custom_resource_manager.metrics_collector.records[0]['operation_name'] == 'read_file'


@pytest.mark.asyncio
async def test_submit_cpu_task(custom_resource_manager):
    """Test submitting a CPU task with metrics collection."""
    # Submit CPU task
    result = await custom_resource_manager.submit_cpu_task(compute_factorial, 5)

    # Verify result and metrics
    assert result == 120
    assert len(custom_resource_manager.metrics_collector.records) == 1
    assert custom_resource_manager.metrics_collector.records[0]['resource_type'] == 'CPU'
    assert custom_resource_manager.metrics_collector.records[0]['operation_name'] == 'compute_factorial'


@pytest.mark.asyncio
async def test_drive_specific_semaphores(temp_dir, config_override):
    """Test that each drive gets its own semaphore with configured limits."""
    # Create a config with different drive limits
    config = AppConfig(
        db_path=':memory:',
        process_pool=ProcessPoolConfig(max_workers=2),
        default_io_limit=1
    )

    # Add drive configs
    drive_id = 'C:' if os.name == 'nt' else '/'
    config.drive_configs[drive_id] = DriveConfig(concurrent_io=3)

    # Create resource manager
    manager = ResourcePoolManager(config)

    # Create test files
    filepath1 = os.path.join(temp_dir, 'test1.txt')
    with open(filepath1, 'w') as f:
        f.write('test1')

    # Get semaphore for the file
    semaphore = manager.get_io_semaphore(filepath1)

    # Verify the semaphore has the correct limit
    assert semaphore.available_permits == 3

    # Try acquiring the semaphore multiple times
    assert semaphore.acquire(blocking=False)  # First acquisition
    assert semaphore.acquire(blocking=False)  # Second acquisition
    assert semaphore.acquire(blocking=False)  # Third acquisition
    assert not semaphore.acquire(blocking=False)  # Fourth should fail

    # Release all semaphores
    semaphore.release()
    semaphore.release()
    semaphore.release()


@pytest.mark.asyncio
async def test_get_drive_identifier():
    """Test that drive identifiers are correctly extracted from filepaths."""
    config = AppConfig(
        db_path=':memory:',
        process_pool=ProcessPoolConfig(max_workers=2),
        default_io_limit=1
    )

    manager = ResourcePoolManager(config)

    if os.name == 'nt':  # Windows
        assert manager.get_drive_identifier('C:\\Users\\test.txt') == 'C:'
        assert manager.get_drive_identifier('D:\\data\\file.csv') == 'D:'
    else:  # Unix-like
        assert manager.get_drive_identifier('/home/user/test.txt') == '/'

        # Add a custom mount point and test it
        config.drive_configs['/home'] = DriveConfig(concurrent_io=2)
        assert manager.get_drive_identifier('/home/user/file.txt') == '/home'