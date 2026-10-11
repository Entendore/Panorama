#!/usr/bin/env python3
"""
Panorama Creator — Entry Point
PySide6 + OpenCV panorama stitching application.
"""

import sys
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)-8s [%(threadName)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S"
)

from PySide6.QtWidgets import QApplication


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Log unhandled exceptions before default handler."""
    logger = logging.getLogger("PanoramaApp")
    logger.critical("Unhandled Exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = log_unhandled_exception


def main() -> None:
    """Application entry point."""
    logger = logging.getLogger("PanoramaApp")
    logger.info("Application starting...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Panorama Creator")
    app.setApplicationVersion("1.0.0")
    
    try:
        # Lazy import to allow graceful error handling
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.critical(
                "Missing packages. Install with: pip install opencv-python numpy PySide6"
            )
            sys.exit("Missing packages. Install with:\n  pip install opencv-python numpy PySide6")
        
        from window import MainWindow
        win = MainWindow()
        win.show()
        
        logger.info("Executing application event loop...")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical("Fatal error during startup or execution", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()