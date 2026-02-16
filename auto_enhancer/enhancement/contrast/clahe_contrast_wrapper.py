import cv2
import os
import numpy as np
import shutil
from utils.logger import log_event


class CLAHEContrastWrapper:
    """
    Forensic-grade CLAHE Contrast Executor (POLICY-DRIVEN)
    ------------------------------------------------------
    ✔ No auto decision
    ✔ No thresholds
    ✔ Executes only what Intelligence requests
    ✔ Luminance-only enhancement
    ✔ Chroma energy restoration
    ✔ Adaptive forensic safety rollback
    """

    def __init__(self):
        pass

    # -------------------------
    # QA METRICS (internal safety only)
    # -------------------------
    def _compute_contrast_metrics(self, gray):
        contrast_std = float(gray.std())
        p5, p95 = np.percentile(gray, (5, 95))
        spread = float(p95 - p5)

        return {
            "std": contrast_std,
            "spread": spread
        }

    # -------------------------
    # STRENGTH → PARAM MAP
    # -------------------------
    def _map_strength(self, strength: str, params: dict):

        # defaults (policy may override)
        clip = params.get("clip", None)
        grid = params.get("grid", (8, 8))
        blend = params.get("blend", 0.70)

        if clip is not None:
            return clip, grid, blend

        strength = strength.lower()

        if strength == "extreme":
            return 2.4, (8, 8), 0.72

        elif strength == "high":
            return 2.0, (8, 8), 0.70

        elif strength == "medium":
            return 1.5, (8, 8), 0.68

        elif strength == "low":
            return 1.2, (8, 8), 0.65

        else:
            return None, None, None

    # -------------------------
    # MAIN EXECUTOR
    # -------------------------
    def enhance_contrast(
        self,
        input_path: str,
        output_path: str,
        strength: str = "medium",
        params: dict = None
    ) -> str:

        params = params or {}

        log_event("CONTRAST", f"Executor running → strength={strength.upper()}")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input image not found: {input_path}")

        img = cv2.imread(input_path)
        if img is None:
            raise ValueError(f"Failed to read image file: {input_path}")

        gray_before = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        metrics_before = self._compute_contrast_metrics(gray_before)

        log_event(
            "CONTRAST",
            f"[QA] Before | std={metrics_before['std']:.2f} spread={metrics_before['spread']:.2f}"
        )

        clip, grid, blend = self._map_strength(strength, params)

        # ---- TRUE SKIP ----
        if clip is None:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(input_path, output_path)
            log_event("CONTRAST", "Skipped (policy strength=None)")
            return output_path

        # -------------------------
        # CLAHE ON L CHANNEL
        # -------------------------
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid)
        cl = clahe.apply(l)

        # -------------------------
        # LUMINANCE BLEND
        # -------------------------
        l_final = cv2.addWeighted(cl, blend, l, 1 - blend, 0)
        merged = cv2.merge((l_final, a, b))
        enhanced_img = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        # -------------------------
        # CHROMA ENERGY RESTORE
        # -------------------------
        hsv_orig = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hsv_enh = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2HSV)

        h, s_new, v = cv2.split(hsv_enh)
        _, s_orig, _ = cv2.split(hsv_orig)

        s_final = cv2.addWeighted(s_new, 0.6, s_orig, 0.4, 0)
        hsv_final = cv2.merge((h, s_final, v))
        enhanced_img = cv2.cvtColor(hsv_final, cv2.COLOR_HSV2BGR)

        # -------------------------
        # AFTER METRICS
        # -------------------------
        gray_after = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2GRAY)
        metrics_after = self._compute_contrast_metrics(gray_after)

        log_event(
            "CONTRAST",
            f"[QA] After  | std={metrics_after['std']:.2f} spread={metrics_after['spread']:.2f}"
        )

        # -------------------------
        # FORENSIC SAFETY ROLLBACK
        # -------------------------
        min_gain = 1.03 if metrics_before["std"] < 35 else 1.01

        if metrics_after["std"] < metrics_before["std"] * min_gain:
            log_event("CONTRAST", "Weak improvement → rollback", "WARN")
            enhanced_img = img

        if metrics_after["std"] > 95:
            log_event("CONTRAST", "Over-contrast detected → rollback", "WARN")
            enhanced_img = img

        # -------------------------
        # SAVE
        # -------------------------
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, enhanced_img)

        log_event("CONTRAST", "Executor completed")
        return output_path
