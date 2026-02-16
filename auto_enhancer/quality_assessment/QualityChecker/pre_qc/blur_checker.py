# QualityChecker/pre_qc/blur_checker.py

import cv2
import numpy as np
from utils.logger import get_logger
LOG = get_logger()


class BlurChecker:
    """
    Forensic Blur Quality Sensor

    Measures:
    • Laplacian variance (local sharpness)
    • Tenengrad energy (edge strength)
    • Edge density (structure presence)

    Outputs:
    • status  → basic pass/fail
    • details → rich blur metrics for Intelligence layer
    """

    def __init__(self, threshold=110.0, verbose=False):
        self.threshold = threshold
        self.verbose = verbose

    # --------------------------------------------------
    # Core metrics
    # --------------------------------------------------

    def _laplacian_var(self, gray):
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def _tenengrad(self, gray):
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        mag = gx * gx + gy * gy
        return float(np.mean(mag))

    def _edge_density(self, gray):
        edges = cv2.Canny(gray, 80, 160)
        return float(np.count_nonzero(edges) / edges.size)

    # --------------------------------------------------
    # Main QA entry
    # --------------------------------------------------

    def check(self, image):
        if not isinstance(image, np.ndarray):
            raise TypeError("Input must be a numpy.ndarray.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image

        lap_var = self._laplacian_var(gray)
        tenengrad = self._tenengrad(gray)
        edge_density = self._edge_density(gray)

        # Basic boolean gate (for legacy compatibility)
        status = lap_var >= self.threshold

        # Normalized sharpness score (0 = unusable, 1 = very sharp)
        sharpness_score = np.clip(
            (lap_var / 300.0) * 0.6 +
            (tenengrad / 8000.0) * 0.3 +
            (edge_density / 0.12) * 0.1,
            0.0, 1.0
        )

        details = {
            "variance": round(lap_var, 2),
            "tenengrad_energy": round(tenengrad, 2),
            "edge_density": round(edge_density, 4),
            "sharpness_score": round(float(sharpness_score), 3),
            "threshold": self.threshold
        }

        if self.verbose:
            LOG.info(
                "[BlurChecker] "
                f"LapVar={lap_var:.1f} | "
                f"Tenengrad={tenengrad:.1f} | "
                f"Edges={edge_density:.4f} | "
                f"Score={sharpness_score:.3f}"
            )

        return status, details
