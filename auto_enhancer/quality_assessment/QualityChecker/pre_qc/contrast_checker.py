# quality_checker/pre_qc/contrast_checker.py

import cv2
import numpy as np
from utils.logger import get_logger
LOG = get_logger()


class ContrastChecker:
    """
    FACTS layer – Contrast Quality Checker
    --------------------------------------
    Measures contrast-related statistics only.
    No thresholds.
    No decisions.
    No enhancement logic.
    """

    def __init__(self, verbose=False):
        self.verbose = verbose

    def check(self, image):
        """
        Analyze contrast properties of the image.

        Args:
            image (np.ndarray): Input BGR image.

        Returns:
            tuple: (status, details)
                - status  = always True (checker executed)
                - details = contrast metrics
        """
        if not isinstance(image, np.ndarray):
            raise TypeError("Input must be a numpy.ndarray.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        std = float(np.std(gray))
        mean = float(np.mean(gray))
        min_val = int(np.min(gray))
        max_val = int(np.max(gray))

        p5, p95 = np.percentile(gray, (5, 95))
        spread = float(p95 - p5)

        details = {
            "std_dev": std,
            "mean": mean,
            "min": min_val,
            "max": max_val,
            "spread": spread
        }

        if self.verbose:
            LOG.info(
                f"[ContrastChecker][QA] "
                f"std={std:.2f}, spread={spread:.2f}, "
                f"min={min_val}, max={max_val}, mean={mean:.2f}"
            )

        # status=True means "checker executed successfully"
        return True, details
