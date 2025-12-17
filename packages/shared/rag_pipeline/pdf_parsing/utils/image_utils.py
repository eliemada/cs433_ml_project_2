"""
Image processing utilities.
"""

import io
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import pymupdf
from PIL import Image

from rag_pipeline.pdf_parsing.data_models import ImageDimensions


def convert_pdf_to_images(pdf_path: Path, target_size: int = 896) -> List[Image.Image]:
    """
    Convert PDF pages to images.

    Args:
        pdf_path: Path to PDF file
        target_size: Target size for the longest dimension

    Returns:
        List of PIL Images, one per page

    Raises:
        Exception: If PDF cannot be opened or converted
    """
    images = []
    try:
        doc = pymupdf.open(str(pdf_path))

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Calculate scale to make longest dimension equal to target_size
            rect = page.rect
            scale = target_size / max(rect.width, rect.height)

            # Render page as image
            mat = pymupdf.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img_data = pix.tobytes("png")
            pil_image = Image.open(io.BytesIO(img_data))
            images.append(pil_image)

        doc.close()
        print(f"Successfully converted {len(images)} pages from PDF")
        return images

    except Exception as e:
        raise Exception(f"Error converting PDF to images: {str(e)}")


def prepare_image(image: Image.Image) -> Tuple[np.ndarray, ImageDimensions]:
    """
    Prepare image with padding while maintaining aspect ratio.

    Creates a square padded image for consistent model input.

    Args:
        image: PIL image

    Returns:
        Tuple of (padded_image_array, image_dimensions)
    """
    try:
        # Convert PIL image to OpenCV format
        image_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        original_h, original_w = image_array.shape[:2]

        # Calculate padding to make square image
        max_size = max(original_h, original_w)
        top = (max_size - original_h) // 2
        bottom = max_size - original_h - top
        left = (max_size - original_w) // 2
        right = max_size - original_w - left

        # Apply padding with black borders
        padded_image = cv2.copyMakeBorder(
            image_array, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(0, 0, 0)
        )

        padded_h, padded_w = padded_image.shape[:2]

        dimensions = ImageDimensions(
            original_width=original_w, original_height=original_h, padded_width=padded_w, padded_height=padded_h
        )

        return padded_image, dimensions

    except Exception as e:
        print(f"prepare_image error: {str(e)}")
        # Create a minimal valid image and dimensions
        h, w = image.height, image.width
        dimensions = ImageDimensions(original_width=w, original_height=h, padded_width=w, padded_height=h)
        return np.zeros((h, w, 3), dtype=np.uint8), dimensions


def crop_image_region(image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> Image.Image:
    """
    Crop a region from an image array.

    Args:
        image: Image array (OpenCV format)
        x1, y1, x2, y2: Crop coordinates

    Returns:
        PIL Image of the cropped region
    """
    try:
        cropped = image[y1:y2, x1:x2]
        if cropped.size > 0 and cropped.shape[0] > 3 and cropped.shape[1] > 3:
            pil_crop = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
            return pil_crop
        else:
            raise ValueError("Invalid crop region")
    except Exception as e:
        raise Exception(f"Error cropping image region: {str(e)}")


def save_image(image: Image.Image, output_path: Path, format: str = "PNG", quality: int = 95) -> None:
    """
    Save a PIL image to disk.

    Args:
        image: PIL Image to save
        output_path: Path to save image
        format: Image format (PNG, JPEG, etc.)
        quality: Image quality (1-100 for JPEG)
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format=format, quality=quality)
    except Exception as e:
        raise Exception(f"Error saving image: {str(e)}")