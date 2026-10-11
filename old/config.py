"""
Panorama Creator — Configuration Constants
"""

from PySide6.QtCore import QSize

# ──────────────────────── Image Settings ────────────────────────

IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
IMAGE_FILTER: str = "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp);;All Files (*)"
SAVE_FILTER: str = "JPEG (*.jpg *.jpeg);;PNG (*.png);;TIFF (*.tiff);;BMP (*.bmp)"

# ──────────────────────── UI Dimensions ─────────────────────────

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

# ──────────────────────── Test Image Config ─────────────────────

TEST_IMAGE_COUNT: int = 3
TEST_CANVAS_WIDTH: int = 2200
TEST_CANVAS_HEIGHT: int = 500
TEST_OVERLAP: int = 300
TEST_STRIP_WIDTH: int = 800
TEST_RANDOM_SEED: int = 42

# ──────────────────────── Stitching Defaults ────────────────────

DEFAULT_STITCH_MODE: int = 0  # Index for "Panorama"
DEFAULT_CONFIDENCE: float = 1.0
DEFAULT_REG_RESOL: float = 0.6
DEFAULT_COMP_RESOL: float = -1.0
DEFAULT_WAVE_CORRECTION: bool = True
DEFAULT_WAVE_KIND: int = 0  # Index for "Horizontal"

STITCH_CONFIDENCE_MIN: float = 0.0
STITCH_CONFIDENCE_MAX: float = 1.0
STITCH_CONFIDENCE_STEP: float = 0.05
STITCH_REG_RESOL_MIN: float = 0.1
STITCH_REG_RESOL_MAX: float = 1.0
STITCH_REG_RESOL_STEP: float = 0.1
STITCH_COMP_RESOL_MIN: float = -1.0
STITCH_COMP_RESOL_MAX: float = 1.0
STITCH_COMP_RESOL_STEP: float = 0.1

# ──────────────────────── Progress Bar ──────────────────────────

PROGRESS_TICK_MS: int = 40
PROGRESS_STEP: int = 2

# ──────────────────────── Zoom Factors ──────────────────────────

ZOOM_IN_FACTOR: float = 1.25
ZOOM_OUT_FACTOR: float = 0.8  # 1 / 1.25
WHEEL_ZOOM_FACTOR: float = 1.15
WHEEL_ZOOM_OUT_FACTOR: float = 1 / 1.15

# ──────────────────────── Theme Styles ──────────────────────────

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