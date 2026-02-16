# =========================================================
# Central AI Engine (Singleton)
# =========================================================

import torch
import time
import tempfile
import os
import numpy as np
import cv2
import io
from contextlib import redirect_stdout, redirect_stderr

from utils.logger import get_logger

_ENGINE = None
NULL = io.StringIO()


class AIEngine:
    _initialized = False

    def __init__(self):
        if AIEngine._initialized:
            raise RuntimeError("AIEngine is a singleton. Use get_ai_engine().")

        AIEngine._initialized = True
        self.LOGGER = get_logger()

        # =====================================================
        # BOOT
        # =====================================================
        self.LOGGER.info("[ENGINE] Boot sequence started")

        if torch.cuda.is_available():
            self.device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            self.LOGGER.info(f"[ENGINE] Device → CUDA ({gpu_name})")
        else:
            self.device = "cpu"
            self.LOGGER.info("[ENGINE] Device → CPU")

        torch.set_grad_enabled(False)

        if self.device == "cuda":
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True
            self.LOGGER.info("[ENGINE] cuDNN optimization enabled")

        # =====================================================
        # LOAD + WARMUP
        # =====================================================
        self._load_models()
        self._warmup()

        self.LOGGER.info("\n[ENGINE] Engine ready")

    # -------------------------------------------------
    # Load all models
    # -------------------------------------------------
    def _load_models(self):
        self.LOGGER.info("[ENGINE] Loading models\n")

        # ---------- SCRFD ----------
        with redirect_stdout(NULL), redirect_stderr(NULL):
            from face_recognition.detection.scrfd.scrfd_wrapper import SCRFDONNXDetector
            from pathlib import Path
            scrfd_path = Path("face_recognition/detection/scrfd/models/scrfd/scrfd_500m.onnx")
            self.live_detector = SCRFDONNXDetector(
                model_path=str(scrfd_path),
                input_size=640,
                conf_thres=0.5,
                nms_thres=0.4
            )
        self.LOGGER.info("[ENGINE] SCRFD loaded")

        # ---------- RetinaFace ----------
        with redirect_stdout(NULL), redirect_stderr(NULL):
            from face_recognition.detection.retinaface_wrapper import FaceDetector
            self.forensic_detector = FaceDetector(network="resnet50")
        self.LOGGER.info("[ENGINE] RetinaFace loaded")

        # ---------- Mask classifier ----------
        with redirect_stdout(NULL), redirect_stderr(NULL):
            from face_recognition.detection.retinaface_wrapper import MaskClassifier
            self.mask_classifier = MaskClassifier()
        self.LOGGER.info("[ENGINE] Mask classifier loaded")

        # ---------- ArcFace ----------
        with redirect_stdout(NULL), redirect_stderr(NULL):
            from face_recognition.embedding.arcface_wrapper import HybridFaceEmbedder
            self.face_embedder = HybridFaceEmbedder()
        self.LOGGER.info("[ENGINE] ArcFace embedder loaded")

        # ---------- GFPGAN ----------
        with redirect_stdout(NULL), redirect_stderr(NULL):
            from auto_enhancer.enhancement.resolution.GFPGAN.gfpgan_wrapper import GFPGANWrapper
            self.face_restorer = GFPGANWrapper()
        self.LOGGER.info("[ENGINE] GFPGAN loaded")

        # ---------- FAN Pose (QA) ----------
        with redirect_stdout(NULL), redirect_stderr(NULL):
            from auto_enhancer.quality_assessment.QualityChecker.post_qc.pose_checker import FANPoseChecker
            self.pose_checker = FANPoseChecker(device=self.device)
        self.LOGGER.info("[ENGINE] FAN pose checker loaded")


        # ---------- HI-DIFF ----------
        try:
            with redirect_stdout(NULL), redirect_stderr(NULL):
                from auto_enhancer.enhancement.deblurring.HI_Diff.hidiff_wrapper import HiDiffWrapper
                self.hidiff = HiDiffWrapper()
            self.LOGGER.info("[ENGINE] HI-DIFF loaded")
        except Exception as e:
            self.hidiff = None
            self.LOGGER.error(f"[ENGINE] HI-DIFF load failed → {e}")

        # ---------- CLIP-IQA ----------
        try:
            with redirect_stdout(NULL), redirect_stderr(NULL):
                from auto_enhancer.quality_assessment.models.clip_iqa import CLIPIQA
                self.clip_iqa = CLIPIQA(device=self.device)
            self.LOGGER.info("[ENGINE] CLIP-IQA loaded")
        except Exception as e:
            self.clip_iqa = None
            self.LOGGER.error(f"[ENGINE] CLIP-IQA load failed → {e}")

    # -------------------------------------------------
    # Warmup (FULL ENGINE)
    # -------------------------------------------------
    def _warmup(self):
        self.LOGGER.info("\n[ENGINE] Warmup started\n")

        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        face = cv2.resize(dummy, (160, 160))

        def timed(label, fn):
            t0 = time.time()
            with redirect_stdout(NULL), redirect_stderr(NULL):
                fn()
            ms = int((time.time() - t0) * 1000)
            self.LOGGER.info(f"[ENGINE] Warmup → {label:<14} {ms:4d} ms")

        with torch.no_grad():

            # ---------- Detection / Recognition ----------
            timed("SCRFD", lambda: self.live_detector.detect(dummy))
            timed("RetinaFace", lambda: self.forensic_detector.detect(dummy))
            timed("Mask", lambda: self.mask_classifier.classify(face))
            timed("ArcFace", lambda: self.face_embedder.get_embedding(face, masked=False))

            # ---------- GFPGAN ----------
            try:
                base = tempfile.gettempdir()
                tmp = os.path.join(base, "gfpgan_warmup.jpg")
                cv2.imwrite(tmp, dummy)

                timed("GFPGAN", lambda: self.face_restorer.enhance_image(
                    tmp,
                    {
                        "cropped_faces": base,
                        "restored_faces": base,
                        "cmp": base,
                        "restored_imgs": base
                    }
                ))

                os.remove(tmp)

            except Exception as e:
                self.LOGGER.warning(f"[ENGINE] GFPGAN warmup skipped → {e}")


            # ---------- HI-DIFF ----------
            if self.hidiff:
                try:
                    small = np.zeros((64, 64, 3), dtype=np.uint8)
                    tmp = os.path.join(tempfile.gettempdir(), "hidiff_warmup.png")
                    cv2.imwrite(tmp, small)

                    t0 = time.time()
                    with redirect_stdout(NULL), redirect_stderr(NULL):
                        self.hidiff.enhance(tmp, silent=True)

                    ms = int((time.time() - t0) * 1000)
                    self.LOGGER.info(f"[ENGINE] Warmup → {'HI-DIFF':<14} {ms:4d} ms")

                    os.remove(tmp)

                except Exception as e:
                    self.LOGGER.warning(f"[ENGINE] HI-DIFF warmup skipped → {e}")

            # ---------- CLIP-IQA ----------
            if self.clip_iqa:
                try:
                    tmp = os.path.join(tempfile.gettempdir(), "clipiqa_warmup.jpg")
                    cv2.imwrite(tmp, dummy)

                    timed("CLIP-IQA", lambda: self.clip_iqa.assess(tmp))

                    os.remove(tmp)

                except Exception as e:
                    self.LOGGER.warning(f"[ENGINE] CLIP-IQA warmup skipped → {e}")

            # ---------- FAN Pose ----------
            try:
                face = cv2.resize(dummy, (256, 256))
                timed("Pose(FAN)", lambda: self.pose_checker.analyze(face))
            except Exception as e:
                self.LOGGER.warning(f"[ENGINE] FAN pose warmup skipped → {e}")


        if self.device == "cuda":
            torch.cuda.synchronize()

    # =====================================================
    # Public API
    # =====================================================

    def detect_live(self, image):
        return self.live_detector.detect(image)

    def detect_forensic(self, image):
        return self.forensic_detector.detect(image)

    def classify_mask(self, face):
        return self.mask_classifier.classify(face)

    def get_embedding(self, face, masked=False):
        return self.face_embedder.get_embedding(face, masked)

    def restore_face(self, img_path, output_dirs, suffix=None):
        return self.face_restorer.enhance_image(img_path, output_dirs, suffix)

    def correct_pose(self, input_path):
        return self.pose_corrector.correct_pose(input_path)

    def assess_quality(self, image_path):
        return self.clip_iqa.assess(image_path)


# =========================================================
# Singleton access
# =========================================================

def get_ai_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = AIEngine()
    return _ENGINE


def init_ai_engine():
    return get_ai_engine()
