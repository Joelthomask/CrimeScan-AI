import numpy as np
import torch
from auto_enhancer.quality_assessment.QualityChecker.post_qc.FAN.face_alignment.api import FaceAlignment, LandmarksType
from utils.logger import get_logger
LOG = get_logger()



class FANPoseChecker:
    """
    FAN-based pose checker (FACTS ONLY)

    ✔ High-precision landmarks
    ✔ QA layer only
    ✔ No cropping output
    ✔ No image modification
    ✔ Returns yaw / pitch / roll facts
    """

    def __init__(self, device=None, verbose=False):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.verbose = verbose
        self.fa = FaceAlignment(LandmarksType.TWO_D, device=self.device)

    # ============================================================
    # Public API
    # ============================================================

    def analyze(self, image):
        """
        Args:
            image (np.ndarray)

        Returns:
            dict:
                {
                    "ok": bool,
                    "yaw": float,
                    "pitch": float,
                    "roll": float,
                    "landmarks": {
                        left_eye, right_eye, nose, mouth_left, mouth_right
                    }
                }
        """

        landmarks = self.fa.get_landmarks_from_image(image)

        if landmarks is None or len(landmarks) == 0:
            if self.verbose:
                LOG.info("[FAN] No face detected")
            return None

        pts = np.array(landmarks[0])  # (68,2)

        # ---------- Extract stable keypoints ----------
        left_eye = np.mean(pts[36:42], axis=0)
        right_eye = np.mean(pts[42:48], axis=0)
        nose = pts[30]
        mouth_left = pts[48]
        mouth_right = pts[54]
        mouth_center = np.mean(pts[48:68], axis=0)

        # ---------- Compute pose ----------
        roll = self._compute_roll(left_eye, right_eye)
        yaw, pitch = self._approx_yaw_pitch(left_eye, right_eye, nose)

        if self.verbose:
            LOG.info(f"[FAN] yaw={yaw:.2f}, pitch={pitch:.2f}, roll={roll:.2f}")

        return {
            "yaw": round(float(yaw), 2),
            "pitch": round(float(pitch), 2),
            "roll": round(float(roll), 2),
            "landmarks": {
                "left_eye": tuple(left_eye.astype(int)),
                "right_eye": tuple(right_eye.astype(int)),
                "nose": tuple(nose.astype(int)),
                "mouth_left": tuple(mouth_left.astype(int)),
                "mouth_right": tuple(mouth_right.astype(int)),
                "mouth_center": tuple(mouth_center.astype(int))
            }
        }

    # ============================================================
    # Math
    # ============================================================

    def _compute_roll(self, left_eye, right_eye):
        lx, ly = left_eye
        rx, ry = right_eye
        return float(np.degrees(np.arctan2(ry - ly, rx - lx)))

    def _approx_yaw_pitch(self, left_eye, right_eye, nose):
        eye_center = (left_eye + right_eye) / 2.0
        dx = right_eye[0] - left_eye[0]

        if abs(dx) < 1e-6:
            return 0.0, 0.0

        yaw = np.degrees(np.arctan2(nose[0] - eye_center[0], dx))
        pitch = np.degrees(np.arctan2(nose[1] - eye_center[1], dx))

        return float(yaw), float(pitch)
