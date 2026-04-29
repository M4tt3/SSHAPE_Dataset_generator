import cv2
import numpy as np
from pathlib import Path

def visualize_yolo_segmentation(image_path, label_path, output_path=None):
    """
    Visualize a YOLO segmentation dataset sample.
    
    Args:
        image_path: Path to the image file
        label_path: Path to the YOLO label file (polygons with normalized coordinates)
        output_path: Optional path to save the visualization
    """
    # Read image
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Error: Could not read image {image_path}")
        return
    
    h, w = img.shape[:2]

    # We'll blend per-instance only inside polygon masks
    result = img.copy()
    
    # Read and parse YOLO labels
    try:
        with open(label_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Warning: No label file found at {label_path}")
        lines = []
    
    # Draw each polygon
    colors = [
        (0, 255, 0),      # Green
        (255, 0, 0),      # Blue
        (0, 0, 255),      # Red
        (0, 255, 255),    # Yellow
        (255, 0, 255),    # Magenta
        (255, 255, 0),    # Cyan
    ]
    
    # for i, line in enumerate(lines):
    for i, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) < 7:
            # class_id + at least 3 (x,y) points
            continue

        parts = list(map(float, parts))
        coords = parts[1:]

        # Convert normalized coordinates to pixel coordinates
        points = []
        for j in range(0, len(coords), 2):
            x = int(round(coords[j] * (w - 1)))
            y = int(round(coords[j + 1] * (h - 1)))
            x = max(0, min(w - 1, x))
            y = max(0, min(h - 1, y))
            points.append([x, y])

        if len(points) >= 3:
            points = np.array(points, dtype=np.int32)
            color = colors[i % len(colors)]

            # for p in points:
            #     cv2.circle(result, tuple(p), 2, (255 - color[0], 255 - color[1], 255 - color[2]), -1)

            # Per-polygon mask
            poly_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(poly_mask, [points], 255)

            # Blend only where the polygon exists
            alpha = 0.4
            color_img = np.zeros_like(result)
            color_img[:] = color
            blended = cv2.addWeighted(result, 1.0 - alpha, color_img, alpha, 0)
            result[poly_mask == 255] = blended[poly_mask == 255]

            # Outline on top
            cv2.polylines(result, [points], True, color, 2)
    
    # Display
    cv2.imshow('YOLO Segmentation', result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # Save if output path provided
    if output_path:
        cv2.imwrite(str(output_path), result)
        print(f"Visualization saved to {output_path}")


if __name__ == "__main__":
    # Example usage - modify these paths to your dataset
    dataset_dir = Path("E:\\probes_segmentation_yolo_rev2_blender\\")
    split = "train"  # or "val", "test"
    
    # Get first image and corresponding label
    images_dir = dataset_dir / "images" / split
    labels_dir = dataset_dir / "labels" / split
    
    if images_dir.exists() and labels_dir.exists():
        image_files = sorted(images_dir.glob("*"))
        if image_files:
            img_file = image_files[5]
            label_file = labels_dir / f"{img_file.stem}.txt"
            
            print(f"Visualizing: {img_file}")
            visualize_yolo_segmentation(img_file, label_file)
    else:
        print(f"Dataset directories not found at {dataset_dir}")
