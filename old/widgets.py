"""
Panorama Creator — Custom Widgets
PanoramaView (zoomable/pannable image display) and ImageListWidget (draggable image list).
"""

import logging

from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QFont
from PySide6.QtCore import Qt, QSize, Signal, QPointF

from config import (
    THUMBNAIL_SIZE,
    IMAGE_LIST_MIN_W,
    IMAGE_LIST_MAX_W,
    IMAGE_LIST_ITEM_W,
    IMAGE_LIST_ITEM_H,
    IMAGE_LIST_STYLE,
    ZOOM_IN_FACTOR,
    ZOOM_OUT_FACTOR,
    WHEEL_ZOOM_FACTOR,
    WHEEL_ZOOM_OUT_FACTOR,
)
from helpers import make_thumbnail

logger = logging.getLogger("PanoramaApp.widgets")


class PanoramaView(QGraphicsView):
    """
    Graphics view with zoom and pan capabilities for displaying images.
    
    Features:
    - Scroll wheel zoom (centered on cursor)
    - Right-click/middle-click drag to pan
    - Fit to view and actual size buttons
    - Placeholder text when no image loaded
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._pixmap_item = None
        self._is_panning = False
        self._pan_start = QPointF()
        
        # Rendering settings
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
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
                self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                logger.debug("Displayed pixmap %dx%d", pixmap.width(), pixmap.height())
            except Exception as e:
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
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
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
    
    def _show_placeholder(self, text: str | None = None) -> None:
        """Display placeholder text when no image is loaded."""
        self._scene.clear()
        default_text = (
            "Add images and click  ▶ Stitch  to create a panorama\n\n"
            "• Scroll wheel → zoom\n"
            "• Right-drag → pan\n"
            "• Drop image files on this window"
        )
        display_text = text or default_text
        
        txt = self._scene.addText(display_text, QFont("Segoe UI", 12))
        txt.setDefaultTextColor(QColor(140, 140, 140))
        txt.setPos(160, 180)
        self._scene.setSceneRect(0, 0, 800, 500)
    
    def wheelEvent(self, event) -> None:
        """Handle scroll wheel for zooming."""
        if not self._pixmap_item:
            return
        
        factor = WHEEL_ZOOM_FACTOR if event.angleDelta().y() > 0 else WHEEL_ZOOM_OUT_FACTOR
        self.scale(factor, factor)
    
    def mousePressEvent(self, event) -> None:
        """Start panning on right/middle click."""
        if event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
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
    
    def mouseReleaseEvent(self, event) -> None:
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
    - Emits signal when order changes
    """
    
    order_changed = Signal()
    
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
    
    def add_image_item(
        self,
        filepath: str,
        cv_img,  # np.ndarray but avoiding forward ref issues
        pixmap: QPixmap
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
        
        name = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]  # Handle both path separators
        h, w = cv_img.shape[:2]
        
        item.setText(f"{name}\n{w}×{h}")
        item.setToolTip(f"{filepath}\n{w}×{h}")
        item.setData(Qt.ItemDataRole.UserRole, filepath)
        item.setSizeHint(QSize(IMAGE_LIST_ITEM_W, IMAGE_LIST_ITEM_H))
        
        self.addItem(item)
    
    def get_ordered_paths(self) -> list[str]:
        """Get list of filepaths in current display order."""
        return [
            self.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.count())
        ]