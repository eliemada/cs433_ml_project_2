"""
Coordinate transformation utilities for image processing.

Handles coordinate mapping between padded and original image spaces.
"""

from typing import Tuple

import numpy as np

from rag_pipeline.pdf_parsing.data_models import ImageDimensions


def map_to_original_coordinates(
    x1: int, y1: int, x2: int, y2: int, dims: ImageDimensions
) -> Tuple[int, int, int, int]:
    """
    Map coordinates from padded image back to original image.

    Args:
        x1, y1, x2, y2: Coordinates in padded image
        dims: Image dimensions object

    Returns:
        Tuple of (x1, y1, x2, y2) coordinates in original image
    """
    try:
        # Calculate padding offsets
        top = (dims.padded_height - dims.original_height) // 2
        left = (dims.padded_width - dims.original_width) // 2

        # Map back to original coordinates
        orig_x1 = max(0, x1 - left)
        orig_y1 = max(0, y1 - top)
        orig_x2 = min(dims.original_width, x2 - left)
        orig_y2 = min(dims.original_height, y2 - top)

        # Ensure we have a valid box (width and height > 0)
        if orig_x2 <= orig_x1:
            orig_x2 = min(orig_x1 + 1, dims.original_width)
        if orig_y2 <= orig_y1:
            orig_y2 = min(orig_y1 + 1, dims.original_height)

        return int(orig_x1), int(orig_y1), int(orig_x2), int(orig_y2)

    except Exception as e:
        print(f"map_to_original_coordinates error: {str(e)}")
        # Return safe coordinates
        return 0, 0, min(100, dims.original_width), min(100, dims.original_height)


def process_coordinates(
    coords: list, padded_image: np.ndarray, dims: ImageDimensions, previous_box: list = None
) -> Tuple[int, int, int, int, int, int, int, int, list]:
    """
    Process and adjust coordinates from normalized space to pixel space.

    Args:
        coords: Normalized coordinates [x1, y1, x2, y2] in 896x896 space
        padded_image: Padded image array
        dims: Image dimensions object
        previous_box: Previous box coordinates for overlap adjustment

    Returns:
        Tuple of (x1, y1, x2, y2, orig_x1, orig_y1, orig_x2, orig_y2, new_previous_box)
    """
    try:
        # Convert normalized coordinates (896x896) to absolute coordinates
        x1 = round(coords[0] / 896.0 * dims.padded_width)
        y1 = round(coords[1] / 896.0 * dims.padded_height)
        x2 = round(coords[2] / 896.0 * dims.padded_width) + 1
        y2 = round(coords[3] / 896.0 * dims.padded_height) + 1

        # Ensure coordinates are within image bounds
        x1 = max(0, min(x1, dims.padded_width - 1))
        y1 = max(0, min(y1, dims.padded_height - 1))
        x2 = max(0, min(x2, dims.padded_width))
        y2 = max(0, min(y2, dims.padded_height))

        # Ensure width and height are at least 1 pixel
        if x2 <= x1:
            x2 = min(x1 + 1, dims.padded_width)
        if y2 <= y1:
            y2 = min(y1 + 1, dims.padded_height)

        # Check for overlap with previous box and adjust
        if previous_box is not None:
            prev_x1, prev_y1, prev_x2, prev_y2 = previous_box
            if (x1 < prev_x2 and x2 > prev_x1) and (y1 < prev_y2 and y2 > prev_y1):
                y1 = prev_y2
                y1 = min(y1, dims.padded_height - 1)
                if y2 <= y1:
                    y2 = min(y1 + 1, dims.padded_height)

        # Update previous box
        new_previous_box = [x1, y1, x2, y2]

        # Map to original coordinates
        orig_x1, orig_y1, orig_x2, orig_y2 = map_to_original_coordinates(x1, y1, x2, y2, dims)

        return x1, y1, x2, y2, orig_x1, orig_y1, orig_x2, orig_y2, new_previous_box

    except Exception as e:
        print(f"process_coordinates error: {str(e)}")
        # Return safe values
        orig_x1, orig_y1, orig_x2, orig_y2 = 0, 0, min(100, dims.original_width), min(
            100, dims.original_height
        )
        return 0, 0, 100, 100, orig_x1, orig_y1, orig_x2, orig_y2, [0, 0, 100, 100]


def parse_layout_string(bbox_str: str) -> list:
    """
    Parse Dolphin layout string to extract bbox and category information.

    Supports formats:
    1. [x1,y1,x2,y2] label
    2. [x1,y1,x2,y2][label][PAIR_SEP]
    3. [x1,y1,x2,y2][label][meta_info][PAIR_SEP]

    Args:
        bbox_str: Layout string from Dolphin model

    Returns:
        List of (coords, label) tuples
    """
    import re

    parsed_results = []

    segments = bbox_str.split("[PAIR_SEP]")
    new_segments = []
    for seg in segments:
        new_segments.extend(seg.split("[RELATION_SEP]"))
    segments = new_segments

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        coord_pattern = r"\[(\d*\.?\d+),(\d*\.?\d+),(\d*\.?\d+),(\d*\.?\d+)\]"
        label_pattern = r"\]\[([^\]]+)\]"

        coord_match = re.search(coord_pattern, segment)
        label_matches = re.findall(label_pattern, segment)

        if coord_match and label_matches:
            coords = [float(coord_match.group(i)) for i in range(1, 5)]
            label = label_matches[0].strip()
            parsed_results.append((coords, label))

    return parsed_results