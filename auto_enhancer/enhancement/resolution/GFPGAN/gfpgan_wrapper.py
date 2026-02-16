import os
import sys
import types
import torch
import cv2
import numpy as np
import torchvision.transforms.functional as F
from utils.logger import get_logger
LOG = get_logger()

# -------------------------------------------------
# TORCHVISION COMPAT PATCH (for basicsr)
# -------------------------------------------------
module_name = "torchvision.transforms.functional_tensor"
if module_name not in sys.modules:
    fake_mod = types.ModuleType(module_name)
    fake_mod.rgb_to_grayscale = F.rgb_to_grayscale
    sys.modules[module_name] = fake_mod

# -------------------------------------------------
# FORCE LOCAL GFPGAN VISIBILITY
# -------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from auto_enhancer.enhancement.resolution.GFPGAN.gfpgan import GFPGANer



def imwrite(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, img)


class GFPGANWrapper:
    """
    Forensic-grade GFPGAN Wrapper (GATED)
    ------------------------------------
    • Skips clean faces
    • Adaptive severity levels
    • Forensic-safe strength
    • No beautification
    """

    def __init__(self, model_version='1.3', upscale=2, only_center_face=False):
        self.upscale = upscale
        self.only_center_face = only_center_face

        self.repo_root = os.path.dirname(os.path.abspath(__file__))
        self.weights_dir = os.path.join(self.repo_root, "gfpgan", "weights")
        os.makedirs(self.weights_dir, exist_ok=True)

        os.environ["GFPGAN_CACHE_DIR"] = self.weights_dir
        os.environ["FACEXLIB_DATA_DIR"] = self.weights_dir
        os.environ["TORCH_HOME"] = os.path.join(self.weights_dir, "torch_models")
        torch.hub.set_dir(os.path.join(self.weights_dir, "torch_models"))

        model_path = os.path.join(self.weights_dir, "GFPGANv1.3.pth")
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"GFPGAN model not found: {model_path}")

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        LOG.info(f"[GFPGAN] Device → {self.device}")

        self.restorer = GFPGANer(
            model_path=model_path,
            upscale=self.upscale,
            arch='clean',
            channel_multiplier=2,
            bg_upsampler=None,
            device=self.device
        )

    # ---------------- QA ----------------
    def _lap_var(self, gray):
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _estimate_noise(self, gray):
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        residual = cv2.absdiff(gray, blur)
        return float(np.median(residual))
    def _rms_contrast(self, gray):
        return float(gray.std())

    def _sobel_energy(self, gray):
        sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        return float(np.mean(np.sqrt(sx**2 + sy**2)))

    # ---------------- SEVERITY ----------------
    def _classify_face(self, gray):

        lap = self._lap_var(gray)
        noise = self._estimate_noise(gray)
        contrast = self._rms_contrast(gray)
        texture = self._sobel_energy(gray)

        LOG.info(f"[GFPGAN][METRICS] lap={lap:.1f} noise={noise:.2f} "
            f"contrast={contrast:.1f} texture={texture:.2f}")

        # ---------- STRICT FORENSIC GATE ----------

        # clean / good enrollment / phone selfies
        if lap > 140 and contrast > 35 and texture > 12:
            return "good"

        # clearly degraded but not destroyed
        if lap > 70 and contrast > 20:
            return "high"

        # very poor structure (blurred / foggy / CCTV / resized)
        return "extreme"

    def _weight_map(self, level):
        return {
            "high":    0.12,
            "extreme": 0.22
        }.get(level, 0.0)



    # ---------------- MAIN ----------------
    def enhance_image(self, img_path, output_dirs):

        img_name = os.path.basename(img_path)
        basename, _ = os.path.splitext(img_name)

        input_img = cv2.imread(img_path)
        if input_img is None:
            raise FileNotFoundError(img_path)

        for folder in output_dirs.values():
            os.makedirs(folder, exist_ok=True)

        LOG.info(f"[GFPGAN] Processing {img_name}")

        cropped_faces, restored_faces, restored_img = self.restorer.enhance(
            input_img,
            has_aligned=False,
            only_center_face=self.only_center_face,
            paste_back=True,
            weight=0.4  # temporary, will override logic by gating
        )

        final_img = input_img.copy()
        any_used = False

        for idx, (crop, restored) in enumerate(zip(cropped_faces, restored_faces)):

            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            lap = self._lap_var(gray)
            noise = self._estimate_noise(gray)
            level = self._classify_face(gray)

            LOG.info(f"[GFPGAN][QA] Face {idx} {w}x{h} | blur={lap:.1f} | noise={noise:.2f} → {level.upper()}")

            if level == "good":
                LOG.info(f"[GFPGAN] Face {idx} skipped")
                continue

            any_used = True
            alpha = self._weight_map(level)

            restored = cv2.resize(restored, (crop.shape[1], crop.shape[0]))
            blended = cv2.addWeighted(restored, alpha, crop, 1 - alpha, 0)

            imwrite(crop, os.path.join(output_dirs['restored_faces'], f"{basename}_{idx:02d}_crop.png"))
            imwrite(blended, os.path.join(output_dirs['restored_faces'], f"{basename}_{idx:02d}_{level}.png"))

        if any_used:
            out_path = os.path.join(output_dirs['restored_imgs'], f"{basename}_gfpgan.png")
            imwrite(restored_img, out_path)
            LOG.info("[GFPGAN] Applied & saved")
            return out_path

        else:
            out_path = os.path.join(output_dirs['restored_imgs'], f"{basename}_skipped.png")
            imwrite(input_img, out_path)
            LOG.info("[GFPGAN] Skipped all faces")
            return out_path
