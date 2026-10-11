"""
Panorama Creator — Background Stitching Worker
Runs OpenCV stitching in a separate thread to keep UI responsive.
"""

import logging
from typing import Any

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("PanoramaApp.worker")


class StitchWorker(QThread):
    """
    Worker thread for panorama stitching.
    
    Signals:
        done: Emitted when stitching completes with (success, message, panorama_image)
    """
    
    done = Signal(bool, str, object)
    
    # OpenCV Stitcher status codes and messages
    STITCH_ERRORS: dict[int, str] = {
        cv2.Stitcher_ERR_NEED_MORE_IMGS: "Need more images or insufficient overlap.",
        cv2.Stitcher_ERR_HOMOGRAPHY_EST_FAIL: "Homography estimation failed. Try images with more overlap.",
        cv2.Stitcher_ERR_CAMERA_PARAMS_ADJUST_FAIL: "Camera parameter adjustment failed.",
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
                if hasattr(stitcher, 'setWaveCorrectKind'):
                    kind = (
                        cv2.detail.WAVE_CORRECT_HORIZ
                        if self.params["wave_kind"] == "horizontal"
                        else cv2.detail.WAVE_CORRECT_VERT
                    )
                    stitcher.setWaveCorrectKind(kind)
                else:
                    logger.warning(
                        "setWaveCorrectKind not available in this OpenCV version. Skipping."
                    )
            
            # Execute stitching
            logger.debug(
                "Calling cv2.Stitcher.stitch() with %d images...",
                len(self.images)
            )
            status, panorama = stitcher.stitch(self.images)
            
            # Handle result
            if status == cv2.Stitcher_OK:
                h, w = panorama.shape[:2]
                logger.info("Stitching SUCCESS. Output size: %dx%d", w, h)
                self.done.emit(True, "OK", panorama)
            else:
                error_msg = self.STITCH_ERRORS.get(
                    status,
                    f"Unknown OpenCV Stitcher error code: {status}"
                )
                logger.warning("Stitching FAILED. Status: %d - %s", status, error_msg)
                self.done.emit(False, error_msg, None)
                
        except Exception as exc:
            logger.error("Exception inside StitchWorker", exc_info=True)
            self.done.emit(False, f"Worker Exception: {exc}", None)