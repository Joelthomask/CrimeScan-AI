# QualityChecker/pre_qc/brightness_checker.py

import cv2
import numpy as np
from utils.logger import get_logger
LOG = get_logger()

class BrightnessChecker:
    def __init__(self, threshold=50, verbose=False):

        self.threshold = threshold
        self.verbose = verbose

    def check(self, image):
        """
        Check if image brightness is above threshold.

        Args:
            image (np.ndarray): Input BGR image.

        Returns:
            tuple: (status, details)
                - status = True if brightness is acceptable, False otherwise
                - details = {"mean_intensity": float, "threshold": int}
        """
        if not isinstance(image, np.ndarray):
            raise TypeError("Input must be a numpy.ndarray.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_intensity = np.mean(gray)
        std_intensity = float(np.std(gray))
        status = mean_intensity >= self.threshold
        details = {
            "mean_intensity": float(mean_intensity),
            "std_intensity": std_intensity,
            "threshold": self.threshold
        }



        if self.verbose:
            LOG.info(f"[BrightnessChecker] Mean intensity: {mean_intensity:.2f}, "
                  f"Threshold: {self.threshold}, "
                  f"Status: {'Acceptable' if status else 'Low Light'}")

        return status, details
