"""
Panorama Creator — Main Window
Contains MainWindow and TestTabWidget classes for the application UI.
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import (
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
)
from PySide6.QtGui import QPixmap, QFont, QKeySequence, QAction
from PySide6.QtCore import Qt, QTimer, Signal

import cv2
import numpy as np

from config import (
    IMAGE_EXTENSIONS,
    IMAGE_FILTER,
    SAVE_FILTER,
    TEST_THUMB_W,
    TEST_THUMB_H,
    MIN_WINDOW_W,
    MIN_WINDOW_H,
    DEFAULT_WINDOW_W,
    DEFAULT_WINDOW_H,
    SPLITTER_LEFT_SIZE,
    SPLITTER_RIGHT_SIZE,
    APPLICATION_STYLE,
    TAB_WIDGET_STYLE,
    TEST_THUMB_STYLE,
    DEFAULT_STITCH_MODE,
    DEFAULT_CONFIDENCE,
    DEFAULT_REG_RESOL,
    DEFAULT_COMP_RESOL,
    DEFAULT_WAVE_CORRECTION,
    DEFAULT_WAVE_KIND,
    STITCH_CONFIDENCE_MIN,
    STITCH_CONFIDENCE_MAX,
    STITCH_CONFIDENCE_STEP,
    STITCH_REG_RESOL_MIN,
    STITCH_REG_RESOL_MAX,
    STITCH_REG_RESOL_STEP,
    STITCH_COMP_RESOL_MIN,
    STITCH_COMP_RESOL_MAX,
    STITCH_COMP_RESOL_STEP,
    PROGRESS_TICK_MS,
    PROGRESS_STEP,
)
from helpers import cv_to_qpixmap, make_thumbnail, generate_test_images, is_valid_image_file
from widgets import PanoramaView, ImageListWidget
from worker import StitchWorker

logger = logging.getLogger("PanoramaApp.window")


class TestTabWidget(QWidget):
    """
    Test tab with 3 programmatically generated overlapping images.
    
    Signals:
        request_stitch: Emitted with list of images when stitch is requested
    """
    
    request_stitch = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._test_imgs: list[np.ndarray] = []
        self._test_pixmaps: list[QPixmap] = []
        self._pano_pixmap: QPixmap | None = None
        self._current_idx: int = -1
        
        self._build_ui()
        self._generate()
    
    def _build_ui(self) -> None:
        """Build the test tab UI."""
        outer = QVBoxLayout(self)
        outer.setSpacing(8)
        
        # Description
        desc = QLabel(
            "This tab generates 3 synthetic test images with ~25% overlap and rich features.\n"
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
        self._lbl_info = QLabel("Generating test images...")
        self._lbl_info.setStyleSheet("color:#999;padding:0 8px;")
        outer.addWidget(self._lbl_info)
        
        # Preview view
        self._view = PanoramaView()
        outer.addWidget(self._view, stretch=1)
        
        # Zoom controls
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
    
    def _generate(self) -> None:
        """Generate and display test images."""
        try:
            self._test_imgs = generate_test_images()
            self._test_pixmaps = [cv_to_qpixmap(img) for img in self._test_imgs]
            
            for i, (px, btn) in enumerate(zip(self._test_pixmaps, self._thumb_btns)):
                thumb = make_thumbnail(px, TEST_THUMB_W, TEST_THUMB_H)
                btn.setIcon(thumb)
                btn.setIconSize(thumb.size())
                btn.setText("")
            
            self._lbl_info.setText("Click a thumbnail to preview.")
            logger.info("Test tab UI populated successfully.")
            
        except Exception as e:
            logger.critical("Failed to populate test tab", exc_info=True)
            self._lbl_info.setText("ERROR: Failed to generate test images. Check terminal logs.")
    
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
    
    def show_panorama(self, pixmap: QPixmap) -> None:
        """Display the stitched panorama result."""
        self._pano_pixmap = pixmap
        self._view.set_pixmap(pixmap)
        
        for b in self._thumb_btns:
            b.setChecked(False)
        
        self._current_idx = -1
        self._lbl_info.setText("Result: stitched panorama from 3 test images")
        self._lbl_size.setText(f"{pixmap.width()}×{pixmap.height()}")


class MainWindow(QMainWindow):
    """
    Main application window with panorama stitching functionality.
    """
    
    def __init__(self):
        super().__init__()
        logger.info("Initializing MainWindow...")
        
        self.setWindowTitle("Panorama Creator")
        self.setMinimumSize(MIN_WINDOW_W, MIN_WINDOW_H)
        self.resize(DEFAULT_WINDOW_W, DEFAULT_WINDOW_H)
        
        # State
        self._paths: list[str] = []
        self._cv_imgs: dict[str, np.ndarray] = {}
        self._pixmaps: dict[str, QPixmap] = {}
        self._panorama_pixmap: QPixmap | None = None
        self._worker: StitchWorker | None = None
        self._stitch_source: str = "main"
        self._active_pbar: QProgressBar | None = None
        self._prog_val: int = 0
        self._prog_dir: int = 1
        
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
        except Exception as e:
            logger.critical("Failed to build UI", exc_info=True)
            raise
    
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
        self._tabs.addTab(self._test_tab, "🧪  Test (3 Images)")
        
        vbox.addWidget(self._tabs)
        
        # Test progress bar (outside tabs)
        self.pbar_test = QProgressBar()
        self.pbar_test.setFixedHeight(20)
        self.pbar_test.setVisible(False)
        vbox.addWidget(self.pbar_test)
        
        self.statusBar().showMessage("Ready — switch to the Test tab for a quick try!")
    
    def _build_main_tab(self) -> QWidget:
        """Build the main panorama creator tab."""
        main_tab = QWidget()
        ml = QVBoxLayout(main_tab)
        ml.setContentsMargins(4, 4, 4, 4)
        ml.setSpacing(6)
        
        # Splitter layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - image list
        left = self._build_left_panel()
        splitter.addWidget(left)
        
        # Right panel - preview and controls
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
        
        # Zoom controls
        zb = QHBoxLayout()
        self.btn_fit = QPushButton("Fit")
        self.btn_100 = QPushButton("100%")
        self.btn_zi = QPushButton("+")
        self.btn_zo = QPushButton("−")
        
        for b in (self.btn_fit, self.btn_100, self.btn_zi, self.btn_zo):
            b.setFixedSize(42, 28)
            zb.addWidget(b)
        
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
        ol.addLayout(self._make_labeled("Mode:", self.combo_mode))
        
        # Confidence spin
        self.spin_conf = QDoubleSpinBox()
        self.spin_conf.setRange(STITCH_CONFIDENCE_MIN, STITCH_CONFIDENCE_MAX)
        self.spin_conf.setValue(DEFAULT_CONFIDENCE)
        self.spin_conf.setSingleStep(STITCH_CONFIDENCE_STEP)
        self.spin_conf.setFixedWidth(100)
        ol.addLayout(self._make_labeled("Confidence:", self.spin_conf))
        
        # Registration resolution spin
        self.spin_reg = QDoubleSpinBox()
        self.spin_reg.setRange(STITCH_REG_RESOL_MIN, STITCH_REG_RESOL_MAX)
        self.spin_reg.setValue(DEFAULT_REG_RESOL)
        self.spin_reg.setSingleStep(STITCH_REG_RESOL_STEP)
        self.spin_reg.setFixedWidth(100)
        ol.addLayout(self._make_labeled("Reg. Resol:", self.spin_reg))
        
        # Compositing resolution spin
        self.spin_comp = QDoubleSpinBox()
        self.spin_comp.setRange(STITCH_COMP_RESOL_MIN, STITCH_COMP_RESOL_MAX)
        self.spin_comp.setValue(DEFAULT_COMP_RESOL)
        self.spin_comp.setSingleStep(STITCH_COMP_RESOL_STEP)
        self.spin_comp.setFixedWidth(100)
        self.spin_comp.setSpecialValueText("Full (−1)")
        ol.addLayout(self._make_labeled("Comp. Resol:", self.spin_comp))
        
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
    def _make_labeled(text: str, widget: QWidget) -> QVBoxLayout:
        """Create a labeled widget layout."""
        v = QVBoxLayout()
        v.addWidget(QLabel(text))
        v.addWidget(widget)
        return v
    
    def _build_toolbar(self) -> None:
        """Build the main toolbar."""
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        
        self._add_toolbar_action(tb, "📁 Add", self.add_images, "Ctrl+O")
        tb.addSeparator()
        self._add_toolbar_action(tb, "▶ Stitch", self._stitch_from_active_tab, "Ctrl+G")
        tb.addSeparator()
        self._add_toolbar_action(tb, "💾 Save", self.save, "Ctrl+Shift+S")
        tb.addSeparator()
        self._add_toolbar_action(tb, "🗑 Clear", self.clear_all)
    
    def _add_toolbar_action(
        self,
        toolbar: QToolBar,
        text: str,
        slot,
        shortcut: str | None = None
    ) -> QAction:
        """Add an action to a toolbar."""
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        toolbar.addAction(action)
        return action
    
    def _build_menu(self) -> None:
        """Build the menu bar."""
        mb = self.menuBar()
        
        # File menu
        fm = mb.addMenu("File")
        fm.addAction("Add Images…", self.add_images, "Ctrl+O")
        fm.addSeparator()
        fm.addAction("Save Panorama…", self.save, "Ctrl+Shift+S")
        fm.addSeparator()
        fm.addAction("Exit", self.close, "Ctrl+Q")
        
        # Edit menu
        em = mb.addMenu("Edit")
        em.addAction("Remove Selected", self.remove_sel)
        em.addAction("Move Up", self.move_up)
        em.addAction("Move Down", self.move_down)
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
    
    def _connect_signals(self) -> None:
        """Connect all UI signals."""
        self.img_list.currentRowChanged.connect(self._preview_selected)
        self.img_list.order_changed.connect(self._sync_order)
        
        self.btn_up.clicked.connect(self.move_up)
        self.btn_dn.clicked.connect(self.move_down)
        self.btn_rm.clicked.connect(self.remove_sel)
        self.btn_clr.clicked.connect(self.clear_all)
        
        self.btn_stitch.clicked.connect(self._stitch_main)
        
        self.btn_fit.clicked.connect(self.view.fit_to_view)
        self.btn_100.clicked.connect(self.view.actual_size)
        self.btn_zi.clicked.connect(self.view.zoom_in)
        self.btn_zo.clicked.connect(self.view.zoom_out)
        
        self._tabs.currentChanged.connect(self._tab_changed)
    
    def _apply_theme(self) -> None:
        """Apply the application stylesheet."""
        self.setStyleSheet(APPLICATION_STYLE)
    
    # ==================== View Helpers ====================
    
    def _active_view(self) -> PanoramaView:
        """Get the currently active panorama view."""
        return self._test_tab._view if self._tabs.currentIndex() == 1 else self.view
    
    def _fit_active(self) -> None:
        self._active_view().fit_to_view()
    
    def _actual_active(self) -> None:
        self._active_view().actual_size()
    
    def _zoomin_active(self) -> None:
        self._active_view().zoom_in()
    
    def _zoomout_active(self) -> None:
        self._active_view().zoom_out()
    
    def _tab_changed(self, idx: int) -> None:
        """Handle tab change - update progress bar visibility."""
        is_stitching = self._worker is not None and self._worker.isRunning()
        self.pbar_test.setVisible(idx == 1 and is_stitching)
        self.pbar.setVisible(idx == 0 and is_stitching)
    
    # ==================== Image Management ====================
    
    def _update_count(self) -> None:
        """Update image count and button states."""
        n = len(self._paths)
        is_busy = self._worker is not None and self._worker.isRunning()
        
        self.lbl_cnt.setText(f"{n} image{'s' if n != 1 else ''}")
        self.btn_stitch.setEnabled(n >= 2 and not is_busy)
        self.btn_stitch.setText(f"▶  Stitch Panorama  ({n} images)")
    
    def add_images(self) -> None:
        """Open file dialog and add selected images."""
        logger.info("User triggered 'Add Images'")
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "", IMAGE_FILTER
        )
        if paths:
            self._load_images(paths)
    
    def _load_images(self, paths: list[str]) -> None:
        """Load images from file paths."""
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
                        f"Cannot read (corrupt/unsupported): {Path(path).name}"
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
                
            except Exception as e:
                logger.error("Error loading image %s", path, exc_info=True)
                self.statusBar().showMessage(f"Failed to load {Path(path).name}")
        
        if added:
            self._update_count()
            self.statusBar().showMessage(
                f"Added {added} image(s).  Total: {len(self._paths)}", 5000
            )
    
    def _sync_order(self) -> None:
        """Synchronize internal path list with widget order."""
        self._paths = self.img_list.get_ordered_paths()
    
    def _preview_selected(self, row: int) -> None:
        """Preview the selected image."""
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
        self.view.set_pixmap(QPixmap())  # Clear preview
        self._panorama_pixmap = None
        self.lbl_info.setText("")
        self.statusBar().showMessage(f"Removed.  Total: {len(self._paths)}")
    
    def clear_all(self) -> None:
        """Clear all loaded images."""
        logger.info("Clearing all images.")
        self._paths.clear()
        self._cv_imgs.clear()
        self._pixmaps.clear()
        self._panorama_pixmap = None
        self.img_list.clear()
        
        self.view.set_pixmap(QPixmap())
        self.lbl_info.setText("")
        self._update_count()
        self.statusBar().showMessage("Cleared.")
    
    # ==================== Stitching ====================
    
    def _get_params(self) -> dict:
        """Get current stitching parameters from UI."""
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
        self.btn_stitch.setEnabled(not busy)
        self._test_tab._btn_stitch.setEnabled(not busy)
        
        if busy:
            self.btn_stitch.setText("⏳  Stitching…")
            self._test_tab._btn_stitch.setText("⏳  Stitching…")
        else:
            self._update_count()
            self._test_tab._btn_stitch.setText("▶  Stitch 3 Test Images")
    
    def _stitch_main(self) -> None:
        """Start stitching from main tab."""
        if len(self._paths) < 2:
            self.statusBar().showMessage("Need at least 2 images to stitch.")
            return
        if self._worker and self._worker.isRunning():
            return
        
        imgs = [self._cv_imgs[p] for p in self._paths]
        self._start_stitch(imgs, "main")
    
    def _stitch_test(self, imgs: list[np.ndarray]) -> None:
        """Start stitching from test tab."""
        if self._worker and self._worker.isRunning():
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
        """Start the stitching worker."""
        self._stitch_source = source
        params = self._get_params()
        self._set_stitching_busy(True)
        
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
        
        self.statusBar().showMessage("Stitching — please wait…")
        
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
    
    def _on_stitch_done(self, ok: bool, msg: str, pano_cv: np.ndarray | None) -> None:
        """Handle stitch completion."""
        self._prog_timer.stop()
        self.pbar.setVisible(False)
        self.pbar_test.setVisible(False)
        self._set_stitching_busy(False)
        
        if ok and pano_cv is not None:
            px = cv_to_qpixmap(pano_cv)
            
            if self._stitch_source == "test":
                self._panorama_pixmap = px
                self._test_tab.show_panorama(px)
            else:
                self._panorama_pixmap = px
                self.view.set_pixmap(px)
                h, w = pano_cv.shape[:2]
                self.lbl_info.setText(f"Panorama  {w}×{h}")
            
            h, w = pano_cv.shape[:2]
            self.statusBar().showMessage(f"Done — panorama {w}×{h} px", 10000)
        else:
            logger.error("Stitching failed: %s", msg)
            self.statusBar().showMessage(f"Stitching failed: {msg}", 10000)
    
    # ==================== Save ====================
    
    def save(self) -> None:
        """Save the current panorama to file."""
        if not self._panorama_pixmap or self._panorama_pixmap.isNull():
            self.statusBar().showMessage("No panorama to save.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Panorama", "panorama.jpg", SAVE_FILTER
        )
        
        if not path:
            return
        
        try:
            logger.info("Saving panorama to: %s", path)
            
            if self._panorama_pixmap.save(path):
                self.statusBar().showMessage(f"Saved → {path}", 5000)
                logger.info("Panorama saved successfully.")
            else:
                logger.error("Qt pixmap.save returned False for %s", path)
                self.statusBar().showMessage(
                    f"Save failed (format mismatch?): {path}", 5000
                )
        except OSError as e:
            logger.error("OS Error saving file", exc_info=True)
            self.statusBar().showMessage(
                f"Save Error (Permissions/Disk space?): {e}", 5000
            )
        except Exception as e:
            logger.error("Unexpected error saving file", exc_info=True)
            self.statusBar().showMessage(f"Save Error: {e}", 5000)
    
    # ==================== About ====================
    
    def _show_about(self) -> None:
        """Show about dialog."""
        logger.info("User viewed 'About'")
        
        QMessageBox.about(
            self,
            "About Panorama Creator",
            "<h3>Panorama Creator</h3>"
            "<p>Version 1.0.0</p>"
            "<p>A panorama stitching application built with:</p>"
            "<ul>"
            "<li>PySide6 for the GUI</li>"
            "<li>OpenCV for image stitching</li>"
            "<li>NumPy for array operations</li>"
            "</ul>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Drag-and-drop image loading</li>"
            "<li>Interactive preview with zoom/pan</li>"
            "<li>Configurable stitching parameters</li>"
            "<li>Built-in test images for quick try</li>"
            "</ul>"
        )
    
    # ==================== Drag & Drop ====================
    
    def dragEnterEvent(self, event) -> None:
        """Accept drag enter if URLs contain local files."""
        if event.mimeData().hasUrls():
            if all(u.isLocalFile() for u in event.mimeData().urls()):
                event.acceptProposedAction()
                return
        event.ignore()
    
    def dragMoveEvent(self, event) -> None:
        """Accept drag move events."""
        event.acceptProposedAction()
    
    def dropEvent(self, event) -> None:
        """Handle file drop."""
        try:
            paths = [
                u.toLocalFile()
                for u in event.mimeData().urls()
                if u.isLocalFile()
            ]
            
            # Filter to image files only
            valid_paths = [p for p in paths if is_valid_image_file(p)]
            
            if valid_paths:
                logger.info("Dropped %d valid image files.", len(valid_paths))
                self._tabs.setCurrentIndex(0)
                self._load_images(valid_paths)
                event.acceptProposedAction()
            else:
                event.ignore()
        except Exception as e:
            logger.error("Error processing drop event", exc_info=True)
            event.ignore()