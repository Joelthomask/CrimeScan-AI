import cv2
import numpy as np
from utils.logger import get_logger
LOG = get_logger()


class NoiseChecker:
    """
    Forensic Noise Facts Extractor (PRE-QC)
    ---------------------------------------
    • No denoising
    • No thresholds
    • No pass/fail
    • Measures noise characteristics only
    • Feeds Intelligence layer
    """

    def __init__(self, verbose=False):
        self.verbose = verbose

    # ------------------------------------------------
    # Core metrics
    # ------------------------------------------------

    def _estimate_noise(self, gray: np.ndarray) -> float:
        """
        Residual-based noise estimate.
        Higher = noisier.
        """
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        residual = cv2.absdiff(gray, blur)
        return float(np.median(residual))

    def _edge_density(self, gray: np.ndarray) -> float:
        """
        Structural complexity estimate.
        Used to protect edges from over-denoising.
        """
        edges = cv2.Canny(gray, 80, 160)
        return float(np.count_nonzero(edges) / edges.size)

    # ------------------------------------------------
    # Public API
    # ------------------------------------------------

    def check(self, image: np.ndarray):
        if not isinstance(image, np.ndarray):
            raise TypeError("Input must be numpy.ndarray")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        noise = self._estimate_noise(gray)
        edges = self._edge_density(gray)

        details = {
            "noise": round(noise, 3),
            "edge_density": round(edges, 4)
        }

        if self.verbose:
            LOG.info(f"[NoiseChecker] noise={noise:.3f}, edge_density={edges:.4f}")

        # ⚠️ Always True → no decisions in QA
        return True, details
