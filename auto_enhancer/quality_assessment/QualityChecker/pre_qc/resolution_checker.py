import cv2
import numpy as np
from utils.logger import get_logger
LOG = get_logger()

class ResolutionChecker:
    def __init__(self, min_width=100, min_height=100, verbose=False):
        """
        Parameters:
        - min_width, min_height: Minimum acceptable resolution for the image.
        - verbose: bool, if True prints details to the terminal.
        """
        self.min_width = min_width
        self.min_height = min_height
        self.verbose = verbose

    # ---------- Helper Methods ----------
    def _laplacian_variance(self, gray):
        """Sharpness indicator."""
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _estimate_psnr(self, image):
        """Approximate PSNR to detect compression/noise."""
        smoothed = cv2.GaussianBlur(image, (3, 3), 0)
        mse = np.mean((image.astype(np.float32) - smoothed.astype(np.float32)) ** 2)
        if mse == 0:
            return 100.0
        return 10 * np.log10((255 ** 2) / mse)

    def _edge_density(self, gray):
        """Texture/detail measure."""
        edges = cv2.Canny(gray, 100, 200)
        return np.sum(edges > 0) / edges.size

    # ---------- Core Check ----------
    def check(self, image):
        """
        Check if the image resolution and quality are acceptable.

        Args:
            image (np.ndarray): Input BGR image.

        Returns:
            tuple: (status, details)
                - status = True if acceptable, False if needs GFPGAN enhancement
                - details = {"width", "height", "min_width", "min_height",
                             "lap_var", "psnr", "edge_density", "trigger_score"}
        """
        if not isinstance(image, np.ndarray):
            raise TypeError("Input must be a numpy.ndarray.")

        h, w = image.shape[:2]
        status = (w >= self.min_width) and (h >= self.min_height)

        # --- Convert to grayscale for metric analysis ---
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # --- Hybrid Quality Metrics ---
        lap_var = self._laplacian_variance(gray)
        psnr = self._estimate_psnr(image)
        edge_density = self._edge_density(gray)

        # --- Scoring Logic ---
        trigger_score = 0
        if lap_var < 80:
            trigger_score += 1
        if psnr < 25:
            trigger_score += 1
        if edge_density < 0.05:
            trigger_score += 1

        # --- Final decision: hybrid + resolution ---
        if (not status) or (trigger_score >= 2):
            final_status = False  # Needs GFPGAN
        else:
            final_status = True

        # --- Details dict ---
        details = {
            "width": w,
            "height": h,
            "min_width": self.min_width,
            "min_height": self.min_height,
            "lap_var": round(lap_var, 3),
            "psnr": round(psnr, 3),
            "edge_density": round(edge_density, 4),
            "trigger_score": trigger_score
        }

        if self.verbose:
            LOG.info("[ResolutionChecker]")
            LOG.info(f"  • Dimensions: {w}×{h} (Min: {self.min_width}×{self.min_height})")
            LOG.info(f"  • Laplacian Variance: {lap_var:.2f}")
            LOG.info(f"  • PSNR: {psnr:.2f} dB")
            LOG.info(f"  • Edge Density: {edge_density:.4f}")
            LOG.info(f"  • Trigger Score: {trigger_score}")
            LOG.info(f"  • Final Status: {'Acceptable' if final_status else 'Needs Enhancement'}")

        return final_status, details
