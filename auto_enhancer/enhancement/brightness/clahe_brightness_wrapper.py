import cv2
import os
import numpy as np
from typing import Optional, Dict

from utils.logger import log_event


class CLAHEWrapper:
    """
    CLAHE Brightness Executor (CLEAN)
    ---------------------------------
    • No quality checks
    • No severity decisions
    • No thresholds
    • Executes only what Intelligence requests

    Intelligence must provide:
        level:   "medium" | "dark" | "extreme"
        params:  dict (optional fine tuning)
    """

    # =====================================================
    # Low-level operators (pure image ops)
    # =====================================================

    def _apply_gamma(self, img, gamma: float):
        inv = 1.0 / gamma
        table = np.array([(i / 255.0) ** inv * 255 for i in range(256)]).astype("uint8")
        return cv2.LUT(img, table)

    def _apply_exposure(self, img, exposure: float):
        return cv2.convertScaleAbs(img, alpha=exposure, beta=0)

    def _lift_shadows(self, img, strength=0.4):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        lut = np.array(
            [min(255, int((i / 255) ** (1 - strength) * 255)) for i in range(256)],
            dtype="uint8"
        )

        l2 = cv2.LUT(l, lut)
        merged = cv2.merge((l2, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def _apply_clahe(self, img, clip=1.4, grid=(8, 8)):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid)
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def _restore_saturation(self, img, boost=1.05):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype("float32")
        h, s, v = cv2.split(hsv)
        s = np.clip(s * boost, 0, 255)
        merged = cv2.merge([h, s, v]).astype("uint8")
        return cv2.cvtColor(merged, cv2.COLOR_HSV2BGR)

    def _safe_save(self, img, out_path):
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        cv2.imwrite(out_path, img)

    # =====================================================
    # Public executor API
    # =====================================================

    def enhance_brightness(
        self,
        input_path: str,
        output_path: str,
        level: str = "medium",
        params: Optional[Dict] = None
    ) -> str:
        """
        Execute brightness enhancement.

        Args:
            input_path: image path
            output_path: save path
            level: "medium" | "dark" | "extreme"
            params: optional override dictionary

        Returns:
            output_path
        """

        img = cv2.imread(input_path)
        if img is None:
            raise ValueError(f"Failed to read image: {input_path}")

        params = params or {}

        log_event("BRIGHTNESS", f"Executor running → level={level.upper()}")

        # =====================================================
        # EXECUTION MODES (NO DECISIONS)
        # =====================================================

        if level == "extreme":

            base = self._apply_exposure(img, params.get("exposure", 1.50))
            shadows = self._lift_shadows(base, params.get("shadow_strength", 0.58))
            local = self._apply_clahe(
                shadows,
                params.get("clahe_clip", 1.3),
                params.get("clahe_grid", (8, 8))
            )

            mixed = cv2.addWeighted(
                shadows, params.get("mix_a", 0.20),
                local, params.get("mix_b", 0.80),
                0
            )

            enhanced = self._restore_saturation(mixed, params.get("saturation", 1.90))

        elif level == "dark":

            base = self._apply_exposure(img, params.get("exposure", 1.38))
            enhanced = self._lift_shadows(base, params.get("shadow_strength", 0.45))
            enhanced = self._restore_saturation(enhanced, params.get("saturation", 1.38))

        else:  # "medium"

            enhanced = self._apply_gamma(img, params.get("gamma", 1.68))
            enhanced = self._restore_saturation(enhanced, params.get("saturation", 1.60))

        # =====================================================
        # SAVE
        # =====================================================

        self._safe_save(enhanced, output_path)
        log_event("BRIGHTNESS", "Executor completed")
        return output_path
