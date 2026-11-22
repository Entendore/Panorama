#!/usr/bin/env python3
"""
Panorama Creator — Single-File Application
PySide6 + OpenCV panorama stitching application.

Features
--------
  • Load images via file dialog or drag & drop (remembers last directory)
  • Drag-and-drop reordering in image list
  • Delete-key shortcut to remove selected image
  • Keyboard shortcuts for move up / move down
  • Configurable stitching parameters (mode, confidence, resolution, wave correction)
  • Zoomable / pannable preview (scroll-wheel zoom, right-drag pan)
  • Built-in Test tab with 3 synthetic overlapping images
  • Auto-crop black borders from panorama result (with smart detection)
  • High-quality save via OpenCV (JPEG 95 %, PNG, TIFF, BMP) with Qt fallback
  • Stitching-time display
  • Remember last open / save directory
  • File size shown in image list items
  • Centered placeholder text in empty preview
  • Clean shutdown (waits for worker thread)
  • Dark-themed UI with styled tooltips
  • Busy-guard prevents double-stitching
  • Crop button available on both main and test tabs
"""

import sys
import time
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QProgressBar,
    QFileDialog,
    QGroupBox,
    QDoubleSpinBox,
    QSplitter,
    QToolBar,
    QTabWidget,
    QCheckBox,
    QSizePolicy,
    QSpacerItem,
    QMessageBox,
    QGraphicsView,
    QGraphicsScene,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)
from PySide6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QColor,
    QBrush,
    QFont,
    QKeySequence,
    QAction,
    QIcon,
)
from PySide6.QtCore import Qt, QSize, Signal, QPointF, QTimer, QThread


# ══════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)-8s [%(threadName)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PanoramaApp")


def _log_unhandled(exc_type, exc_value, exc_tb):
    logger.critical("Unhandled Exception", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _log_unhandled


# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════

# ── Application ──────────────────────────────────────────────────

APP_NAME: str = "Panorama Creator"
APP_VERSION: str = "0.0.0"

# ── Image Settings ───────────────────────────────────────────────

IMAGE_EXTENSIONS: set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
}
IMAGE_FILTER: str = (
    "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp);;All Files (*)"
)
SAVE_FILTER: str = "JPEG (*.jpg *.jpeg);;PNG (*.png);;TIFF (*.tiff);;BMP (*.bmp)"

# ── UI Dimensions ────────────────────────────────────────────────

THUMBNAIL_SIZE: QSize = QSize(128, 96)
THUMBNAIL_MAX_W: int = 128
THUMBNAIL_MAX_H: int = 96

TEST_THUMB_W: int = 210
TEST_THUMB_H: int = 120

IMAGE_LIST_MIN_W: int = 200
IMAGE_LIST_MAX_W: int = 280
IMAGE_LIST_ITEM_W: int = 220
IMAGE_LIST_ITEM_H: int = 112

MIN_WINDOW_W: int = 1024
MIN_WINDOW_H: int = 680
DEFAULT_WINDOW_W: int = 1280
DEFAULT_WINDOW_H: int = 820

SPLITTER_LEFT_SIZE: int = 240
SPLITTER_RIGHT_SIZE: int = 1040

# ── Test Image Config ────────────────────────────────────────────

TEST_IMAGE_COUNT: int = 3
TEST_CANVAS_WIDTH: int = 2200
TEST_CANVAS_HEIGHT: int = 500
TEST_OVERLAP: int = 300
TEST_STRIP_WIDTH: int = 800
TEST_RANDOM_SEED: int = 42

# ── Stitching Defaults ──────────────────────────────────────────

DEFAULT_STITCH_MODE: int = 0
DEFAULT_CONFIDENCE: float = 1.0
DEFAULT_REG_RESOL: float = 0.6
DEFAULT_COMP_RESOL: float = -1.0
DEFAULT_WAVE_CORRECTION: bool = True
DEFAULT_WAVE_KIND: int = 0

STITCH_CONFIDENCE_MIN: float = 0.0
STITCH_CONFIDENCE_MAX: float = 1.0
STITCH_CONFIDENCE_STEP: float = 0.05
STITCH_REG_RESOL_MIN: float = 0.1
STITCH_REG_RESOL_MAX: float = 1.0
STITCH_REG_RESOL_STEP: float = 0.1
STITCH_COMP_RESOL_MIN: float = -1.0
STITCH_COMP_RESOL_MAX: float = 1.0
STITCH_COMP_RESOL_STEP: float = 0.1

# ── Progress Bar ─────────────────────────────────────────────────

PROGRESS_TICK_MS: int = 40
PROGRESS_STEP: int = 2

# ── Zoom Factors ─────────────────────────────────────────────────

ZOOM_IN_FACTOR: float = 1.25
ZOOM_OUT_FACTOR: float = 0.8
WHEEL_ZOOM_FACTOR: float = 1.15
WHEEL_ZOOM_OUT_FACTOR: float = 1.0 / 1.15

# ── Auto-Crop ────────────────────────────────────────────────────

CROP_BLACK_THRESHOLD: int = 1
CROP_BORDER_DETECT_THRESHOLD: int = 5
CROP_BORDER_MARGIN_RATIO: float = 0.05
CROP_BORDER_MIN_RATIO: float = 0.25

# ── Status Bar ───────────────────────────────────────────────────

STATUS_TIMEOUT_SHORT: int = 3000
STATUS_TIMEOUT_MEDIUM: int = 5000
STATUS_TIMEOUT_LONG: int = 10000

# ── Save Quality ─────────────────────────────────────────────────

JPEG_QUALITY: int = 95
PNG_COMPRESSION: int = 3

# ── Stylesheets ──────────────────────────────────────────────────

APPLICATION_STYLE = """
    QMainWindow {
        background: #1e1e1e;
    }
    QWidget {
        color: #ddd;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    QGroupBox {
        border: 1px solid #555;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 14px;
        color: #ccc;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
    QPushButton {
        background: #3a3a3a;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 4px 10px;
        color: #ddd;
    }
    QPushButton:hover {
        background: #4a4a4a;
    }
    QPushButton:pressed {
        background: #2a2a2a;
    }
    QPushButton:disabled {
        color: #666;
        background: #333;
    }
    QPushButton#stitchBtn {
        background: #3a6a3a;
        font-size: 14px;
        font-weight: bold;
        border: none;
        border-radius: 6px;
        color: #fff;
    }
    QPushButton#stitchBtn:hover {
        background: #4a8a4a;
    }
    QPushButton#stitchBtn:pressed {
        background: #2a5a2a;
    }
    QPushButton#stitchBtn:disabled {
        background: #444;
        color: #777;
    }
    QPushButton#cropBtn {
        background: #5a4a2a;
        border: 1px solid #887744;
        border-radius: 4px;
        padding: 4px 12px;
        color: #eedd88;
        font-weight: bold;
    }
    QPushButton#cropBtn:hover {
        background: #6a5a3a;
    }
    QPushButton#cropBtn:disabled {
        background: #333;
        color: #666;
        border-color: #555;
    }
    QComboBox {
        background: #3a3a3a;
        border: 1px solid #555;
        border-radius: 3px;
        padding: 3px 8px;
        color: #ddd;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox QAbstractItemView {
        background: #3a3a3a;
        color: #ddd;
        selection-background-color: #4a6fa5;
    }
    QDoubleSpinBox, QSpinBox {
        background: #3a3a3a;
        border: 1px solid #555;
        border-radius: 3px;
        padding: 3px 6px;
        color: #ddd;
    }
    QProgressBar {
        border: 1px solid #555;
        border-radius: 3px;
        background: #2a2a2a;
        text-align: center;
        color: #ddd;
    }
    QProgressBar::chunk {
        background: #4a6fa5;
        border-radius: 2px;
    }
    QToolBar {
        background: #2a2a2a;
        border-bottom: 1px solid #444;
        spacing: 6px;
        padding: 3px;
    }
    QMenuBar {
        background: #2a2a2a;
        border-bottom: 1px solid #444;
        color: #ddd;
    }
    QMenuBar::item:selected {
        background: #4a4a4a;
    }
    QMenu {
        background: #2a2a2a;
        border: 1px solid #555;
        color: #ddd;
    }
    QMenu::item:selected {
        background: #4a6fa5;
    }
    QStatusBar {
        background: #252525;
        border-top: 1px solid #444;
        color: #aaa;
    }
    QCheckBox {
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #555;
        border-radius: 3px;
        background: #3a3a3a;
    }
    QCheckBox::indicator:checked {
        background: #4a6fa5;
        border-color: #6a9fd5;
    }
    QLabel {
        background: transparent;
    }
    QToolTip {
        background: #2a2a2a;
        color: #ddd;
        border: 1px solid #555;
        padding: 4px;
    }
    QSplitter::handle {
        background: #444;
        width: 3px;
    }
    QSplitter::handle:hover {
        background: #666;
    }
"""

TAB_WIDGET_STYLE = """
    QTabWidget::pane {
        border: 1px solid #555;
        border-radius: 4px;
        background: #1e1e1e;
    }
    QTabBar::tab {
        background: #2a2a2a;
        color: #aaa;
        padding: 8px 20px;
        border: 1px solid #555;
        border-bottom: none;
        border-radius: 6px 6px 0 0;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background: #1e1e1e;
        color: #fff;
        border-color: #4a6fa5;
    }
    QTabBar::tab:hover {
        color: #ddd;
    }
"""

IMAGE_LIST_STYLE = """
    QListWidget {
        background: #2d2d2d;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 4px;
    }
    QListWidget::item {
        background: #383838;
        border: 1px solid #555;
        border-radius: 3px;
        padding: 4px;
        margin: 2px;
    }
    QListWidget::item:selected {
        background: #4a6fa5;
        border-color: #6a9fd5;
    }
    QListWidget::item:hover {
        background: #404040;
    }
"""

TEST_THUMB_STYLE = """
    QPushButton {
        background: #383838;
        border: 2px solid #555;
        border-radius: 6px;
    }
    QPushButton:hover {
        border-color: #88aacc;
    }
    QPushButton:checked {
        border-color: #4a9fd5;
        background: #3a5570;
    }
"""


# ══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════


def cv_to_qpixmap(cv_img: np.ndarray | None) -> QPixmap:
    """
    Convert an OpenCV BGR or grayscale image to QPixmap.

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

        # Convert BGR → RGB
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape

        # Create QImage from contiguous data
        rgb_contiguous = np.ascontiguousarray(rgb)
        bytes_per_line = ch * w
        qimg = QImage(
            rgb_contiguous.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )

        # Deep copy to detach from numpy array
        return QPixmap.fromImage(qimg.copy())

    except Exception as exc:
        logger.error("cv_to_qpixmap failed: %s", exc, exc_info=True)
        return QPixmap()


def make_thumbnail(
    pixmap: QPixmap,
    max_w: int = THUMBNAIL_MAX_W,
    max_h: int = THUMBNAIL_MAX_H,
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
        Qt.TransformationMode.SmoothTransformation,
    )


def is_valid_image_file(filepath: str | Path) -> bool:
    """Check if file has a valid image extension."""
    return Path(filepath).suffix.lower() in IMAGE_EXTENSIONS


def auto_crop_black_borders(
    cv_img: np.ndarray | None,
    threshold: int = CROP_BLACK_THRESHOLD,
) -> np.ndarray | None:
    """
    Remove black / near-black borders from a stitched panorama.

    Args:
        cv_img: OpenCV BGR image
        threshold: Pixel intensity threshold for "black" (0-255)

    Returns:
        Cropped image, or None if input is None
    """
    if cv_img is None:
        return None

    # Convert to grayscale for analysis
    if len(cv_img.shape) == 3:
        ch = cv_img.shape[2]
        if ch == 4:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2GRAY)
        else:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv_img

    # Threshold to find non-black pixels
    _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    coords = cv2.findNonZero(thresh)

    if coords is None:
        # Entirely black — return as-is
        return cv_img

    x, y, w, h = cv2.boundingRect(coords)

    # Add a 1-pixel pad to avoid cutting right at the edge
    pad = 1
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(cv_img.shape[1], x + w + pad)
    y1 = min(cv_img.shape[0], y + h + pad)

    return cv_img[y0:y1, x0:x1].copy()


def has_black_borders(
    cv_img: np.ndarray | None,
    threshold: int = CROP_BORDER_DETECT_THRESHOLD,
    margin_ratio: float = CROP_BORDER_MARGIN_RATIO,
    min_ratio: float = CROP_BORDER_MIN_RATIO,
) -> bool:
    """
    Quick check whether an image has significant black borders.

    Args:
        cv_img: OpenCV BGR image
        threshold: Pixel intensity threshold for "black"
        margin_ratio: Fraction of image dimension to check at each edge
        min_ratio: Minimum fraction of black pixels in a margin to count as a border

    Returns:
        True if a significant black border is detected
    """
    if cv_img is None:
        return False

    # Convert to grayscale
    gray = (
        cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        if len(cv_img.shape) == 3
        else cv_img
    )

    h, w = gray.shape
    margin = max(2, int(min(h, w) * margin_ratio))

    # Check each edge for percentage of black pixels
    top_ratio = np.mean(gray[:margin, :] < threshold)
    bottom_ratio = np.mean(gray[-margin:, :] < threshold)
    left_ratio = np.mean(gray[:, :margin] < threshold)
    right_ratio = np.mean(gray[:, -margin:] < threshold)

    return max(top_ratio, bottom_ratio, left_ratio, right_ratio) > min_ratio


def _human_size(size_bytes: int) -> str:
    """Return a human-readable file-size string."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"


def generate_test_images() -> list[np.ndarray]:
    """
    Generate synthetic test images with overlapping regions.

    Creates a canvas with sky/ground gradients, mountain silhouettes,
    coloured circles/rectangles, grid patterns, and numbered markers.
    Three overlapping strips are sliced from the canvas with ~25% overlap
    and slight tint/noise variation per strip.

    Returns:
        List of 3 numpy arrays (BGR) with overlapping content
    """
    logger.info("Generating %d synthetic test images …", TEST_IMAGE_COUNT)

    W_FULL = TEST_CANVAS_WIDTH
    H = TEST_CANVAS_HEIGHT
    OVERLAP = TEST_OVERLAP
    STRIP_W = TEST_STRIP_WIDTH
    NUM = TEST_IMAGE_COUNT

    rng = np.random.RandomState(TEST_RANDOM_SEED)

    try:
        # ── Create base canvas ──
        canvas = np.zeros((H, W_FULL, 3), dtype=np.uint8)

        # Sky gradient (top half)
        for y in range(H // 2):
            t = y / (H // 2)
            canvas[y, :] = (
                int(30 + 80 * t),
                int(60 + 100 * t),
                int(140 + 80 * t),
            )

        # Ground gradient (bottom half)
        for y in range(H // 2, H):
            t = (y - H // 2) / (H // 2)
            canvas[y, :] = (
                int(50 + 60 * t),
                int(120 + 40 * t),
                int(40 + 30 * t),
            )

        # Horizon line
        cv2.line(canvas, (0, H // 2), (W_FULL, H // 2), (200, 200, 180), 2)

        # Mountain silhouettes
        mountain_params = [
            (100, 180),
            (400, 140),
            (700, 160),
            (1050, 130),
            (1400, 150),
            (1700, 170),
            (2000, 155),
        ]
        for px, ph in mountain_params:
            pts = np.array(
                [[px - 120, H // 2], [px, H // 2 - ph], [px + 120, H // 2]],
                np.int32,
            )
            color = (
                80 + rng.randint(0, 40),
                100 + rng.randint(0, 30),
                70 + rng.randint(0, 30),
            )
            cv2.fillPoly(canvas, [pts], color)

        # Ground grid — vertical lines
        for gx in range(0, W_FULL, 80):
            cv2.line(canvas, (gx, H // 2 + 5), (gx, H), (70, 110, 50), 1)

        # Ground grid — horizontal lines
        for gy in range(H // 2 + 20, H, 30):
            cv2.line(canvas, (0, gy), (W_FULL, gy), (70, 110, 50), 1)

        # Coloured circles with labels
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
                canvas,
                str(r),
                (cx - 8, cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
            )

        # Coloured rectangles
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
            cv2.line(
                canvas, (x, H // 2 + 8), (x + 60, H // 2 + 68), (90, 130, 70), 1
            )
            cv2.line(
                canvas, (x + 60, H // 2 + 8), (x, H // 2 + 68), (90, 130, 70), 1
            )

        # Star markers
        star_positions = [
            (250, 250),
            (500, 220),
            (800, 240),
            (1100, 210),
            (1400, 235),
            (1700, 225),
            (1950, 245),
        ]
        for sx, sy in star_positions:
            cv2.drawMarker(
                canvas, (sx, sy), (255, 255, 255), cv2.MARKER_STAR, 20, 2
            )

        # Numbered markers along bottom
        for i in range(1, 12):
            cv2.putText(
                canvas,
                f"N{i}",
                (80 + (i - 1) * 200, H - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

        # ── Slice into overlapping strips ──
        starts = [i * (STRIP_W - OVERLAP) for i in range(NUM)]
        strips: list[np.ndarray] = []

        for idx_s, s in enumerate(starts):
            e = min(s + STRIP_W, W_FULL)
            strip = canvas[:, s:e].copy()

            # Add subtle tint variation per strip
            tint = np.array(
                [
                    rng.randint(-8, 9),
                    rng.randint(-8, 9),
                    rng.randint(-8, 9),
                ],
                dtype=np.int16,
            )
            strip = np.clip(strip.astype(np.int16) + tint, 0, 255).astype(np.uint8)

            # Add subtle noise
            noise = rng.randn(*strip.shape) * 3
            strip = np.clip(strip.astype(np.float64) + noise, 0, 255).astype(
                np.uint8
            )

            strips.append(strip)
            logger.debug(
                "Sliced strip %d at x=%d, shape=%s",
                idx_s + 1,
                s,
                strip.shape[:2],
            )

        # ── Add labels to each strip ──
        labels = ["LEFT", "CENTER", "RIGHT"]
        for idx, (strip, label) in enumerate(zip(strips, labels)):
            cv2.putText(
                strip,
                f"[{label}]",
                (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                strip,
                f"Image {idx + 1}/{NUM}",
                (15, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1,
            )
            hh, ww = strip.shape[:2]
            cv2.putText(
                strip,
                f"{ww}x{hh}",
                (ww - 100, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (180, 180, 180),
                1,
            )
            cv2.rectangle(strip, (0, 0), (ww - 1, hh - 1), (180, 180, 180), 2)

        logger.info("Successfully generated %d test images.", NUM)
        return strips

    except Exception:
        logger.error("Failed to generate test images", exc_info=True)
        raise


# ══════════════════════════════════════════════════════════════════
#  CUSTOM WIDGETS
# ══════════════════════════════════════════════════════════════════


class PanoramaView(QGraphicsView):
    """
    Graphics view with zoom and pan capabilities for displaying images.

    Features:
    - Scroll wheel zoom (centered on cursor)
    - Right-click / middle-click drag to pan
    - Fit to view and actual size methods
    - Centered placeholder text when no image loaded
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._pixmap_item = None
        self._is_panning = False
        self._pan_start = QPointF()

        # Rendering settings
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor(42, 42, 42)))

        # Scene setup
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._show_placeholder()

    # ── public ──────────────────────────────────────────────

    def set_pixmap(self, pixmap: QPixmap) -> None:
        """
        Display a pixmap in the view.

        Args:
            pixmap: QPixmap to display, or null/None to show placeholder
        """
        self._scene.clear()
        self._pixmap_item = None

        if pixmap and not pixmap.isNull():
            try:
                self._pixmap_item = self._scene.addPixmap(pixmap)
                self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
                self.fitInView(
                    self._scene.sceneRect(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                )
                logger.debug("Displayed pixmap %dx%d", pixmap.width(), pixmap.height())
            except Exception:
                logger.error("Error setting pixmap in scene", exc_info=True)
                self._show_placeholder("Error displaying image")
        else:
            self._show_placeholder()

    def has_image(self) -> bool:
        """Check if an image is currently displayed."""
        return self._pixmap_item is not None

    def fit_to_view(self) -> None:
        """Fit the image to the view."""
        if self._pixmap_item:
            self.fitInView(
                self._scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    def actual_size(self) -> None:
        """Reset zoom to show actual pixel size."""
        if self._pixmap_item:
            self.resetTransform()

    def zoom_in(self) -> None:
        """Zoom in by fixed factor."""
        if self._pixmap_item:
            self.scale(ZOOM_IN_FACTOR, ZOOM_IN_FACTOR)

    def zoom_out(self) -> None:
        """Zoom out by fixed factor."""
        if self._pixmap_item:
            self.scale(ZOOM_OUT_FACTOR, ZOOM_OUT_FACTOR)

    # ── private ─────────────────────────────────────────────

    def _show_placeholder(self, text: str | None = None) -> None:
        """Display centred placeholder text when no image is loaded."""
        self._scene.clear()
        default_text = (
            "Add images and click  ▶ Stitch  to create a panorama\n\n"
            "• Scroll wheel → zoom\n"
            "• Right-drag → pan\n"
            "• Drop image files on this window"
        )
        display_text = text or default_text

        scene_w, scene_h = 800, 500
        txt = self._scene.addText(display_text, QFont("Segoe UI", 12))
        txt.setDefaultTextColor(QColor(140, 140, 140))
        txt.setTextWidth(scene_w - 120)
        br = txt.boundingRect()
        txt.setPos((scene_w - br.width()) / 2, (scene_h - br.height()) / 2)
        self._scene.setSceneRect(0, 0, scene_w, scene_h)

    # ── events ──────────────────────────────────────────────

    def wheelEvent(self, event) -> None:  # noqa: N802
        """Handle scroll wheel for zooming."""
        if not self._pixmap_item:
            return
        factor = (
            WHEEL_ZOOM_FACTOR
            if event.angleDelta().y() > 0
            else WHEEL_ZOOM_OUT_FACTOR
        )
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        """Start panning on right / middle click."""
        if event.button() in (
            Qt.MouseButton.RightButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        """Handle panning movement."""
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        """Stop panning."""
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class ImageListWidget(QListWidget):
    """
    List widget for displaying loaded images with thumbnails.

    Features:
    - Drag-and-drop reordering
    - Single selection
    - Custom styling
    - Emits signals when order changes or delete is requested
    - Shows filename, dimensions, and file size
    """

    order_changed = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setIconSize(THUMBNAIL_SIZE)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSpacing(4)
        self.setMinimumWidth(IMAGE_LIST_MIN_W)
        self.setMaximumWidth(IMAGE_LIST_MAX_W)
        self.setStyleSheet(IMAGE_LIST_STYLE)

        # Connect internal move signal
        self.model().rowsMoved.connect(lambda *_: self.order_changed.emit())

    # ── public ──────────────────────────────────────────────

    def add_image_item(
        self,
        filepath: str,
        cv_img: np.ndarray,
        pixmap: QPixmap,
    ) -> None:
        """
        Add an image item to the list.

        Args:
            filepath: Path to the image file
            cv_img: OpenCV image array (for dimensions)
            pixmap: QPixmap of the image
        """
        item = QListWidgetItem()
        item.setIcon(make_thumbnail(pixmap))

        name = Path(filepath).name
        h, w = cv_img.shape[:2]

        # Try to get file size
        try:
            size_str = _human_size(Path(filepath).stat().st_size)
        except OSError:
            size_str = ""

        item.setText(f"{name}\n{w}×{h}  {size_str}")
        item.setToolTip(f"{filepath}\n{w}×{h}  {size_str}")
        item.setData(Qt.ItemDataRole.UserRole, filepath)
        item.setSizeHint(QSize(IMAGE_LIST_ITEM_W, IMAGE_LIST_ITEM_H))

        self.addItem(item)

    def get_ordered_paths(self) -> list[str]:
        """Get list of filepaths in current display order."""
        return [
            self.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.count())
        ]

    # ── keyboard ────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:  # noqa: N802
        """Handle Delete / Backspace to remove selected image."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


# ══════════════════════════════════════════════════════════════════
#  STITCH WORKER
# ══════════════════════════════════════════════════════════════════


class StitchWorker(QThread):
    """
    Worker thread for panorama stitching.

    Runs OpenCV stitching in a separate thread to keep the UI responsive.

    Signals:
        done: Emitted when stitching completes with (success, message, panorama_image)
    """

    done = Signal(bool, str, object)

    # OpenCV Stitcher status codes and messages
    STITCH_ERRORS: dict[int, str] = {
        cv2.Stitcher_ERR_NEED_MORE_IMGS: (
            "Need more images or insufficient overlap."
        ),
        cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL: (
            "Homography estimation failed — try images with more overlap / features."
        ),
        cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL: (
            "Camera parameter adjustment failed."
        ),
    }

    def __init__(self, images: list[np.ndarray], params: dict[str, Any]):
        """
        Initialize the stitch worker.

        Args:
            images: List of OpenCV images to stitch (BGR format)
            params: Dictionary of stitching parameters
                - mode: "panorama" or "scans"
                - conf: Confidence threshold (0.0-1.0)
                - reg_res: Registration resolution
                - comp_res: Compositing resolution (-1 for full)
                - wave: Enable wave correction
                - wave_kind: "horizontal" or "vertical"
        """
        super().__init__()
        self.images = images
        self.params = params

    def run(self) -> None:
        """Execute the stitching operation."""
        logger.info("StitchWorker started. Parameters: %s", self.params)

        try:
            # Create stitcher with selected mode
            mode = (
                cv2.Stitcher_PANORAMA
                if self.params["mode"] == "panorama"
                else cv2.Stitcher_SCANS
            )
            stitcher = cv2.Stitcher.create(mode)

            # Configure stitcher parameters
            stitcher.setRegistrationResol(self.params["reg_res"])
            stitcher.setSeamEstimationResol(0.1)
            stitcher.setCompositingResol(self.params["comp_res"])
            stitcher.setPanoConfidenceThresh(self.params["conf"])
            stitcher.setWaveCorrection(self.params["wave"])

            # Set wave correction kind (API may not exist in all OpenCV versions)
            if self.params["wave"]:
                try:
                    kind = (
                        cv2.detail.WAVE_CORRECT_HORIZ
                        if self.params["wave_kind"] == "horizontal"
                        else cv2.detail.WAVE_CORRECT_VERT
                    )
                    stitcher.setWaveCorrectKind(kind)
                except AttributeError:
                    logger.warning(
                        "setWaveCorrectKind not available in this OpenCV version. "
                        "Skipping."
                    )

            # Execute stitching
            logger.debug(
                "Calling cv2.Stitcher.stitch() with %d images …",
                len(self.images),
            )
            status, panorama = stitcher.stitch(self.images)

            # Handle result
            if status == cv2.Stitcher_OK:
                h, w = panorama.shape[:2]
                logger.info("Stitching SUCCESS. Output size: %dx%d", w, h)
                self.done.emit(True, "OK", panorama)
            else:
                error_msg = self.STITCH_ERRORS.get(
                    status, f"Unknown OpenCV Stitcher error code: {status}"
                )
                logger.warning(
                    "Stitching FAILED. Status: %d - %s", status, error_msg
                )
                self.done.emit(False, error_msg, None)

        except Exception as exc:
            logger.error("Exception inside StitchWorker", exc_info=True)
            self.done.emit(False, f"Worker Exception: {exc}", None)


# ══════════════════════════════════════════════════════════════════
#  TEST TAB WIDGET
# ══════════════════════════════════════════════════════════════════


class TestTabWidget(QWidget):
    """
    Test tab with 3 programmatically generated overlapping images.

    Signals:
        request_stitch: Emitted with list of images when stitch is requested
        request_crop: Emitted when crop borders is requested
    """

    request_stitch = Signal(list)
    request_crop = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._test_imgs: list[np.ndarray] = []
        self._test_pixmaps: list[QPixmap] = []
        self._pano_pixmap: QPixmap | None = None
        self._current_idx: int = -1

        self._build_ui()
        self._generate()

    # ── UI construction ─────────────────────────────────────

    def _build_ui(self) -> None:
        """Build the test tab UI."""
        outer = QVBoxLayout(self)
        outer.setSpacing(8)

        # Description
        desc = QLabel(
            "This tab generates 3 synthetic test images with ~25% overlap "
            "and rich features.\n"
            "Click any thumbnail to preview it, then press the stitch button."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#aaa;padding:4px 8px;")
        outer.addWidget(desc)

        # Thumbnail buttons
        thumb_box = QHBoxLayout()
        thumb_box.setSpacing(12)
        self._thumb_btns: list[QPushButton] = []

        for i in range(3):
            btn = QPushButton()
            btn.setFixedSize(220, 130)
            btn.setCheckable(True)
            btn.setStyleSheet(TEST_THUMB_STYLE)
            btn.clicked.connect(lambda checked, idx=i: self._select(idx))
            thumb_box.addWidget(btn)
            self._thumb_btns.append(btn)

        thumb_box.addStretch()
        outer.addLayout(thumb_box)

        # Info label
        self._lbl_info = QLabel("Generating test images …")
        self._lbl_info.setStyleSheet("color:#999;padding:0 8px;")
        outer.addWidget(self._lbl_info)

        # Preview view
        self._view = PanoramaView()
        outer.addWidget(self._view, stretch=1)

        # Zoom + crop controls
        zb = QHBoxLayout()

        zoom_actions = [
            ("Fit", self._view.fit_to_view),
            ("100%", self._view.actual_size),
            ("+", self._view.zoom_in),
            ("−", self._view.zoom_out),
        ]
        for text, slot in zoom_actions:
            b = QPushButton(text)
            b.setFixedSize(42, 28)
            b.clicked.connect(slot)
            zb.addWidget(b)

        zb.addSpacing(12)

        # Crop button (on test tab too)
        self._btn_crop = QPushButton("✂ Crop")
        self._btn_crop.setObjectName("cropBtn")
        self._btn_crop.setFixedHeight(28)
        self._btn_crop.setEnabled(False)
        self._btn_crop.setToolTip(
            "Remove black borders from the stitched panorama"
        )
        self._btn_crop.clicked.connect(self.request_crop.emit)
        zb.addWidget(self._btn_crop)

        zb.addStretch()

        self._lbl_size = QLabel("")
        self._lbl_size.setStyleSheet("color:#999;")
        zb.addWidget(self._lbl_size)
        outer.addLayout(zb)

        # Stitch button
        self._btn_stitch = QPushButton("▶  Stitch 3 Test Images")
        self._btn_stitch.setFixedHeight(42)
        self._btn_stitch.setObjectName("stitchBtn")
        self._btn_stitch.clicked.connect(self._do_stitch)
        outer.addWidget(self._btn_stitch)

    # ── internals ───────────────────────────────────────────

    def _generate(self) -> None:
        """Generate and display test images."""
        try:
            self._test_imgs = generate_test_images()
            self._test_pixmaps = [cv_to_qpixmap(img) for img in self._test_imgs]

            for px, btn in zip(self._test_pixmaps, self._thumb_btns):
                thumb = make_thumbnail(px, TEST_THUMB_W, TEST_THUMB_H)
                btn.setIcon(thumb)
                btn.setIconSize(thumb.size())
                btn.setText("")

            self._lbl_info.setText("Click a thumbnail to preview.")
            logger.info("Test tab UI populated successfully.")

        except Exception:
            logger.critical("Failed to populate test tab", exc_info=True)
            self._lbl_info.setText(
                "ERROR: Failed to generate test images. Check terminal logs."
            )

    def _select(self, idx: int) -> None:
        """Select and preview a test image."""
        for i, b in enumerate(self._thumb_btns):
            b.setChecked(i == idx)

        self._current_idx = idx
        self._pano_pixmap = None
        self._view.set_pixmap(self._test_pixmaps[idx])

        h, w = self._test_imgs[idx].shape[:2]
        self._lbl_info.setText(f"Preview: Image {idx + 1}")
        self._lbl_size.setText(f"{w}×{h}")

    def _do_stitch(self) -> None:
        """Request stitching of test images."""
        self.request_stitch.emit(self._test_imgs)

    # ── public ──────────────────────────────────────────────

    def show_panorama(self, pixmap: QPixmap) -> None:
        """Display the stitched panorama result."""
        self._pano_pixmap = pixmap
        self._view.set_pixmap(pixmap)

        for b in self._thumb_btns:
            b.setChecked(False)

        self._current_idx = -1
        self._lbl_info.setText("Result: stitched panorama from 3 test images")
        self._lbl_size.setText(f"{pixmap.width()}×{pixmap.height()}")


# ══════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════


class MainWindow(QMainWindow):
    """
    Main application window with panorama stitching functionality.

    Provides:
    - Image loading via file dialog or drag & drop
    - Drag-reorderable image list with thumbnails
    - Configurable stitching parameters
    - Zoomable / pannable preview
    - Auto-crop of black borders
    - High-quality save via OpenCV
    - Built-in test images tab
    """

    def __init__(self):
        super().__init__()
        logger.info("Initializing MainWindow …")

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(MIN_WINDOW_W, MIN_WINDOW_H)
        self.resize(DEFAULT_WINDOW_W, DEFAULT_WINDOW_H)

        # ── State ──
        self._paths: list[str] = []
        self._cv_imgs: dict[str, np.ndarray] = {}
        self._pixmaps: dict[str, QPixmap] = {}

        self._panorama_cv: np.ndarray | None = None
        self._panorama_pixmap: QPixmap | None = None
        self._stitch_source: str = "main"
        self._stitch_start: float = 0.0

        self._worker: StitchWorker | None = None
        self._active_pbar: QProgressBar | None = None
        self._prog_val: int = 0
        self._prog_dir: int = 1

        # Remember directories
        self._last_open_dir: Path = Path.home()
        self._last_save_dir: Path = Path.home()

        # Progress timer
        self._prog_timer = QTimer(self)
        self._prog_timer.timeout.connect(self._tick_progress)

        try:
            self._build_ui()
            self._build_toolbar()
            self._build_menu()
            self._connect_signals()
            self._apply_theme()
            self.setAcceptDrops(True)
            logger.info("MainWindow initialization complete.")
        except Exception:
            logger.critical("Failed to build UI", exc_info=True)
            raise

    # ════════════════════ UI Construction ═══════════════════

    def _build_ui(self) -> None:
        """Build the main UI layout."""
        root = QWidget()
        self.setCentralWidget(root)

        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(6)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(TAB_WIDGET_STYLE)

        # Main tab
        main_tab = self._build_main_tab()
        self._tabs.addTab(main_tab, "📷  Panorama Creator")

        # Test tab
        self._test_tab = TestTabWidget()
        self._test_tab.request_stitch.connect(self._stitch_test)
        self._test_tab.request_crop.connect(self._crop_borders)
        self._tabs.addTab(self._test_tab, "🧪  Test (3 Images)")

        vbox.addWidget(self._tabs)

        # Test progress bar (outside tabs so it stays visible on both)
        self.pbar_test = QProgressBar()
        self.pbar_test.setFixedHeight(20)
        self.pbar_test.setVisible(False)
        vbox.addWidget(self.pbar_test)

        self.statusBar().showMessage(
            "Ready — switch to the Test tab for a quick try!"
        )

    def _build_main_tab(self) -> QWidget:
        """Build the main panorama creator tab."""
        main_tab = QWidget()
        ml = QVBoxLayout(main_tab)
        ml.setContentsMargins(4, 4, 4, 4)
        ml.setSpacing(6)

        # Splitter layout
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel — image list
        left = self._build_left_panel()
        splitter.addWidget(left)

        # Right panel — preview and controls
        right = self._build_right_panel()
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([SPLITTER_LEFT_SIZE, SPLITTER_RIGHT_SIZE])

        ml.addWidget(splitter)
        return main_tab

    def _build_left_panel(self) -> QWidget:
        """Build the left panel with image list."""
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(4)

        # Header
        header = QLabel("Images  (drag to reorder)")
        header.setStyleSheet("font-weight:bold;color:#ccc;padding:4px;")
        ll.addWidget(header)

        # Image list
        self.img_list = ImageListWidget()
        ll.addWidget(self.img_list)

        # Control buttons
        row = QHBoxLayout()
        self.btn_up = QPushButton("▲ Up")
        self.btn_dn = QPushButton("▼ Down")
        self.btn_rm = QPushButton("✕ Remove")
        self.btn_clr = QPushButton("Clear All")

        for b in (self.btn_up, self.btn_dn, self.btn_rm, self.btn_clr):
            b.setFixedHeight(30)
            row.addWidget(b)

        ll.addLayout(row)

        # Count label
        self.lbl_cnt = QLabel("0 images")
        self.lbl_cnt.setStyleSheet("color:#999;padding:2px;")
        ll.addWidget(self.lbl_cnt)

        return left

    def _build_right_panel(self) -> QWidget:
        """Build the right panel with preview and controls."""
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)

        # Preview view
        self.view = PanoramaView()
        rl.addWidget(self.view, stretch=1)

        # Zoom + crop controls
        zb = QHBoxLayout()
        self.btn_fit = QPushButton("Fit")
        self.btn_100 = QPushButton("100%")
        self.btn_zi = QPushButton("+")
        self.btn_zo = QPushButton("−")

        for b in (self.btn_fit, self.btn_100, self.btn_zi, self.btn_zo):
            b.setFixedSize(42, 28)
            zb.addWidget(b)

        zb.addSpacing(12)

        # Crop borders button
        self.btn_crop = QPushButton("✂ Crop Borders")
        self.btn_crop.setObjectName("cropBtn")
        self.btn_crop.setFixedHeight(28)
        self.btn_crop.setEnabled(False)
        self.btn_crop.setToolTip(
            "Remove black borders from the stitched panorama"
        )
        zb.addWidget(self.btn_crop)

        zb.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding))
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color:#999;")
        zb.addWidget(self.lbl_info)
        rl.addLayout(zb)

        # Stitching options
        og = self._build_options_group()
        rl.addWidget(og)

        # Progress bar
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(20)
        self.pbar.setVisible(False)
        rl.addWidget(self.pbar)

        # Stitch button
        self.btn_stitch = QPushButton("▶  Stitch Panorama")
        self.btn_stitch.setFixedHeight(42)
        self.btn_stitch.setObjectName("stitchBtn")
        self.btn_stitch.setEnabled(False)
        rl.addWidget(self.btn_stitch)

        return right

    def _build_options_group(self) -> QGroupBox:
        """Build the stitching options group box."""
        og = QGroupBox("Stitching Options")
        ol = QHBoxLayout(og)
        ol.setSpacing(14)

        # Mode combo
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Panorama", "Scans"])
        self.combo_mode.setFixedWidth(120)
        self.combo_mode.setCurrentIndex(DEFAULT_STITCH_MODE)
        ol.addLayout(self._labeled("Mode:", self.combo_mode))

        # Confidence spin
        self.spin_conf = QDoubleSpinBox()
        self.spin_conf.setRange(STITCH_CONFIDENCE_MIN, STITCH_CONFIDENCE_MAX)
        self.spin_conf.setValue(DEFAULT_CONFIDENCE)
        self.spin_conf.setSingleStep(STITCH_CONFIDENCE_STEP)
        self.spin_conf.setFixedWidth(100)
        ol.addLayout(self._labeled("Confidence:", self.spin_conf))

        # Registration resolution spin
        self.spin_reg = QDoubleSpinBox()
        self.spin_reg.setRange(STITCH_REG_RESOL_MIN, STITCH_REG_RESOL_MAX)
        self.spin_reg.setValue(DEFAULT_REG_RESOL)
        self.spin_reg.setSingleStep(STITCH_REG_RESOL_STEP)
        self.spin_reg.setFixedWidth(100)
        ol.addLayout(self._labeled("Reg. Resol:", self.spin_reg))

        # Compositing resolution spin
        self.spin_comp = QDoubleSpinBox()
        self.spin_comp.setRange(STITCH_COMP_RESOL_MIN, STITCH_COMP_RESOL_MAX)
        self.spin_comp.setValue(DEFAULT_COMP_RESOL)
        self.spin_comp.setSingleStep(STITCH_COMP_RESOL_STEP)
        self.spin_comp.setFixedWidth(100)
        self.spin_comp.setSpecialValueText("Full (−1)")
        ol.addLayout(self._labeled("Comp. Resol:", self.spin_comp))

        # Wave correction
        wv = QVBoxLayout()
        self.chk_wave = QCheckBox("Wave Correction")
        self.chk_wave.setChecked(DEFAULT_WAVE_CORRECTION)
        wv.addWidget(self.chk_wave)

        self.combo_wk = QComboBox()
        self.combo_wk.addItems(["Horizontal", "Vertical"])
        self.combo_wk.setFixedWidth(120)
        self.combo_wk.setCurrentIndex(DEFAULT_WAVE_KIND)
        wv.addWidget(self.combo_wk)
        ol.addLayout(wv)

        ol.addStretch()
        return og

    @staticmethod
    def _labeled(text: str, widget: QWidget) -> QVBoxLayout:
        """Create a labeled widget layout."""
        v = QVBoxLayout()
        v.addWidget(QLabel(text))
        v.addWidget(widget)
        return v

    # ── toolbar ─────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        """Build the main toolbar."""
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)

        self._add_toolbar_action(tb, "📁 Add", self.add_images, "Ctrl+O")
        tb.addSeparator()
        self._add_toolbar_action(
            tb, "▶ Stitch", self._stitch_from_active_tab, "Ctrl+G"
        )
        tb.addSeparator()
        self._add_toolbar_action(tb, "💾 Save", self.save, "Ctrl+Shift+S")
        tb.addSeparator()
        self._add_toolbar_action(tb, "🗑 Clear", self.clear_all)

    @staticmethod
    def _add_toolbar_action(
        toolbar: QToolBar,
        text: str,
        slot,
        shortcut: str | None = None,
    ) -> QAction:
        """Add an action to a toolbar."""
        action = QAction(text, toolbar)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        toolbar.addAction(action)
        return action

    # ── menu bar ────────────────────────────────────────────

    def _build_menu(self) -> None:
        """Build the menu bar."""
        mb = self.menuBar()

        # File menu
        fm = mb.addMenu("File")
        fm.addAction("Add Images …", self.add_images, "Ctrl+O")
        fm.addSeparator()
        fm.addAction("Save Panorama …", self.save, "Ctrl+Shift+S")
        fm.addSeparator()
        fm.addAction("Exit", self.close, "Ctrl+Q")

        # Edit menu
        em = mb.addMenu("Edit")
        em.addAction("Remove Selected", self.remove_sel, "Delete")
        em.addAction("Move Up", self.move_up, "Ctrl+Up")
        em.addAction("Move Down", self.move_down, "Ctrl+Down")
        em.addSeparator()
        em.addAction("Crop Borders", self._crop_borders, "Ctrl+Shift+C")
        em.addSeparator()
        em.addAction("Clear All", self.clear_all)

        # View menu
        vm = mb.addMenu("View")
        vm.addAction("Fit to View", self._fit_active, "Ctrl+0")
        vm.addAction("Actual Size", self._actual_active, "Ctrl+1")
        vm.addAction("Zoom In", self._zoomin_active, "Ctrl+=")
        vm.addAction("Zoom Out", self._zoomout_active, "Ctrl+-")

        # Help menu
        hm = mb.addMenu("Help")
        hm.addAction("About", self._show_about)

    # ── signal wiring ───────────────────────────────────────

    def _connect_signals(self) -> None:
        """Connect all UI signals."""
        # Image list
        self.img_list.currentRowChanged.connect(self._preview_selected)
        self.img_list.order_changed.connect(self._sync_order)
        self.img_list.delete_requested.connect(self.remove_sel)

        # Control buttons
        self.btn_up.clicked.connect(self.move_up)
        self.btn_dn.clicked.connect(self.move_down)
        self.btn_rm.clicked.connect(self.remove_sel)
        self.btn_clr.clicked.connect(self.clear_all)

        # Stitch / crop
        self.btn_stitch.clicked.connect(self._stitch_main)
        self.btn_crop.clicked.connect(self._crop_borders)

        # Zoom buttons
        self.btn_fit.clicked.connect(self.view.fit_to_view)
        self.btn_100.clicked.connect(self.view.actual_size)
        self.btn_zi.clicked.connect(self.view.zoom_in)
        self.btn_zo.clicked.connect(self.view.zoom_out)

        # Tab changes
        self._tabs.currentChanged.connect(self._tab_changed)

    def _apply_theme(self) -> None:
        """Apply the application stylesheet."""
        self.setStyleSheet(APPLICATION_STYLE)

    # ════════════════════ View Helpers ══════════════════════

    def _active_view(self) -> PanoramaView:
        """Get the currently active panorama view."""
        if self._tabs.currentIndex() == 1:
            return self._test_tab._view
        return self.view

    def _fit_active(self) -> None:
        self._active_view().fit_to_view()

    def _actual_active(self) -> None:
        self._active_view().actual_size()

    def _zoomin_active(self) -> None:
        self._active_view().zoom_in()

    def _zoomout_active(self) -> None:
        self._active_view().zoom_out()

    def _tab_changed(self, idx: int) -> None:
        """Handle tab change — update progress bar visibility."""
        is_stitching = self._worker is not None and self._worker.isRunning()
        self.pbar_test.setVisible(idx == 1 and is_stitching)
        self.pbar.setVisible(idx == 0 and is_stitching)

    # ════════════════════ Image Management ═════════════════

    def _update_count(self) -> None:
        """Update image count label and stitch button state."""
        n = len(self._paths)
        is_busy = self._worker is not None and self._worker.isRunning()

        self.lbl_cnt.setText(f"{n} image{'s' if n != 1 else ''}")
        self.btn_stitch.setEnabled(n >= 2 and not is_busy)
        self.btn_stitch.setText(f"▶  Stitch Panorama  ({n} images)")

    def add_images(self) -> None:
        """Open file dialog and add selected images."""
        logger.info("User triggered 'Add Images'")
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", str(self._last_open_dir), IMAGE_FILTER
        )
        if paths:
            self._last_open_dir = Path(paths[0]).parent
            self._load_images(paths)

    def _load_images(self, paths: list[str]) -> None:
        """Load images from file paths into the list."""
        added = 0

        for path in paths:
            if path in self._cv_imgs:
                continue

            try:
                logger.debug("Reading image: %s", path)
                img = cv2.imread(path)

                if img is None:
                    logger.warning("cv2.imread returned None for: %s", path)
                    self.statusBar().showMessage(
                        f"Cannot read (corrupt/unsupported): {Path(path).name}",
                        STATUS_TIMEOUT_MEDIUM,
                    )
                    continue

                px = cv_to_qpixmap(img)
                if px.isNull():
                    logger.error("Pixmap conversion failed for: %s", path)
                    continue

                self._paths.append(path)
                self._cv_imgs[path] = img
                self._pixmaps[path] = px
                self.img_list.add_image_item(path, img, px)
                added += 1

            except Exception:
                logger.error("Error loading image %s", path, exc_info=True)
                self.statusBar().showMessage(
                    f"Failed to load {Path(path).name}", STATUS_TIMEOUT_MEDIUM
                )

        if added:
            self._update_count()
            self.statusBar().showMessage(
                f"Added {added} image(s).  Total: {len(self._paths)}",
                STATUS_TIMEOUT_MEDIUM,
            )

    def _sync_order(self) -> None:
        """Synchronize internal path list with widget display order."""
        self._paths = self.img_list.get_ordered_paths()

    def _preview_selected(self, row: int) -> None:
        """Preview the selected image in the view."""
        if 0 <= row < len(self._paths):
            path = self._paths[row]
            self.view.set_pixmap(self._pixmaps[path])
            img = self._cv_imgs[path]
            self.lbl_info.setText(f"Preview  {img.shape[1]}×{img.shape[0]}")

    def move_up(self) -> None:
        """Move selected image up in the list."""
        row = self.img_list.currentRow()
        if row > 0:
            item = self.img_list.takeItem(row)
            self.img_list.insertItem(row - 1, item)
            self.img_list.setCurrentRow(row - 1)
            self._sync_order()

    def move_down(self) -> None:
        """Move selected image down in the list."""
        row = self.img_list.currentRow()
        if 0 <= row < self.img_list.count() - 1:
            item = self.img_list.takeItem(row)
            self.img_list.insertItem(row + 1, item)
            self.img_list.setCurrentRow(row + 1)
            self._sync_order()

    def remove_sel(self) -> None:
        """Remove the selected image."""
        row = self.img_list.currentRow()
        if row < 0:
            return

        path = self._paths.pop(row)
        self._cv_imgs.pop(path, None)
        self._pixmaps.pop(path, None)
        self.img_list.takeItem(row)

        self._update_count()
        self.view.set_pixmap(QPixmap())
        self._panorama_cv = None
        self._panorama_pixmap = None
        self.btn_crop.setEnabled(False)
        self.lbl_info.setText("")
        self.statusBar().showMessage(
            f"Removed.  Total: {len(self._paths)}", STATUS_TIMEOUT_MEDIUM
        )

    def clear_all(self) -> None:
        """Clear all loaded images."""
        logger.info("Clearing all images.")
        self._paths.clear()
        self._cv_imgs.clear()
        self._pixmaps.clear()
        self._panorama_cv = None
        self._panorama_pixmap = None
        self.img_list.clear()

        self.view.set_pixmap(QPixmap())
        self.lbl_info.setText("")
        self.btn_crop.setEnabled(False)
        self._test_tab._btn_crop.setEnabled(False)
        self._update_count()
        self.statusBar().showMessage("Cleared.")

    # ════════════════════ Stitching ════════════════════════

    def _get_params(self) -> dict:
        """Get current stitching parameters from UI controls."""
        return {
            "mode": self.combo_mode.currentText().lower(),
            "conf": self.spin_conf.value(),
            "reg_res": self.spin_reg.value(),
            "comp_res": self.spin_comp.value(),
            "wave": self.chk_wave.isChecked(),
            "wave_kind": self.combo_wk.currentText().lower(),
        }

    def _set_stitching_busy(self, busy: bool) -> None:
        """Update UI state for stitching in progress."""
        self.btn_stitch.setEnabled(not busy and len(self._paths) >= 2)
        self._test_tab._btn_stitch.setEnabled(not busy)

        if busy:
            self.btn_stitch.setText("⏳  Stitching …")
            self._test_tab._btn_stitch.setText("⏳  Stitching …")
        else:
            self._update_count()
            self._test_tab._btn_stitch.setText("▶  Stitch 3 Test Images")

    def _stitch_main(self) -> None:
        """Start stitching from main tab."""
        if len(self._paths) < 2:
            self.statusBar().showMessage(
                "Need at least 2 images to stitch.", STATUS_TIMEOUT_MEDIUM
            )
            return
        if self._worker and self._worker.isRunning():
            self.statusBar().showMessage(
                "Already stitching — please wait.", STATUS_TIMEOUT_SHORT
            )
            return

        imgs = [self._cv_imgs[p] for p in self._paths]
        self._start_stitch(imgs, "main")

    def _stitch_test(self, imgs: list[np.ndarray]) -> None:
        """Start stitching from test tab."""
        if self._worker and self._worker.isRunning():
            self.statusBar().showMessage(
                "Already stitching — please wait.", STATUS_TIMEOUT_SHORT
            )
            return
        self._tabs.setCurrentIndex(1)
        self._start_stitch(imgs, "test")

    def _stitch_from_active_tab(self) -> None:
        """Stitch based on currently active tab."""
        if self._tabs.currentIndex() == 1:
            self._test_tab._do_stitch()
        else:
            self._stitch_main()

    def _start_stitch(self, imgs: list[np.ndarray], source: str) -> None:
        """Start the stitching worker thread."""
        self._stitch_source = source
        self._stitch_start = time.time()
        params = self._get_params()
        self._set_stitching_busy(True)

        # Disable crop buttons until result arrives
        self.btn_crop.setEnabled(False)
        self._test_tab._btn_crop.setEnabled(False)

        # Show appropriate progress bar
        if source == "test":
            self.pbar.setVisible(False)
            self.pbar_test.setVisible(True)
            self._active_pbar = self.pbar_test
        else:
            self.pbar_test.setVisible(False)
            self.pbar.setVisible(True)
            self._active_pbar = self.pbar

        self._active_pbar.setRange(0, 0)
        self._prog_val = 0
        self._prog_dir = 1
        self._prog_timer.start(PROGRESS_TICK_MS)

        self.statusBar().showMessage("Stitching — please wait …")

        # Start worker
        self._worker = StitchWorker(imgs, params)
        self._worker.done.connect(self._on_stitch_done)
        self._worker.start()

    def _tick_progress(self) -> None:
        """Update indeterminate progress animation."""
        self._prog_val += self._prog_dir * PROGRESS_STEP
        if self._prog_val >= 100:
            self._prog_dir = -1
        elif self._prog_val <= 0:
            self._prog_dir = 1

        if self._active_pbar:
            self._active_pbar.setValue(max(0, min(100, self._prog_val)))

    def _on_stitch_done(
        self, ok: bool, msg: str, pano_cv: np.ndarray | None
    ) -> None:
        """Handle stitch completion."""
        self._prog_timer.stop()
        self.pbar.setVisible(False)
        self.pbar_test.setVisible(False)
        self._set_stitching_busy(False)

        elapsed = time.time() - self._stitch_start

        if ok and pano_cv is not None:
            px = cv_to_qpixmap(pano_cv)
            self._panorama_cv = pano_cv
            self._panorama_pixmap = px

            if self._stitch_source == "test":
                self._test_tab.show_panorama(px)
            else:
                self.view.set_pixmap(px)
                h, w = pano_cv.shape[:2]
                self.lbl_info.setText(f"Panorama  {w}×{h}")

            # Enable crop buttons if black borders are detected
            borders_found = has_black_borders(pano_cv)
            self.btn_crop.setEnabled(borders_found)
            self._test_tab._btn_crop.setEnabled(borders_found)
            if borders_found:
                self.btn_crop.setToolTip(
                    "Black borders detected — click to crop them"
                )
            else:
                self.btn_crop.setToolTip("No significant black borders detected")

            h, w = pano_cv.shape[:2]
            self.statusBar().showMessage(
                f"Done — panorama {w}×{h} px  ({elapsed:.1f} s)",
                STATUS_TIMEOUT_LONG,
            )
        else:
            logger.error("Stitching failed: %s", msg)
            self._panorama_cv = None
            self._panorama_pixmap = None
            self.btn_crop.setEnabled(False)
            self._test_tab._btn_crop.setEnabled(False)
            self.statusBar().showMessage(
                f"Stitching failed: {msg}", STATUS_TIMEOUT_LONG
            )

    # ════════════════════ Crop Borders ═════════════════════

    def _crop_borders(self) -> None:
        """Auto-crop black borders from the current panorama."""
        if self._panorama_cv is None:
            self.statusBar().showMessage(
                "No panorama to crop.", STATUS_TIMEOUT_SHORT
            )
            return

        old_h, old_w = self._panorama_cv.shape[:2]
        cropped = auto_crop_black_borders(self._panorama_cv)

        if cropped is None or (
            cropped.shape[0] == old_h and cropped.shape[1] == old_w
        ):
            self.statusBar().showMessage(
                "No black borders detected to crop.", STATUS_TIMEOUT_SHORT
            )
            return

        self._panorama_cv = cropped
        px = cv_to_qpixmap(cropped)
        self._panorama_pixmap = px

        if self._stitch_source == "test":
            self._test_tab.show_panorama(px)
        else:
            self.view.set_pixmap(px)
            h, w = cropped.shape[:2]
            self.lbl_info.setText(f"Panorama (cropped)  {w}×{h}")

        new_h, new_w = cropped.shape[:2]
        self.statusBar().showMessage(
            f"Cropped: {old_w}×{old_h} → {new_w}×{new_h}",
            STATUS_TIMEOUT_MEDIUM,
        )

        # Re-check for remaining borders
        still_has = has_black_borders(cropped)
        self.btn_crop.setEnabled(still_has)
        self._test_tab._btn_crop.setEnabled(still_has)

    # ════════════════════ Save ═════════════════════════════

    def save(self) -> None:
        """Save the current panorama to file via OpenCV (high quality)."""
        if self._panorama_cv is None:
            self.statusBar().showMessage(
                "No panorama to save.", STATUS_TIMEOUT_SHORT
            )
            return

        default_name = str(self._last_save_dir / "panorama.jpg")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Panorama", default_name, SAVE_FILTER
        )

        if not path:
            return

        try:
            logger.info("Saving panorama to: %s", path)
            ext = Path(path).suffix.lower()

            # Choose OpenCV imwrite params based on format
            imwrite_params: list[int] = []
            if ext in (".jpg", ".jpeg"):
                imwrite_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            elif ext == ".png":
                imwrite_params = [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION]
            # TIFF and BMP use defaults

            success = cv2.imwrite(path, self._panorama_cv, imwrite_params)

            if success:
                self._last_save_dir = Path(path).parent
                self.statusBar().showMessage(
                    f"Saved → {path}", STATUS_TIMEOUT_MEDIUM
                )
                logger.info("Panorama saved successfully.")
            else:
                logger.error("cv2.imwrite returned False for %s", path)
                # Fallback: try QPixmap.save
                if self._panorama_pixmap and not self._panorama_pixmap.isNull():
                    if self._panorama_pixmap.save(path):
                        self._last_save_dir = Path(path).parent
                        self.statusBar().showMessage(
                            f"Saved (via Qt fallback) → {path}",
                            STATUS_TIMEOUT_MEDIUM,
                        )
                        return
                self.statusBar().showMessage(
                    f"Save failed (format mismatch?): {path}",
                    STATUS_TIMEOUT_MEDIUM,
                )
        except OSError as exc:
            logger.error("OS Error saving file", exc_info=True)
            self.statusBar().showMessage(
                f"Save Error (Permissions/Disk space?): {exc}",
                STATUS_TIMEOUT_MEDIUM,
            )
        except Exception as exc:
            logger.error("Unexpected error saving file", exc_info=True)
            self.statusBar().showMessage(
                f"Save Error: {exc}", STATUS_TIMEOUT_MEDIUM
            )

    # ════════════════════ About ════════════════════════════

    def _show_about(self) -> None:
        """Show about dialog."""
        logger.info("User viewed 'About'")
        QMessageBox.about(
            self,
            "About Panorama Creator",
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {APP_VERSION}</p>"
            "<p>A panorama stitching application built with:</p>"
            "<ul>"
            "<li>PySide6 for the GUI</li>"
            "<li>OpenCV for image stitching</li>"
            "<li>NumPy for array operations</li>"
            "</ul>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Drag-and-drop image loading &amp; reordering</li>"
            "<li>Interactive preview with zoom / pan</li>"
            "<li>Configurable stitching parameters</li>"
            "<li>Auto-crop black borders from result</li>"
            "<li>High-quality save (JPEG 95%, PNG, TIFF, BMP)</li>"
            "<li>Built-in test images for quick try</li>"
            "<li>Delete-key shortcut to remove images</li>"
            "<li>Remembers last open / save directory</li>"
            "</ul>",
        )

    # ════════════════════ Drag & Drop ══════════════════════

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        """Accept drag enter if URLs contain local files."""
        if event.mimeData().hasUrls():
            if all(u.isLocalFile() for u in event.mimeData().urls()):
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        """Accept drag move events."""
        event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        """Handle file drop — filter to valid image files and load."""
        try:
            paths = [
                u.toLocalFile()
                for u in event.mimeData().urls()
                if u.isLocalFile()
            ]

            # Filter to image files only
            valid_paths = [p for p in paths if is_valid_image_file(p)]

            if valid_paths:
                logger.info("Dropped %d valid image file(s).", len(valid_paths))
                self._tabs.setCurrentIndex(0)
                self._last_open_dir = Path(valid_paths[0]).parent
                self._load_images(valid_paths)
                event.acceptProposedAction()
            else:
                event.ignore()
        except Exception:
            logger.error("Error processing drop event", exc_info=True)
            event.ignore()

    # ════════════════════ Clean Shutdown ═══════════════════

    def closeEvent(self, event) -> None:  # noqa: N802
        """Wait for the worker thread to finish before closing."""
        if self._worker and self._worker.isRunning():
            logger.info("Waiting for stitch worker to finish …")
            self._worker.quit()
            self._worker.wait(3000)
        event.accept()


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════


def main() -> None:
    """Application entry point."""
    logger.info("Application starting …")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    try:
        import cv2 as _cv2  # noqa: F811 — verifying availability
        import numpy as _np  # noqa: F811
    except ImportError:
        logger.critical(
            "Missing packages. Install with:  "
            "pip install opencv-python numpy PySide6"
        )
        sys.exit(
            "Missing packages. Install with:\n"
            "  pip install opencv-python numpy PySide6"
        )

    win = MainWindow()
    win.show()

    logger.info("Executing application event loop …")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()