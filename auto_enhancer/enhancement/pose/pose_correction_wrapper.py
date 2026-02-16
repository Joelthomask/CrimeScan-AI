import cv2
import numpy as np
from utils.logger import log_event


class PoseCorrector:
    """
    Forensic-safe roll correction module (EXECUTION LAYER).

    ✔ NO detection
    ✔ Uses QA-provided landmarks
    ✔ Full-frame rotation only
    ✔ Recognition-safe guards
    """

    IGNORE_BELOW = 5.0     # degrees (micro tilt ignored)
    MAX_ROTATE = 90.0     # you requested 0–90 support

    # ============================================================
    # Public API
    # ============================================================

    def correct(self, image_path: str, output_path: str, faces: list) -> str:

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")

        if not faces or not isinstance(faces, list):
            log_event("POSE", "No QA faces passed → skipping pose correction")
            cv2.imwrite(output_path, img)
            return output_path

        # ---- Largest face only (forensic standard) ----
        face = max(faces, key=lambda f: f.get("area", 0))
        landmarks = face.get("landmarks")

        if not isinstance(landmarks, dict):
            log_event("POSE", "QA landmarks missing → skipping pose correction")
            cv2.imwrite(output_path, img)
            return output_path

        left_eye = landmarks.get("left_eye")
        right_eye = landmarks.get("right_eye")

        if left_eye is None or right_eye is None:
            log_event("POSE", "Eye landmarks missing → skipping pose correction")
            cv2.imwrite(output_path, img)
            return output_path

        angle = self._compute_roll(left_eye, right_eye)
        log_event("POSE", f"Roll detected → {round(angle, 2)}°")

        # ---- SAFETY ----
        if abs(angle) < self.IGNORE_BELOW:
            log_event("POSE", "Tilt too small → skipped")
            cv2.imwrite(output_path, img)
            return output_path

        if abs(angle) > self.MAX_ROTATE:
            log_event("POSE", "Extreme roll beyond safe cap → skipped")
            cv2.imwrite(output_path, img)
            return output_path

        # ---- EXECUTION ----
        rotated = self._rotate(img, angle)
        cv2.imwrite(output_path, rotated)

        log_event("POSE", f"Pose corrected → {round(angle, 2)}°")
        return output_path

    # ============================================================
    # Internal math
    # ============================================================

    def _compute_roll(self, left_eye, right_eye) -> float:
        lx, ly = left_eye
        rx, ry = right_eye
        return float(np.degrees(np.arctan2(ry - ly, rx - lx)))

    def _rotate(self, img, angle):
        h, w = img.shape[:2]
        center = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        return cv2.warpAffine(
            img,
            M,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE
        )
