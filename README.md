# Resource Management Framework

A Python framework for efficient IO and CPU resource management with parallel execution support.

## Components

- **Resource Pool Manager**: Controls allocation of IO and CPU resources
- **Annotations**: Decorators for resource-managed operations
- **Dependency Injection**: Simple DI container for service management

## Core Features

### IO-Bound Operations

`@io_bound(param_name='filepath')` decorator manages access to IO resources, limiting concurrent operations per storage
device:

```python
@io_bound(param_name='filepath')
def read_file(filepath: str) -> str:
    with open(filepath, 'r') as f:
        return f.read()
```

### CPU-Bound Operations

`@cpu_bound()` decorator executes operations in a process pool, preventing CPU saturation:

```python
@cpu_bound()
def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

Handles recursive function calls correctly using thread-local state tracking to prevent deadlocks:

```python
@cpu_bound()
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)  # Recursion works without deadlock
```

### Parallel Execution

`execute_parallel()` runs multiple tasks concurrently:

```python
# Run mixed task types in parallel
results = await execute_parallel(
    async_task(),  # Async function
    (cpu_function, (arg1, arg2), {})  # (func, args, kwargs) tuple
)
```

## Implementation Details

### Drive-Specific IO Management

- Configurable per-drive IO concurrency limits
- Automatic drive identification (Windows drives, Unix mount points)
- Dynamic semaphore creation based on resource limits

### CPU Management

- Process/Thread pool with configurable worker count
- Scalable execution metrics for performance tracking
- Recursive call detection using thread-local storage to prevent executor deadlocks

### Dependency Injection

Type-based service resolution with factory support:

```python
container.register(ResourcePoolManager, manager)
container.resolve(ResourcePoolManager)  # Returns registered instance
```

## Configuration

Environment variables control pool sizes and IO limits:

- `PEER_CPU_WORKERS`: Maximum concurrent CPU tasks (default: CPU count)
- `PEER_DEFAULT_IO_LIMIT`: Default IO operations per drive (default: 2)
- `PEER_DRIVE_*_IO`: Per-drive IO limits
