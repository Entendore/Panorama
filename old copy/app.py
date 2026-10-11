#!/usr/bin/env python3
"""
Panorama Creator — PySide6 + OpenCV
Includes a Test tab with 3 programmatically generated overlapping images.
Features comprehensive terminal logging, error handling, and NO popup dialogs.
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)-8s [%(threadName)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("PanoramaApp")

try:
    import cv2
    import numpy as np
except ImportError:
    logger.critical("Missing packages. Install with: pip install opencv-python numpy PySide6")
    sys.exit("Missing packages. Install with:\n  pip install opencv-python numpy PySide6")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QFileDialog,
    QGroupBox, QDoubleSpinBox, QSplitter, QGraphicsView, QGraphicsScene,
    QToolBar, QListWidget, QListWidgetItem, QAbstractItemView,
    QCheckBox, QSizePolicy, QSpacerItem, QTabWidget,
)
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QBrush, QFont, QKeySequence, QAction,
)
from PySide6.QtCore import Qt, QSize, QThread, Signal, QPointF, QTimer

def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    logger.critical("Unhandled Exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = log_unhandled_exception

# ──────────────────────────── Helpers ────────────────────────────

def cv_to_qpixmap(cv_img):
    if cv_img is None:
        logger.warning("cv_to_qpixmap received None")
        return QPixmap()
    try:
        if len(cv_img.shape) == 2:
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2BGR)
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data.tobytes(), w, h, ch * w, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg)
    except Exception as e:
        logger.error("Failed to convert cv image to QPixmap: %e", e, exc_info=True)
        return QPixmap()

def make_thumbnail(pixmap, max_w=128, max_h=96):
    if pixmap.isNull(): return pixmap
    return pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

# ──────────────────── Synthetic Test Image Generator ─────────────

def generate_test_images():
    logger.info("Generating 3 synthetic test images...")
    W_FULL, H, OVERLAP, STRIP_W, NUM = 2200, 500, 200, 800, 3
    rng = np.random.RandomState(42)

    try:
        canvas = np.zeros((H, W_FULL, 3), dtype=np.uint8)
        for y in range(H // 2):
            t = y / (H // 2)
            canvas[y, :] = (int(30 + 80 * t), int(60 + 100 * t), int(140 + 80 * t))
        for y in range(H // 2, H):
            t = (y - H // 2) / (H // 2)
            canvas[y, :] = (int(50 + 60 * t), int(120 + 40 * t), int(40 + 30 * t))
        cv2.line(canvas, (0, H // 2), (W_FULL, H // 2), (200, 200, 180), 2)

        for px, ph in [(100, 180), (400, 140), (700, 160), (1050, 130), (1400, 150), (1700, 170), (2000, 155)]:
            pts = np.array([[px - 120, H // 2], [px, H // 2 - ph], [px + 120, H // 2]], np.int32)
            cv2.fillPoly(canvas, [pts], (80 + rng.randint(0, 40), 100 + rng.randint(0, 30), 70 + rng.randint(0, 30)))
        for gx in range(0, W_FULL, 80): cv2.line(canvas, (gx, H // 2 + 5), (gx, H), (70, 110, 50), 1)
        for gy in range(H // 2 + 20, H, 30): cv2.line(canvas, (0, gy), (W_FULL, gy), (70, 110, 50), 1)

        for cx, cy, r, col in [(150, 320, 35, (0, 0, 255)), (350, 280, 28, (0, 200, 200)), (550, 350, 40, (0, 255, 0)),
                   (750, 300, 25, (255, 0, 255)), (950, 360, 32, (255, 165, 0)), (1100, 290, 30, (255, 255, 0)),
                   (1300, 340, 38, (200, 0, 255)), (1500, 310, 26, (0, 255, 200)), (1700, 370, 34, (100, 200, 255)),
                   (1950, 280, 30, (255, 100, 100))]:
            cv2.circle(canvas, (cx, cy), r, col, -1)
            cv2.circle(canvas, (cx, cy), r, (255, 255, 255), 2)
            cv2.putText(canvas, str(r), (cx - 8, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        for rx, ry, rw, rh, col in [(200, 380, 60, 45, (180, 60, 60)), (480, 370, 70, 50, (60, 60, 180)),
                 (820, 385, 55, 40, (60, 180, 60)), (1150, 375, 65, 48, (180, 180, 60)),
                 (1450, 390, 58, 42, (180, 60, 180)), (1800, 380, 62, 46, (60, 180, 180))]:
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), col, -1)
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), (255, 255, 255), 2)

        for x in range(0, W_FULL, 18):
            cv2.line(canvas, (x, H // 2 + 8), (x + 60, H // 2 + 68), (90, 130, 70), 1)
            cv2.line(canvas, (x + 60, H // 2 + 8), (x, H // 2 + 68), (90, 130, 70), 1)

        for sx, sy in [(250, 250), (500, 220), (800, 240), (1100, 210), (1400, 235), (1700, 225), (1950, 245)]:
            cv2.drawMarker(canvas, (sx, sy), (255, 255, 255), cv2.MARKER_STAR, 20, 2)

        for i in range(1, 12):
            cv2.putText(canvas, f"N{i}", (80 + (i - 1) * 200, H - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        starts = [i * (STRIP_W - OVERLAP) for i in range(NUM)]
        strips = []
        for idx_s, s in enumerate(starts):
            e = min(s + STRIP_W, W_FULL)
            strip = canvas[:, s:e].copy()
            tint = np.array([rng.randint(-8, 9), rng.randint(-8, 9), rng.randint(-8, 9)], dtype=np.int16)
            strip = np.clip(strip.astype(np.int16) + tint, 0, 255).astype(np.uint8)
            noise = rng.randn(*strip.shape) * 3
            strip = np.clip(strip.astype(np.float64) + noise, 0, 255).astype(np.uint8)
            strips.append(strip)
            logger.debug("Sliced strip %d at x=%d, shape=%s", idx_s + 1, s, strip.shape[:2])

        for idx, (strip, lab) in enumerate(zip(strips, ["LEFT", "CENTER", "RIGHT"])):
            cv2.putText(strip, f"[{lab}]", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(strip, f"Image {idx+1}/3", (15, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            hh, ww = strip.shape[:2]
            cv2.putText(strip, f"{ww}x{hh}", (ww - 100, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)
            cv2.rectangle(strip, (0, 0), (ww - 1, hh - 1), (180, 180, 180), 2)

        logger.info("Successfully generated 3 test images.")
        return strips
    except Exception as e:
        logger.error("Failed to generate test images", exc_info=True)
        raise

# ──────────────────────── Graphics View ──────────────────────────

class PanoramaView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap_item = None
        self._is_panning = False
        self._pan_start = QPointF()
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor(42, 42, 42)))
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._show_placeholder()

    def set_pixmap(self, pixmap):
        self._scene.clear(); self._pixmap_item = None
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

    def fit_to_view(self):
        if self._pixmap_item: self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    def actual_size(self):
        if self._pixmap_item: self.resetTransform()
    def zoom_in(self):
        if self._pixmap_item: self.scale(1.25, 1.25)
    def zoom_out(self):
        if self._pixmap_item: self.scale(1 / 1.25, 1 / 1.25)

    def _show_placeholder(self, text=None):
        self._scene.clear()
        t = text or ("Add images and click  ▶ Stitch  to create a panorama\n\n"
                     "• Scroll wheel → zoom\n• Right-drag → pan\n• Drop image files on this window")
        txt = self._scene.addText(t, QFont("Segoe UI", 12))
        txt.setDefaultTextColor(QColor(140, 140, 140)); txt.setPos(160, 180)
        self._scene.setSceneRect(0, 0, 800, 500)

    def wheelEvent(self, event):
        if not self._pixmap_item: return
        self.scale(1.15 if event.angleDelta().y() > 0 else 1 / 1.15, 1.15 if event.angleDelta().y() > 0 else 1 / 1.15)

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self._is_panning = True; self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor); event.accept()
        else: super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            d = event.position() - self._pan_start; self._pan_start = event.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - d.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - d.y()))
            event.accept()
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_panning:
            self._is_panning = False; self.setCursor(Qt.CursorShape.ArrowCursor); event.accept()
        else: super().mouseReleaseEvent(event)

# ──────────────────────── Image List ─────────────────────────────

class ImageListWidget(QListWidget):
    order_changed = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(128, 96))
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setResizeMode(QListWidget.ResizeMode.Adjust); self.setSpacing(4)
        self.setMinimumWidth(200); self.setMaximumWidth(280)
        self.setStyleSheet("""
            QListWidget{background:#2d2d2d;border:1px solid #555;border-radius:4px;padding:4px;}
            QListWidget::item{background:#383838;border:1px solid #555;border-radius:3px;padding:4px;margin:2px;}
            QListWidget::item:selected{background:#4a6fa5;border-color:#6a9fd5;}
            QListWidget::item:hover{background:#404040;}""")
        self.model().rowsMoved.connect(lambda *_: self.order_changed.emit())

    def add_image_item(self, filepath, cv_img, pixmap):
        item = QListWidgetItem(); item.setIcon(make_thumbnail(pixmap))
        name = Path(filepath).name; h, w = cv_img.shape[:2]
        item.setText(f"{name}\n{w}×{h}"); item.setToolTip(f"{filepath}\n{w}×{h}")
        item.setData(Qt.ItemDataRole.UserRole, filepath); item.setSizeHint(QSize(220, 112))
        self.addItem(item)

# ──────────────────────── Stitch Worker ──────────────────────────

class StitchWorker(QThread):
    done = Signal(bool, str, object)

    def __init__(self, images, params):
        super().__init__()
        self.images = images; self.p = params

    def run(self):
        logger.info("StitchWorker started. Parameters: %s", self.p)
        try:
            mode = cv2.Stitcher_PANORAMA if self.p["mode"] == "panorama" else cv2.Stitcher_SCANS
            st = cv2.Stitcher.create(mode)
            st.setRegistrationResol(self.p["reg_res"])
            st.setSeamEstimationResol(0.1)
            st.setCompositingResol(self.p["comp_res"])
            st.setPanoConfidenceThresh(self.p["conf"])
            st.setWaveCorrection(self.p["wave"])
            
            # Safely handle wave correct kind (removed in newer OpenCV 4.x bindings)
            if self.p["wave"]:
                if hasattr(st, 'setWaveCorrectKind'):
                    kind = cv2.detail.WAVE_CORRECT_HORIZ if self.p["wave_kind"] == "horizontal" else cv2.detail.WAVE_CORRECT_VERT
                    st.setWaveCorrectKind(kind)
                else:
                    logger.warning("setWaveCorrectKind not available in this OpenCV version. Skipping.")
            
            logger.debug("Calling cv2.Stitcher.stitch() with %d images...", len(self.images))
            status, pano = st.stitch(self.images)
            
            if status == cv2.Stitcher_OK:
                h, w = pano.shape[:2]
                logger.info("Stitching SUCCESS. Output size: %dx%d", w, h)
                self.done.emit(True, "OK", pano)
            else:
                msgs = {
                    cv2.Stitcher_ERR_NEED_MORE_IMGS: "Need more images or insufficient overlap.",
                    cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL: "Homography estimation failed.",
                    cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL: "Camera parameter adjustment failed."
                }
                err_msg = msgs.get(status, f"Unknown OpenCV Stitcher error code {status}")
                logger.warning("Stitching FAILED. Status: %d - %s", status, err_msg)
                self.done.emit(False, err_msg, None)
        except Exception as exc:
            logger.error("Exception inside StitchWorker", exc_info=True)
            self.done.emit(False, f"Worker Exception: {str(exc)}", None)

# ──────────────── Test Tab Widget ───────────────────────────────

class TestTabWidget(QWidget):
    request_stitch = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._test_imgs = []; self._test_pixmaps = []; self._pano_pixmap = None; self._current_idx = -1
        self._build_ui(); self._generate()

    def _build_ui(self):
        outer = QVBoxLayout(self); outer.setSpacing(8)
        desc = QLabel("This tab generates 3 synthetic test images with ~25 % overlap and rich features.\nClick any thumbnail to preview it, then press the stitch button.")
        desc.setWordWrap(True); desc.setStyleSheet("color:#aaa;padding:4px 8px;"); outer.addWidget(desc)

        thumb_box = QHBoxLayout(); thumb_box.setSpacing(12); self._thumb_btns = []
        for i in range(3):
            btn = QPushButton(); btn.setFixedSize(220, 130); btn.setCheckable(True)
            btn.setStyleSheet("""QPushButton{background:#383838;border:2px solid #555;border-radius:6px;}
                QPushButton:hover{border-color:#88aacc;} QPushButton:checked{border-color:#4a9fd5;background:#3a5570;}""")
            btn.clicked.connect(lambda checked, idx=i: self._select(idx))
            thumb_box.addWidget(btn); self._thumb_btns.append(btn)
        thumb_box.addStretch(); outer.addLayout(thumb_box)

        self._lbl_info = QLabel("Generating test images..."); self._lbl_info.setStyleSheet("color:#999;padding:0 8px;"); outer.addWidget(self._lbl_info)
        self._view = PanoramaView(); outer.addWidget(self._view, stretch=1)

        zb = QHBoxLayout()
        for text, slot in [("Fit", self._view.fit_to_view), ("100%", self._view.actual_size), ("+", self._view.zoom_in), ("−", self._view.zoom_out)]:
            b = QPushButton(text); b.setFixedSize(42, 28); b.clicked.connect(slot); zb.addWidget(b)
        zb.addStretch()
        self._lbl_size = QLabel(""); self._lbl_size.setStyleSheet("color:#999;"); zb.addWidget(self._lbl_size)
        outer.addLayout(zb)

        self._btn_stitch = QPushButton("▶  Stitch 3 Test Images"); self._btn_stitch.setFixedHeight(42); self._btn_stitch.setObjectName("stitchBtn")
        self._btn_stitch.clicked.connect(self._do_stitch); outer.addWidget(self._btn_stitch)

    def _generate(self):
        try:
            self._test_imgs = generate_test_images()
            self._test_pixmaps = [cv_to_qpixmap(img) for img in self._test_imgs]
            for i, (px, btn) in enumerate(zip(self._test_pixmaps, self._thumb_btns)):
                thumb = make_thumbnail(px, 210, 120); btn.setIcon(thumb); btn.setIconSize(thumb.size()); btn.setText("")
            self._lbl_info.setText("Click a thumbnail to preview.")
            logger.info("Test tab UI populated successfully.")
        except Exception as e:
            logger.critical("Failed to populate test tab", exc_info=True)
            self._lbl_info.setText("ERROR: Failed to generate test images. Check terminal logs.")

    def _select(self, idx):
        for i, b in enumerate(self._thumb_btns): b.setChecked(i == idx)
        self._current_idx = idx; self._pano_pixmap = None
        self._view.set_pixmap(self._test_pixmaps[idx])
        h, w = self._test_imgs[idx].shape[:2]
        self._lbl_info.setText(f"Preview: Image {idx+1}"); self._lbl_size.setText(f"{w}×{h}")

    def _do_stitch(self): self.request_stitch.emit(self._test_imgs)

    def show_panorama(self, pixmap):
        self._pano_pixmap = pixmap; self._view.set_pixmap(pixmap)
        for b in self._thumb_btns: b.setChecked(False)
        self._current_idx = -1; self._lbl_info.setText("Result: stitched panorama from 3 test images")
        self._lbl_size.setText(f"{pixmap.width()}×{pixmap.height()}")

# ──────────────────────── Main Window ────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing MainWindow...")
        self.setWindowTitle("Panorama Creator"); self.setMinimumSize(1024, 680); self.resize(1280, 820)
        self._paths = []; self._cv_imgs = {}; self._pixmaps = {}
        self._panorama_pixmap = None; self._worker = None; self._stitch_source = "main"; self._active_pbar = None
        self._prog_timer = QTimer(self); self._prog_val = 0; self._prog_dir = 1
        try:
            self._build_ui(); self._build_toolbar(); self._build_menu(); self._connect(); self._apply_theme(); self.setAcceptDrops(True)
            logger.info("MainWindow initialization complete.")
        except Exception as e:
            logger.critical("Failed to build UI", exc_info=True); raise

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        vbox = QVBoxLayout(root); vbox.setContentsMargins(6, 6, 6, 6); vbox.setSpacing(6)
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane{border:1px solid #555;border-radius:4px;background:#1e1e1e;}
            QTabBar::tab{background:#2a2a2a;color:#aaa;padding:8px 20px;border:1px solid #555;border-bottom:none;border-radius:6px 6px 0 0;margin-right:2px;}
            QTabBar::tab:selected{background:#1e1e1e;color:#fff;border-color:#4a6fa5;} QTabBar::tab:hover{color:#ddd;}""")

        main_tab = QWidget(); ml = QVBoxLayout(main_tab); ml.setContentsMargins(4, 4, 4, 4); ml.setSpacing(6)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget(); ll = QVBoxLayout(left); ll.setContentsMargins(0, 0, 0, 0); ll.setSpacing(4)
        ll.addWidget(self._bold_label("Images  (drag to reorder)")); self.img_list = ImageListWidget(); ll.addWidget(self.img_list)
        row = QHBoxLayout()
        self.btn_up = QPushButton("▲ Up"); self.btn_dn = QPushButton("▼ Down"); self.btn_rm = QPushButton("✕ Remove"); self.btn_clr = QPushButton("Clear All")
        for b in (self.btn_up, self.btn_dn, self.btn_rm, self.btn_clr): b.setFixedHeight(30); row.addWidget(b)
        ll.addLayout(row); self.lbl_cnt = QLabel("0 images"); self.lbl_cnt.setStyleSheet("color:#999;padding:2px;"); ll.addWidget(self.lbl_cnt)
        splitter.addWidget(left)

        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(4)
        self.view = PanoramaView(); rl.addWidget(self.view, stretch=1)
        zb = QHBoxLayout()
        self.btn_fit = QPushButton("Fit"); self.btn_100 = QPushButton("100%"); self.btn_zi = QPushButton("+"); self.btn_zo = QPushButton("−")
        for b in (self.btn_fit, self.btn_100, self.btn_zi, self.btn_zo): b.setFixedSize(42, 28); zb.addWidget(b)
        zb.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding))
        self.lbl_info = QLabel(""); self.lbl_info.setStyleSheet("color:#999;"); zb.addWidget(self.lbl_info); rl.addLayout(zb)

        og = QGroupBox("Stitching Options"); ol = QHBoxLayout(og); ol.setSpacing(14)
        self.combo_mode = self._combo(["Panorama", "Scans"], "combo_mode", 120); ol.addLayout(self._labeled("Mode:", self.combo_mode))
        self.spin_conf = self._dspin(0, 1, 1.0, 0.05, "spin_conf", 100); ol.addLayout(self._labeled("Confidence:", self.spin_conf))
        self.spin_reg = self._dspin(0.1, 1, 0.6, 0.1, "spin_reg", 100); ol.addLayout(self._labeled("Reg. Resol:", self.spin_reg))
        self.spin_comp = self._dspin(-1, 1, -1, 0.1, "spin_comp", 100, "Full (−1)"); ol.addLayout(self._labeled("Comp. Resol:", self.spin_comp))
        wv = QVBoxLayout(); self.chk_wave = QCheckBox("Wave Correction"); self.chk_wave.setChecked(True); wv.addWidget(self.chk_wave)
        self.combo_wk = self._combo(["Horizontal", "Vertical"], "combo_wk", 120); wv.addWidget(self.combo_wk); ol.addLayout(wv)
        ol.addStretch(); rl.addWidget(og)

        self.pbar = QProgressBar(); self.pbar.setFixedHeight(20); self.pbar.setVisible(False); rl.addWidget(self.pbar)
        self.btn_stitch = QPushButton("▶  Stitch Panorama"); self.btn_stitch.setFixedHeight(42); self.btn_stitch.setObjectName("stitchBtn"); self.btn_stitch.setEnabled(False)
        rl.addWidget(self.btn_stitch)
        splitter.addWidget(right); splitter.setStretchFactor(0, 0); splitter.setStretchFactor(1, 1); splitter.setSizes([240, 1040])
        ml.addWidget(splitter); self._tabs.addTab(main_tab, "📷  Panorama Creator")

        self._test_tab = TestTabWidget(); self._test_tab.request_stitch.connect(self._stitch_test)
        self._tabs.addTab(self._test_tab, "🧪  Test (3 Images)"); vbox.addWidget(self._tabs)
        
        self.pbar_test = QProgressBar(); self.pbar_test.setFixedHeight(20); self.pbar_test.setVisible(False); vbox.addWidget(self.pbar_test)
        self.statusBar().showMessage("Ready — switch to the Test tab for a quick try!")

    @staticmethod
    def _bold_label(text): return QLabel(text) if not hasattr(QLabel(text), 'setStyleSheet') else (l := QLabel(text), l.setStyleSheet("font-weight:bold;color:#ccc;padding:4px;"), l)[1]
    @staticmethod
    def _combo(items, attr, w=120): c = QComboBox(); c.addItems(items); c.setFixedWidth(w); setattr(c, "_attr", attr); return c
    @staticmethod
    def _dspin(lo, hi, val, step, attr, w=100, svtext=None):
        s = QDoubleSpinBox(); s.setRange(lo, hi); s.setValue(val); s.setSingleStep(step); s.setFixedWidth(w)
        if svtext: s.setSpecialValueText(svtext)
        setattr(s, "_attr", attr); return s
    @staticmethod
    def _labeled(text, widget): v = QVBoxLayout(); v.addWidget(QLabel(text)); v.addWidget(widget); return v

    def _build_toolbar(self):
        tb = QToolBar("Main"); tb.setMovable(False); tb.setIconSize(QSize(20, 20)); self.addToolBar(tb)
        a = lambda txt, slot, sc=None: self._action(tb, txt, slot, sc)
        a("📁 Add", self.add_images, "Ctrl+O"); tb.addSeparator()
        a("▶ Stitch", self._stitch_from_active_tab, "Ctrl+G"); tb.addSeparator()
        a("💾 Save", self.save, "Ctrl+Shift+S"); tb.addSeparator(); a("🗑 Clear", self.clear_all)

    def _action(self, parent, text, slot, shortcut):
        a = QAction(text, self)
        if shortcut: a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot); parent.addAction(a); return a

    def _build_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("File"); fm.addAction("Add Images…", self.add_images, "Ctrl+O"); fm.addSeparator()
        fm.addAction("Save Panorama…", self.save, "Ctrl+Shift+S"); fm.addSeparator(); fm.addAction("Exit", self.close, "Ctrl+Q")
        em = mb.addMenu("Edit"); em.addAction("Remove Selected", self.remove_sel); em.addAction("Move Up", self.move_up)
        em.addAction("Move Down", self.move_down); em.addSeparator(); em.addAction("Clear All", self.clear_all)
        vm = mb.addMenu("View"); vm.addAction("Fit to View", self._fit_active, "Ctrl+0"); vm.addAction("Actual Size", self._actual_active, "Ctrl+1")
        vm.addAction("Zoom In", self._zoomin_active, "Ctrl+="); vm.addAction("Zoom Out", self._zoomout_active, "Ctrl+-")
        hm = mb.addMenu("Help"); hm.addAction("About", self._about)

    def _connect(self):
        self.img_list.currentRowChanged.connect(self._preview_selected); self.img_list.order_changed.connect(self._sync_order)
        self.btn_up.clicked.connect(self.move_up); self.btn_dn.clicked.connect(self.move_down)
        self.btn_rm.clicked.connect(self.remove_sel); self.btn_clr.clicked.connect(self.clear_all)
        self.btn_stitch.clicked.connect(self._stitch_main)
        self.btn_fit.clicked.connect(self.view.fit_to_view); self.btn_100.clicked.connect(self.view.actual_size)
        self.btn_zi.clicked.connect(self.view.zoom_in); self.btn_zo.clicked.connect(self.view.zoom_out)
        self._prog_timer.timeout.connect(self._tick_progress); self._tabs.currentChanged.connect(self._tab_changed)

    def _active_view(self): return self._test_tab._view if self._tabs.currentIndex() == 1 else self.view
    def _fit_active(self): self._active_view().fit_to_view()
    def _actual_active(self): self._active_view().actual_size()
    def _zoomin_active(self): self._active_view().zoom_in()
    def _zoomout_active(self): self._active_view().zoom_out()

    def _tab_changed(self, idx):
        self.pbar_test.setVisible(idx == 1 and bool(self._worker and self._worker.isRunning()))

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow{background:#1e1e1e;} QWidget{color:#ddd;font-family:'Segoe UI',Arial,sans-serif;}
            QGroupBox{border:1px solid #555;border-radius:4px;margin-top:8px;padding-top:14px;color:#ccc;}
            QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 5px;}
            QPushButton{background:#3a3a3a;border:1px solid #555;border-radius:4px;padding:4px 10px;color:#ddd;}
            QPushButton:hover{background:#4a4a4a;} QPushButton:pressed{background:#2a2a2a;}
            QPushButton:disabled{color:#666;background:#333;}
            QPushButton#stitchBtn{background:#3a6a3a;font-size:14px;font-weight:bold;border:none;border-radius:6px;color:#fff;}
            QPushButton#stitchBtn:hover{background:#4a8a4a;} QPushButton#stitchBtn:pressed{background:#2a5a2a;}
            QPushButton#stitchBtn:disabled{background:#444;color:#777;}
            QComboBox{background:#3a3a3a;border:1px solid #555;border-radius:3px;padding:3px 8px;color:#ddd;}
            QComboBox::drop-down{border:none;width:20px;}
            QComboBox QAbstractItemView{background:#3a3a3a;color:#ddd;selection-background-color:#4a6fa5;}
            QDoubleSpinBox,QSpinBox{background:#3a3a3a;border:1px solid #555;border-radius:3px;padding:3px 6px;color:#ddd;}
            QProgressBar{border:1px solid #555;border-radius:3px;background:#2a2a2a;text-align:center;color:#ddd;}
            QProgressBar::chunk{background:#4a6fa5;border-radius:2px;}
            QToolBar{background:#2a2a2a;border-bottom:1px solid #444;spacing:6px;padding:3px;}
            QMenuBar{background:#2a2a2a;border-bottom:1px solid #444;color:#ddd;} QMenuBar::item:selected{background:#4a4a4a;}
            QMenu{background:#2a2a2a;border:1px solid #555;color:#ddd;} QMenu::item:selected{background:#4a6fa5;}
            QStatusBar{background:#252525;border-top:1px solid #444;color:#aaa;}
            QCheckBox{spacing:6px;} QCheckBox::indicator{width:16px;height:16px;border:1px solid #555;border-radius:3px;background:#3a3a3a;}
            QCheckBox::indicator:checked{background:#4a6fa5;border-color:#6a9fd5;} QLabel{background:transparent;}""")

    # ====================== Image Management =====================
    def _update_count(self):
        n = len(self._paths); is_busy = bool(self._worker and self._worker.isRunning())
        self.lbl_cnt.setText(f"{n} image{'s' if n != 1 else ''}")
        self.btn_stitch.setEnabled(n >= 2 and not is_busy)
        self.btn_stitch.setText(f"▶  Stitch Panorama  ({n} images)")

    def add_images(self):
        logger.info("User triggered 'Add Images'")
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp);;All Files (*)")
        if paths: self._load(paths)

    def _load(self, paths):
        added = 0
        for p in paths:
            if p in self._cv_imgs: continue
            try:
                logger.debug("Reading image: %s", p)
                img = cv2.imread(p)
                if img is None:
                    logger.warning("cv2.imread returned None for: %s", p)
                    self.statusBar().showMessage(f"Cannot read (corrupt/unsupported): {Path(p).name}")
                    continue
                px = cv_to_qpixmap(img)
                if px.isNull():
                    logger.error("Pixmap conversion failed for: %s", p); continue
                self._paths.append(p); self._cv_imgs[p] = img; self._pixmaps[p] = px
                self.img_list.add_image_item(p, img, px); added += 1
            except Exception as e:
                logger.error("Error loading image %s", p, exc_info=True)
                self.statusBar().showMessage(f"Failed to load {Path(p).name}")
        if added:
            self._update_count()
            self.statusBar().showMessage(f"Added {added} image(s).  Total: {len(self._paths)}", 5000)

    def _sync_order(self):
        self._paths = [self.img_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.img_list.count())]

    def _preview_selected(self, row):
        if 0 <= row < len(self._paths):
            p = self._paths[row]; self.view.set_pixmap(self._pixmaps[p])
            img = self._cv_imgs[p]; self.lbl_info.setText(f"Preview  {img.shape[1]}×{img.shape[0]}")

    def move_up(self):
        r = self.img_list.currentRow()
        if r > 0:
            it = self.img_list.takeItem(r); self.img_list.insertItem(r - 1, it)
            self.img_list.setCurrentRow(r - 1); self._sync_order()

    def move_down(self):
        r = self.img_list.currentRow()
        if 0 <= r < self.img_list.count() - 1:
            it = self.img_list.takeItem(r); self.img_list.insertItem(r + 1, it)
            self.img_list.setCurrentRow(r + 1); self._sync_order()

    def remove_sel(self):
        r = self.img_list.currentRow()
        if r < 0: return
        p = self._paths.pop(r); self._cv_imgs.pop(p, None); self._pixmaps.pop(p, None)
        self.img_list.takeItem(r); self._update_count()
        self.view.set_pixmap(None); self._panorama_pixmap = None; self.lbl_info.setText("")
        self.statusBar().showMessage(f"Removed.  Total: {len(self._paths)}")

    def clear_all(self):
        logger.info("Clearing all images.")
        self._paths.clear(); self._cv_imgs.clear(); self._pixmaps.clear()
        self._panorama_pixmap = None; self.img_list.clear()
        self.view.set_pixmap(None); self.lbl_info.setText(""); self._update_count()
        self.statusBar().showMessage("Cleared.")

    # ====================== Stitching ============================
    def _get_params(self):
        return dict(mode=self.combo_mode.currentText().lower(), conf=self.spin_conf.value(),
                    reg_res=self.spin_reg.value(), comp_res=self.spin_comp.value(),
                    wave=self.chk_wave.isChecked(), wave_kind=self.combo_wk.currentText().lower())

    def _set_stitching_busy(self, busy):
        self.btn_stitch.setEnabled(not busy); self._test_tab._btn_stitch.setEnabled(not busy)
        if busy:
            self.btn_stitch.setText("⏳  Stitching…"); self._test_tab._btn_stitch.setText("⏳  Stitching…")
        else:
            self._update_count(); self._test_tab._btn_stitch.setText("▶  Stitch 3 Test Images")

    def _stitch_main(self):
        if len(self._paths) < 2:
            self.statusBar().showMessage("Need at least 2 images to stitch."); return
        if self._worker and self._worker.isRunning(): return
        imgs = [self._cv_imgs[p] for p in self._paths]; self._start_stitch(imgs, "main")

    def _stitch_test(self, imgs):
        if self._worker and self._worker.isRunning(): return
        self._tabs.setCurrentIndex(1); self._start_stitch(imgs, "test")

    def _stitch_from_active_tab(self):
        if self._tabs.currentIndex() == 1: self._test_tab._do_stitch()
        else: self._stitch_main()

    def _start_stitch(self, imgs, source):
        self._stitch_source = source; params = self._get_params(); self._set_stitching_busy(True)
        if source == "test": self.pbar.setVisible(False); self.pbar_test.setVisible(True); self._active_pbar = self.pbar_test
        else: self.pbar_test.setVisible(False); self.pbar.setVisible(True); self._active_pbar = self.pbar
        self._active_pbar.setRange(0, 0); self._prog_val, self._prog_dir = 0, 1
        self._prog_timer.start(40); self.statusBar().showMessage("Stitching — please wait…")
        self._worker = StitchWorker(imgs, params); self._worker.done.connect(self._on_done); self._worker.start()

    def _tick_progress(self):
        self._prog_val += self._prog_dir * 2
        if self._prog_val >= 100: self._prog_dir = -1
        elif self._prog_val <= 0: self._prog_dir = 1
        if self._active_pbar: self._active_pbar.setValue(max(0, min(100, self._prog_val)))

    def _on_done(self, ok, msg, pano_cv):
        self._prog_timer.stop(); self.pbar.setVisible(False); self.pbar_test.setVisible(False)
        self._set_stitching_busy(False)
        if ok and pano_cv is not None:
            px = cv_to_qpixmap(pano_cv)
            if self._stitch_source == "test": self._panorama_pixmap = px; self._test_tab.show_panorama(px)
            else:
                self._panorama_pixmap = px; self.view.set_pixmap(px)
                h, w = pano_cv.shape[:2]; self.lbl_info.setText(f"Panorama  {w}×{h}")
            h, w = pano_cv.shape[:2]; self.statusBar().showMessage(f"Done — panorama {w}×{h} px", 10000)
        else:
            logger.error("Stitching UI callback failed: %s", msg)
            self.statusBar().showMessage(f"Stitching failed: {msg}", 10000)

    # ====================== Save =================================
    def save(self):
        if not self._panorama_pixmap or self._panorama_pixmap.isNull():
            self.statusBar().showMessage("No panorama to save."); return
        path, _ = QFileDialog.getSaveFileName(self, "Save Panorama", "panorama.jpg", "JPEG (*.jpg *.jpeg);;PNG (*.png);;TIFF (*.tiff);;BMP (*.bmp)")
        if path:
            try:
                logger.info("Saving panorama to: %s", path)
                if self._panorama_pixmap.save(path):
                    self.statusBar().showMessage(f"Saved → {path}", 5000); logger.info("Panorama saved successfully.")
                else:
                    logger.error("Qt pixmap.save returned False for %s", path)
                    self.statusBar().showMessage(f"Save failed (format mismatch?): {path}", 5000)
            except OSError as e:
                logger.error("OS Error saving file", exc_info=True)
                self.statusBar().showMessage(f"Save Error (Permissions/Disk space?): {e}", 5000)
            except Exception as e:
                logger.error("Unexpected error saving file", exc_info=True)
                self.statusBar().showMessage(f"Save Error: {e}", 5000)

    # ====================== About ================================
    def _about(self):
        logger.info("User viewed 'About'")
        self.statusBar().showMessage("Panorama Creator — Built with PySide6 + OpenCV", 5000)

    # ====================== Drag & Drop ==========================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()): event.acceptProposedAction()
        else: event.ignore()

    def dragMoveEvent(self, event): event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            paths = [p for p in paths if Path(p).suffix.lower() in IMAGE_EXTS]
            if paths:
                logger.info("Dropped %d valid image files.", len(paths))
                self._tabs.setCurrentIndex(0); self._load(paths); event.acceptProposedAction()
            else: event.ignore()
        except Exception as e:
            logger.error("Error processing drop event", exc_info=True); event.ignore()

# ──────────────────────────── main ───────────────────────────────

def main():
    logger.info("Application starting...")
    app = QApplication(sys.argv); app.setApplicationName("Panorama Creator")
    try:
        win = MainWindow(); win.show()
        logger.info("Executing application event loop..."); sys.exit(app.exec())
    except Exception as e:
        logger.critical("Fatal error during startup or execution", exc_info=True); sys.exit(1)

if __name__ == "__main__":
    main()