# src/peer/services/image_processor.py
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Import for type annotations, actual implementation uses mocks for testing
try:
    import cv2
    import numpy as np
except ImportError:
    # For environments without cv2, provide mock types
    import sys
    import types

    # Create mock modules if not available
    if 'numpy' not in sys.modules:
        np = types.ModuleType('numpy')
        np.ndarray = type('ndarray', (), {})
        sys.modules['numpy'] = np

    if 'cv2' not in sys.modules:
        cv2 = types.ModuleType('cv2')
        cv2.imread = lambda x: None
        cv2.imwrite = lambda x, y: None
        sys.modules['cv2'] = cv2

from ..core.annotations import io_bound, cpu_bound, execute_parallel


class ImageProcessor:
    """
    Example service for image processing with resource management.

    This demonstrates how to use the resource management annotations
    with functions that already perform IO or CPU-intensive operations.
    """

    @io_bound(param_name='image_path')
    def read_image(self, image_path: str) -> np.ndarray:
        """
        Read an image from disk - will use IO semaphore.
        This is a transparent wrapper around cv2.imread.
        """
        return cv2.imread(image_path)

    @cpu_bound()
    def blur_image(self, image: np.ndarray, kernel_size: Tuple[int, int] = (15, 15)) -> np.ndarray:
        """Apply Gaussian blur - CPU intensive operation."""
        if image is None:
            # For testing without actual images
            return image
        return cv2.GaussianBlur(image, kernel_size, 0)

    @cpu_bound()
    def detect_edges(self, image: np.ndarray) -> np.ndarray:
        """Detect edges in an image - CPU intensive operation."""
        if image is None:
            # For testing without actual images
            return image

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply Canny edge detection
        return cv2.Canny(gray, 100, 200)

    @io_bound(param_name='output_path')
    def save_image(self, output_path: str, image: np.ndarray) -> bool:
        """Save an image to disk - will use IO semaphore."""
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # For testing without actual images
        if image is None:
            with open(output_path, 'w') as f:
                f.write('mock image data')
            return True

        return cv2.imwrite(output_path, image)

    @io_bound(param_name='output_path')
    def save_metadata(self, output_path: str, metadata: Dict[str, Any]) -> None:
        """Save processing metadata to JSON file."""
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    async def process_image(self, input_path: str, output_path: str,
                            apply_blur: bool = True, detect_edges: bool = False) -> Dict[str, Any]:
        """Process a single image with various operations."""
        # Read the image
        img = await self.read_image(input_path)

        metadata = {
            "input_path": input_path,
            "output_path": output_path,
            "operations": []
        }

        # Apply processing operations
        if apply_blur:
            img = await self.blur_image(img)
            metadata["operations"].append("blur")

        if detect_edges:
            img = await self.detect_edges(img)
            metadata["operations"].append("edge_detection")

        # Save the processed image
        await self.save_image(output_path, img)

        # Save metadata alongside the image
        metadata_path = str(Path(output_path).with_suffix('.json'))
        await self.save_metadata(metadata_path, metadata)

        return metadata

    async def batch_process(self, image_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple images in parallel.

        Args:
            image_tasks: List of dictionaries with processing instructions
                Each dict should have:
                - input_path: source image path
                - output_path: target image path
                - apply_blur: (optional) whether to apply blur
                - detect_edges: (optional) whether to detect edges

        Returns:
            List of metadata dictionaries for each processed image
        """
        tasks = []

        for task in image_tasks:
            # Create a processing task for each image
            input_path = task["input_path"]
            output_path = task["output_path"]
            apply_blur = task.get("apply_blur", True)
            detect_edges = task.get("detect_edges", False)

            # Add as a callable task
            async def process_task(img_path=input_path, out_path=output_path,
                                   blur=apply_blur, edges=detect_edges):
                return await self.process_image(img_path, out_path, blur, edges)

            tasks.append(process_task)

        # Execute all tasks in parallel and return the results
        return await execute_parallel(*tasks)
