# tests/test_annotations.py
import os
import pytest
import time
from unittest.mock import patch, MagicMock, ANY

from giggityflix_mgmt_peer.v1.core import io_bound, cpu_bound, execute_parallel
from giggityflix_mgmt_peer.v1.core import container
from giggityflix_mgmt_peer.v1.core import ResourcePoolManager


# Test functions with decorators
@io_bound(param_name='filepath')
def read_file(filepath: str) -> str:
    """Read a file with IO-bound annotation."""
    with open(filepath, 'r') as f:
        return f.read()


@cpu_bound()
def compute_factorial(n: int) -> int:
    """Compute factorial with CPU-bound annotation."""
    if n <= 1:
        return 1
    return n * compute_factorial(n - 1)


async def async_factorial(n: int) -> int:
    """Async function for parallel execution."""
    return compute_factorial(n)


@pytest.mark.asyncio
async def test_io_bound_decorator(json_file, resource_manager, cleanup_container):
    """Test that io_bound decorator works correctly."""
    # Mock the submit_io_task method to track calls
    with patch.object(resource_manager, 'submit_io_task', wraps=resource_manager.submit_io_task) as mock_submit:
        # Register the resource manager
        container.register(ResourcePoolManager, resource_manager)

        # Test the decorated function
        with open(json_file, 'r') as f:
            expected_content = f.read()

        content = await read_file(json_file)

        # Verify the result is correct
        assert content == expected_content

        # Verify submit_io_task was called with the correct arguments
        mock_submit.assert_called_once()
        mock_submit.assert_called_with(json_file, ANY, json_file)


@pytest.mark.asyncio
async def test_io_bound_semaphore_usage(json_file, resource_manager, cleanup_container):
    """Test that IO-bound operations properly use semaphores."""
    # Mock the semaphore acquisition/release to track calls
    semaphore = resource_manager.get_io_semaphore(json_file)
    original_acquire = semaphore.acquire
    original_release = semaphore.release

    semaphore.acquire = MagicMock(wraps=original_acquire)
    semaphore.release = MagicMock(wraps=original_release)

    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Test the decorated function
    await read_file(json_file)

    # Verify semaphore was acquired and released
    semaphore.acquire.assert_called_once()
    semaphore.release.assert_called_once()

    # Restore original methods
    semaphore.acquire = original_acquire
    semaphore.release = original_release


@pytest.mark.asyncio
async def test_cpu_bound_decorator(resource_manager, cleanup_container):
    """Test that cpu_bound decorator works correctly."""
    # Mock the submit_cpu_task method to track calls
    with patch.object(resource_manager, 'submit_cpu_task', wraps=resource_manager.submit_cpu_task) as mock_submit:
        # Register the resource manager
        container.register(ResourcePoolManager, resource_manager)

        # Test the decorated function
        result = await compute_factorial(5)

        # Verify the result is correct
        assert result == 120

        # Verify submit_cpu_task was called exactly once (not for recursive calls)
        assert mock_submit.call_count == 1
        # The first argument is the executor function we created in the decorator
        assert mock_submit.call_args[0][0].__name__ == 'executor_run'


@pytest.mark.asyncio
async def test_cpu_bound_large_recursive(resource_manager, cleanup_container):
    """Test that cpu_bound decorator works with larger recursive computations."""
    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Test with a larger factorial to ensure recursion works correctly
    result = await compute_factorial(10)
    assert result == 3628800


@pytest.mark.asyncio
async def test_metrics_collection(json_file, resource_manager, cleanup_container):
    """Test that metrics are collected correctly for operations."""
    # Create a mock metrics collector
    mock_collector = MagicMock()
    resource_manager.metrics_collector = mock_collector

    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Test the decorated function
    await read_file(json_file)

    # Verify metrics were recorded
    mock_collector.record_operation.assert_called_once()
    # Check arguments: resource_type, operation_name, queue_time, execution_time
    args = mock_collector.record_operation.call_args[0]
    assert args[0] == "IO"
    assert args[1] == "read_file"
    assert isinstance(args[2], float)  # queue_time
    assert isinstance(args[3], float)  # execution_time

@pytest.mark.asyncio
async def test_execute_parallel_with_functions(resource_manager, cleanup_container):
    """Test executing multiple functions in parallel."""
    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Create test coroutines with explicit CPU-bound decoration
    @cpu_bound()
    def cpu_task1():
        time.sleep(0.9)  # This will run in a worker process
        return 10

    @cpu_bound()
    def cpu_task2():
        time.sleep(0.9)  # This will run in a worker process
        return 20

    # Task3 uses the existing compute_factorial which is already CPU-bound
    async def task3():
        return await compute_factorial(4)

    # Add timing to verify parallel execution
    start_time = time.time()

    # Execute parallel tasks
    results = await execute_parallel(cpu_task1, cpu_task2, cpu_task2)

    end_time = time.time()
    execution_time = end_time - start_time

    # Verify results
    assert results == [10, 20, 20]

    # If tasks ran in parallel, execution time should be closer to the longest task
    assert execution_time < 1.9, "Tasks should execute in parallel, not sequentially"


@pytest.mark.asyncio
async def test_execute_parallel_with_tuples(temp_dir, resource_manager, cleanup_container):
    """Test executing tasks as (func, args, kwargs) tuples in parallel."""
    # Mock resource manager methods to track calls
    with patch.object(resource_manager, 'submit_io_task', wraps=resource_manager.submit_io_task) as mock_io, \
            patch.object(resource_manager, 'submit_cpu_task', wraps=resource_manager.submit_cpu_task) as mock_cpu:
        # Register the resource manager
        container.register(ResourcePoolManager, resource_manager)

        # Create test files
        file1 = os.path.join(temp_dir, 'test1.txt')
        file2 = os.path.join(temp_dir, 'test2.txt')

        with open(file1, 'w') as f:
            f.write('content1')

        with open(file2, 'w') as f:
            f.write('content2')

        # Create task tuples
        task1 = (read_file, (file1,), {})
        task2 = (read_file, (file2,), {})
        task3 = (compute_factorial, (4,), {})

        # Execute parallel tasks
        results = await execute_parallel(task1, task2, task3)

        # Verify results
        assert results == ['content1', 'content2', 24]

        # Verify the correct resource manager methods were called
        assert mock_io.call_count == 2  # Two file reads
        assert mock_cpu.call_count == 1  # One factorial calculation


@pytest.mark.asyncio
async def test_execute_parallel_mixed(temp_dir, resource_manager, cleanup_container):
    """Test executing a mix of task types in parallel."""
    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Create a test file
    test_file = os.path.join(temp_dir, 'test.txt')
    with open(test_file, 'w') as f:
        f.write('test content')

    # Create a mix of task types
    async def task1():
        return 'result1'

    task2 = (read_file, (test_file,), {})

    async def task3():
        return await compute_factorial(3)

    # Execute parallel tasks
    results = await execute_parallel(task1, task2, task3)

    # Verify results
    assert results == ['result1', 'test content', 6]


@pytest.mark.asyncio
async def test_recursive_cpu_bound_internal_mechanics(resource_manager, cleanup_container):
    """Test the internal mechanics of recursive cpu_bound functions."""
    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Mock the _cpu_pool.submit method to count calls
    original_submit = resource_manager._cpu_pool.submit
    submit_count = 0

    def counting_submit(*args, **kwargs):
        nonlocal submit_count
        submit_count += 1
        return original_submit(*args, **kwargs)

    resource_manager._cpu_pool.submit = counting_submit

    try:
        # Execute a recursive cpu-bound function
        result = await compute_factorial(5)

        # Verify the result
        assert result == 120

        # Verify the executor was used exactly once
        # If recursive calls go through the executor, there would be multiple submissions
        assert submit_count == 1, "Recursive calls should bypass the executor"

    finally:
        # Restore the original method
        resource_manager._cpu_pool.submit = original_submit