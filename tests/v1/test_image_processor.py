# tests/test_image_processor.py
import os
import json
import pytest

from giggityflix_mgmt_peer.v1.core import container
from giggityflix_mgmt_peer.v1.core import ResourcePoolManager


@pytest.mark.asyncio
async def test_process_image(temp_dir, image_processor, resource_manager, cleanup_container):
    """Test processing a single image."""
    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Create test paths
    input_path = os.path.join(temp_dir, 'test_image.jpg')
    output_path = os.path.join(temp_dir, 'output_image.jpg')

    # Create a mock input file
    with open(input_path, 'w') as f:
        f.write('mock image data')

    # Process the image
    metadata = await image_processor.process_image(input_path, output_path, apply_blur=True, detect_edges=True)

    # Verify the output file exists
    assert os.path.exists(output_path)

    # Verify the metadata
    assert metadata['input_path'] == input_path
    assert metadata['output_path'] == output_path
    assert 'blur' in metadata['operations']
    assert 'edge_detection' in metadata['operations']

    # Check the metadata file
    metadata_path = output_path.replace('.jpg', '.json')
    assert os.path.exists(metadata_path)

    with open(metadata_path, 'r') as f:
        saved_metadata = json.load(f)

    assert saved_metadata == metadata


@pytest.mark.asyncio
async def test_batch_process(temp_dir, image_processor, resource_manager, cleanup_container):
    """Test batch processing multiple images."""
    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Create test images
    image_tasks = []
    for i in range(3):
        input_path = os.path.join(temp_dir, f'input_{i}.jpg')
        output_path = os.path.join(temp_dir, f'output_{i}.jpg')

        # Create a mock input file
        with open(input_path, 'w') as f:
            f.write(f'mock image data {i}')

        # Add to tasks
        image_tasks.append({
            'input_path': input_path,
            'output_path': output_path,
            'apply_blur': i % 2 == 0,  # Alternate blur
            'detect_edges': i % 2 == 1  # Alternate edge detection
        })

    # Process all images in parallel
    results = await image_processor.batch_process(image_tasks)

    # Verify results
    assert len(results) == 3

    for i, metadata in enumerate(results):
        # Check output file exists
        assert os.path.exists(image_tasks[i]['output_path'])

        # Check operations match what we specified
        assert ('blur' in metadata['operations']) == image_tasks[i]['apply_blur']
        assert ('edge_detection' in metadata['operations']) == image_tasks[i]['detect_edges']

        # Check metadata file exists
        metadata_path = image_tasks[i]['output_path'].replace('.jpg', '.json')
        assert os.path.exists(metadata_path)


@pytest.mark.asyncio
async def test_individual_operations(temp_dir, image_processor, resource_manager, cleanup_container):
    """Test individual image operations."""
    # Register the resource manager
    container.register(ResourcePoolManager, resource_manager)

    # Create test paths
    input_path = os.path.join(temp_dir, 'test_image.jpg')
    output_path = os.path.join(temp_dir, 'output_image.jpg')

    # Create a mock input file
    with open(input_path, 'w') as f:
        f.write('mock image data')

    # Test read_image operation
    image = await image_processor.read_image(input_path)
    assert image is None  # Mock implementation returns None

    # Test save_image operation
    result = await image_processor.save_image(output_path, image)
    assert result is True
    assert os.path.exists(output_path)

    # Test save_metadata operation
    metadata = {'test': 'data'}
    metadata_path = os.path.join(temp_dir, 'metadata.json')
    await image_processor.save_metadata(metadata_path, metadata)

    assert os.path.exists(metadata_path)
    with open(metadata_path, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == metadata