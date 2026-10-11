"""
Panorama Creator — Helper Functions
Image conversion, thumbnail creation, and synthetic test image generation.
"""

import logging
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

from config import (
    THUMBNAIL_MAX_W,
    THUMBNAIL_MAX_H,
    TEST_CANVAS_WIDTH,
    TEST_CANVAS_HEIGHT,
    TEST_OVERLAP,
    TEST_STRIP_WIDTH,
    TEST_IMAGE_COUNT,
    TEST_RANDOM_SEED,
)

logger = logging.getLogger("PanoramaApp.helpers")


def cv_to_qpixmap(cv_img: np.ndarray | None) -> QPixmap:
    """
    Convert OpenCV image (BGR or grayscale) to QPixmap.
    
    Args:
        cv_img: OpenCV image array (BGR or grayscale), or None
        
    Returns:
        QPixmap, or null QPixmap on failure
    """
    if cv_img is None:
        logger.warning("cv_to_qpixmap received None")
        return QPixmap()
    
    try:
        # Handle grayscale input
        if len(cv_img.shape) == 2:
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2BGR)
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        
        # Create QImage from contiguous data
        # Make a copy to ensure data stays valid
        rgb_copy = np.ascontiguousarray(rgb)
        bytes_per_line = ch * w
        qimg = QImage(
            rgb_copy.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )
        
        # Deep copy the QImage to detach from numpy array
        return QPixmap.fromImage(qimg.copy())
    except Exception as e:
        logger.error("Failed to convert cv image to QPixmap: %s", e, exc_info=True)
        return QPixmap()


def make_thumbnail(
    pixmap: QPixmap,
    max_w: int = THUMBNAIL_MAX_W,
    max_h: int = THUMBNAIL_MAX_H
) -> QPixmap:
    """
    Create a scaled thumbnail from a QPixmap.
    
    Args:
        pixmap: Source pixmap
        max_w: Maximum width
        max_h: Maximum height
        
    Returns:
        Scaled thumbnail pixmap
    """
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )


def is_valid_image_file(filepath: str | Path) -> bool:
    """Check if file has a valid image extension."""
    return Path(filepath).suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def generate_test_images() -> list[np.ndarray]:
    """
    Generate synthetic test images with overlapping regions.
    
    Creates a canvas with:
    - Sky gradient (top half)
    - Ground gradient (bottom half)  
    - Mountain silhouettes
    - Grid pattern on ground
    - Colored circles with labels
    - Colored rectangles
    - Cross-hatch pattern
    - Star markers
    - Numbered markers
    
    Returns:
        List of 3 numpy arrays (BGR) with ~25% overlap
    """
    logger.info("Generating %d synthetic test images...", TEST_IMAGE_COUNT)
    
    W_FULL = TEST_CANVAS_WIDTH
    H = TEST_CANVAS_HEIGHT
    OVERLAP = TEST_OVERLAP
    STRIP_W = TEST_STRIP_WIDTH
    NUM = TEST_IMAGE_COUNT
    
    rng = np.random.RandomState(TEST_RANDOM_SEED)
    
    try:
        # Create base canvas
        canvas = np.zeros((H, W_FULL, 3), dtype=np.uint8)
        
        # Sky gradient (top half)
        for y in range(H // 2):
            t = y / (H // 2)
            canvas[y, :] = (
                int(30 + 80 * t),
                int(60 + 100 * t),
                int(140 + 80 * t)
            )
        
        # Ground gradient (bottom half)
        for y in range(H // 2, H):
            t = (y - H // 2) / (H // 2)
            canvas[y, :] = (
                int(50 + 60 * t),
                int(120 + 40 * t),
                int(40 + 30 * t)
            )
        
        # Horizon line
        cv2.line(canvas, (0, H // 2), (W_FULL, H // 2), (200, 200, 180), 2)
        
        # Mountain silhouettes
        mountain_params = [
            (100, 180), (400, 140), (700, 160), (1050, 130),
            (1400, 150), (1700, 170), (2000, 155)
        ]
        for px, ph in mountain_params:
            pts = np.array(
                [[px - 120, H // 2], [px, H // 2 - ph], [px + 120, H // 2]],
                np.int32
            )
            color = (
                80 + rng.randint(0, 40),
                100 + rng.randint(0, 30),
                70 + rng.randint(0, 30)
            )
            cv2.fillPoly(canvas, [pts], color)
        
        # Ground grid - vertical lines
        for gx in range(0, W_FULL, 80):
            cv2.line(canvas, (gx, H // 2 + 5), (gx, H), (70, 110, 50), 1)
        
        # Ground grid - horizontal lines
        for gy in range(H // 2 + 20, H, 30):
            cv2.line(canvas, (0, gy), (W_FULL, gy), (70, 110, 50), 1)
        
        # Colored circles with labels
        circle_params = [
            (150, 320, 35, (0, 0, 255)),
            (350, 280, 28, (0, 200, 200)),
            (550, 350, 40, (0, 255, 0)),
            (750, 300, 25, (255, 0, 255)),
            (950, 360, 32, (255, 165, 0)),
            (1100, 290, 30, (255, 255, 0)),
            (1300, 340, 38, (200, 0, 255)),
            (1500, 310, 26, (0, 255, 200)),
            (1700, 370, 34, (100, 200, 255)),
            (1950, 280, 30, (255, 100, 100)),
        ]
        for cx, cy, r, col in circle_params:
            cv2.circle(canvas, (cx, cy), r, col, -1)
            cv2.circle(canvas, (cx, cy), r, (255, 255, 255), 2)
            cv2.putText(
                canvas, str(r), (cx - 8, cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1
            )
        
        # Colored rectangles
        rect_params = [
            (200, 380, 60, 45, (180, 60, 60)),
            (480, 370, 70, 50, (60, 60, 180)),
            (820, 385, 55, 40, (60, 180, 60)),
            (1150, 375, 65, 48, (180, 180, 60)),
            (1450, 390, 58, 42, (180, 60, 180)),
            (1800, 380, 62, 46, (60, 180, 180)),
        ]
        for rx, ry, rw, rh, col in rect_params:
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), col, -1)
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), (255, 255, 255), 2)
        
        # Cross-hatch pattern
        for x in range(0, W_FULL, 18):
            cv2.line(canvas, (x, H // 2 + 8), (x + 60, H // 2 + 68), (90, 130, 70), 1)
            cv2.line(canvas, (x + 60, H // 2 + 8), (x, H // 2 + 68), (90, 130, 70), 1)
        
        # Star markers
        star_positions = [
            (250, 250), (500, 220), (800, 240), (1100, 210),
            (1400, 235), (1700, 225), (1950, 245)
        ]
        for sx, sy in star_positions:
            cv2.drawMarker(canvas, (sx, sy), (255, 255, 255), cv2.MARKER_STAR, 20, 2)
        
        # Numbered markers along bottom
        for i in range(1, 12):
            cv2.putText(
                canvas, f"N{i}", (80 + (i - 1) * 200, H - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )
        
        # Slice into overlapping strips
        starts = [i * (STRIP_W - OVERLAP) for i in range(NUM)]
        strips = []
        
        for idx_s, s in enumerate(starts):
            e = min(s + STRIP_W, W_FULL)
            strip = canvas[:, s:e].copy()
            
            # Add subtle tint variation per strip
            tint = np.array(
                [rng.randint(-8, 9), rng.randint(-8, 9), rng.randint(-8, 9)],
                dtype=np.int16
            )
            strip = np.clip(strip.astype(np.int16) + tint, 0, 255).astype(np.uint8)
            
            # Add subtle noise
            noise = rng.randn(*strip.shape) * 3
            strip = np.clip(strip.astype(np.float64) + noise, 0, 255).astype(np.uint8)
            
            strips.append(strip)
            logger.debug(
                "Sliced strip %d at x=%d, shape=%s",
                idx_s + 1, s, strip.shape[:2]
            )
        
        # Add labels to each strip
        labels = ["LEFT", "CENTER", "RIGHT"]
        for idx, (strip, label) in enumerate(zip(strips, labels)):
            cv2.putText(
                strip, f"[{label}]", (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2
            )
            cv2.putText(
                strip, f"Image {idx + 1}/{NUM}", (15, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1
            )
            hh, ww = strip.shape[:2]
            cv2.putText(
                strip, f"{ww}x{hh}", (ww - 100, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1
            )
            cv2.rectangle(strip, (0, 0), (ww - 1, hh - 1), (180, 180, 180), 2)
        
        logger.info("Successfully generated %d test images.", NUM)
        return strips
        
    except Exception as e:
        logger.error("Failed to generate test images", exc_info=True)
        raise