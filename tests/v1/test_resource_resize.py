# tests/test_resource_resize.py
import os
import time
import asyncio
import pytest

from giggityflix_mgmt_peer.v1.core import container
from giggityflix_mgmt_peer.v1.core import ResourcePoolManager
from giggityflix_mgmt_peer.v1.app import create_app


# Helper functions for slow operations
def slow_cpu_operation(seconds: float = 1.0):
    """CPU-intensive operation simulation."""
    time.sleep(seconds)
    return seconds


async def slow_io_operation(filepath: str, seconds: float = 1.0):
    """IO-intensive operation simulation."""
    # Write to the file
    with open(filepath, 'a') as f:
        f.write(f"Running IO operation for {seconds} seconds\n")
        f.flush()  # Ensure content is written to disk

    # Use asyncio.sleep instead of time.sleep for proper async behavior
    await asyncio.sleep(seconds)

    return seconds


@pytest.mark.slow
@pytest.mark.asyncio
async def test_process_pool_resize_during_execution(temp_dir):
    """Test that process pool resizing works correctly during execution."""
    # Create app with small pool
    app = create_app({"process_pool_workers": 1})
    resource_manager = container.resolve(ResourcePoolManager)

    # Start time measurement
    start_time = time.time()

    # First batch with small pool (1 worker)
    tasks = []
    for i in range(2):
        task = asyncio.create_task(resource_manager.submit_cpu_task(
            slow_cpu_operation, 2.0  # Each task takes 2 seconds
        ))
        tasks.append(task)

    # Let the first task start
    await asyncio.sleep(0.5)

    # Resize pool to 4 workers
    assert resource_manager.resize_process_pool(4)

    # Second batch with larger pool
    for i in range(2):
        task = asyncio.create_task(resource_manager.submit_cpu_task(
            slow_cpu_operation, 2.0
        ))
        tasks.append(task)

    # Wait for all tasks
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    total_time = end_time - start_time

    # Verify timing - should be much faster than sequential execution
    # Sequential: 4 tasks × 2 seconds = 8 seconds
    # With resize: first task 2s, then 3 tasks in parallel ~2s = ~4s
    assert total_time < 6.0, f"Execution took {total_time}s, expected <6s"

    # Verify all tasks completed with correct results
    assert all(r == 2.0 for r in results)

    # Verify pool size was updated
    assert resource_manager.get_process_pool_size() == 4


@pytest.mark.slow
@pytest.mark.asyncio
async def test_drive_semaphore_resize_during_execution(temp_dir):
    """Test that drive semaphore resizing works correctly during execution."""
    # Create app with restrictive IO limits
    app = create_app({"default_io_limit": 1})
    resource_manager = container.resolve(ResourcePoolManager)

    # Create "virtual" IO resources (no real files needed)
    resource_ids = [f"virtual_resource_{i}" for i in range(4)]

    # Define a simple async IO operation that just sleeps
    async def virtual_io_operation(resource_id: str, seconds: float = 1.0):
        # Just sleep to simulate IO
        await asyncio.sleep(seconds)
        return f"Completed IO on {resource_id}"

    # Start time measurement
    start_time = time.time()

    # First batch with small limit
    tasks = []
    for i in range(2):
        task = asyncio.create_task(resource_manager.submit_io_task(
            resource_ids[i], virtual_io_operation, resource_ids[i], 2.0
        ))
        tasks.append(task)

    # Let the first task start
    await asyncio.sleep(0.5)

    # Get drive identifier (use the same for all virtual resources)
    drive = resource_manager.get_drive_identifier(temp_dir)

    # Resize semaphore
    assert resource_manager.resize_drive_semaphore(drive, 4)

    # Second batch with larger limit
    for i in range(2, 4):
        task = asyncio.create_task(resource_manager.submit_io_task(
            resource_ids[i], virtual_io_operation, resource_ids[i], 2.0
        ))
        tasks.append(task)

    # Wait for all tasks
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    total_time = end_time - start_time

    # Verify timing - should be faster than sequential execution
    # Sequential: 4 tasks × 2 seconds = 8 seconds
    # With resize: ~4-5 seconds total (first task + parallelized remaining tasks)
    assert total_time < 6.0, f"Execution took {total_time}s, expected <6s"

    # Verify all tasks completed with the expected results
    for i, result in enumerate(results):
        assert result == f"Completed IO on {resource_ids[i]}"


@pytest.fixture
async def http_client():
    """Create HTTP client for testing the API."""
    from fastapi.testclient import TestClient
    from giggityflix_mgmt_peer.v1.api import create_fastapi_app
    
    # Create the application and get the FastAPI app
    app_dict = create_app()
    fastapi_app = app_dict.get("api")
    
    # Make sure we have a valid FastAPI app
    if not fastapi_app:
        fastapi_app = create_fastapi_app()
        
    return TestClient(fastapi_app)


@pytest.mark.asyncio
async def test_api_process_pool_resize(http_client):
    """Test API endpoints for process pool resizing."""
    # Get initial size
    response = http_client.get("/api/resources/pool")
    assert response.status_code == 200
    initial_size = response.json()["size"]

    # Update size
    new_size = initial_size + 2
    response = http_client.put(
        "/api/resources/pool",
        json={"size": new_size}
    )
    assert response.status_code == 200
    assert response.json()["new_size"] == new_size

    # Verify update
    response = http_client.get("/api/resources/pool")
    assert response.status_code == 200
    assert response.json()["size"] == new_size


@pytest.mark.asyncio
async def test_api_io_limit_resize(http_client, temp_dir):
    """Test API endpoints for IO limit resizing."""
    # Create test file to get drive
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("Test content")

    # Get drive identifier
    resource_manager = container.resolve(ResourcePoolManager)
    drive = resource_manager.get_drive_identifier(test_file)

    # Get initial limits
    response = http_client.get("/api/resources/io-limits")
    assert response.status_code == 200
    limits = response.json()["limits"]

    # Get current or default limit
    current_limit = limits.get(drive, resource_manager.config.default_io_limit)

    # Update limit
    new_limit = current_limit + 2
    response = http_client.put(
        "/api/resources/io-limits",
        json={"drive": drive, "limit": new_limit}
    )
    assert response.status_code == 200
    assert response.json()["limit"] == new_limit

    # Verify update
    response = http_client.get("/api/resources/io-limits")
    assert response.status_code == 200
    assert response.json()["limits"][drive] == new_limit


@pytest.mark.slow
@pytest.mark.asyncio
async def test_drive_semaphore_resize_during_execution(temp_dir):
    """Test that drive semaphore resizing works correctly during execution."""
    # Create app with restrictive IO limits
    app = create_app({"default_io_limit": 1})
    resource_manager = container.resolve(ResourcePoolManager)

    # Create "virtual" IO resources (no real files needed)
    resource_ids = [f"{temp_dir}/virtual_resource_{i}" for i in range(4)]

    # Define a simple async IO operation that just sleeps
    async def virtual_io_operation(resource_id: str, seconds: float = 1.0):
        # Just sleep to simulate IO
        await asyncio.sleep(seconds)
        return f"Completed IO on {resource_id}"

    # Start time measurement
    start_time = time.time()

    # First batch with small limit - this will allow only 1 task at a time
    tasks = []
    for i in range(2):
        task = asyncio.create_task(resource_manager.submit_io_task(
            resource_ids[i], virtual_io_operation, resource_ids[i], 2.0
        ))
        tasks.append(task)

    # Let the first task start and the second queue up
    await asyncio.sleep(0.5)

    # Get drive identifier (use the same for all virtual resources)
    drive = resource_manager.get_drive_identifier(resource_ids[0])

    # Resize semaphore to allow more concurrent operations
    resource_manager.resize_drive_semaphore(drive, 4)

    # Second batch - now we should have capacity for all remaining tasks
    for i in range(2, 4):
        task = asyncio.create_task(resource_manager.submit_io_task(
            resource_ids[i], virtual_io_operation, resource_ids[i], 2.0
        ))
        tasks.append(task)

    # Wait for all tasks
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    total_time = end_time - start_time

    # With resize: first task starts immediately (2s)
    # Second waits for first but might start in parallel with batch 2
    # after resize
    # Total should be ~4s if everything works correctly
    assert total_time < 6.0, f"Execution took {total_time}s, expected <6s"

    # Verify all tasks completed with the expected results
    for i, result in enumerate(results):
        assert result == f"Completed IO on {resource_ids[i]}"


@pytest.mark.asyncio
async def test_io_task_queueing_above_limit(temp_dir, resource_manager, cleanup_container):
    """Test that IO tasks above the semaphore limit are queued and executed."""
    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Set a specific drive limit
    drive = resource_manager.get_drive_identifier(temp_dir)
    resource_manager.resize_drive_semaphore(drive, 2)  # Limit to 2 concurrent operations

    # Create test resources
    resource_ids = [f"{temp_dir}/resource_{i}" for i in range(5)]

    # Define a simple IO operation that sleeps
    async def io_operation(resource_id: str, seconds: float = 0.5):
        await asyncio.sleep(seconds)
        return f"Completed {resource_id}"

    # Start time measurement
    start_time = time.time()

    # Submit 5 tasks (more than our limit of 2)
    tasks = []
    for i in range(5):
        task = asyncio.create_task(resource_manager.submit_io_task(
            resource_ids[i], io_operation, resource_ids[i], 0.5
        ))
        tasks.append(task)

    # Wait for all tasks
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    total_time = end_time - start_time

    # Verify timing - should take at least 1.5 seconds (3 batches × 0.5s)
    # But less than 2.5s to confirm it's not running all sequentially
    assert total_time >= 1.3, f"Execution time too short: {total_time}s"
    assert total_time < 2.5, f"Execution time too long: {total_time}s"

    # Verify all results
    for i, result in enumerate(results):
        assert result == f"Completed {resource_ids[i]}"