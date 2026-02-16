import cv2
import time
import numpy as np

from utils.logger import get_logger
from auto_enhancer.quality_assessment.core.qa_report import QAReport

# -------- PRE-QC --------
from auto_enhancer.quality_assessment.QualityChecker.pre_qc.blur_checker import BlurChecker
from auto_enhancer.quality_assessment.QualityChecker.pre_qc.brightness_checker import BrightnessChecker
from auto_enhancer.quality_assessment.QualityChecker.pre_qc.contrast_checker import ContrastChecker
from auto_enhancer.quality_assessment.QualityChecker.pre_qc.noise_checker import NoiseChecker
from auto_enhancer.quality_assessment.QualityChecker.pre_qc.resolution_checker import ResolutionChecker
# -------- POST-QC --------
from auto_enhancer.quality_assessment.QualityChecker.post_qc.pose_checker import FANPoseChecker


# -------- AI ENGINE --------
from core.ai_engine import get_ai_engine


class QualityAssessmentEngine:
    """
    FACTS LAYER (QA)

    Responsibilities:
    • Objective image QC
    • Face condition extraction
    • Perceptual quality scoring

    Produces ONLY facts.
    No decisions. No thresholds. No enhancement logic.
    """

    def __init__(self, device="cuda", verbose=False):

        self.device = device
        self.verbose = verbose
        self.log = get_logger()

        # -------- Checkers (FACT EXTRACTORS) --------
        self.blur_checker = BlurChecker(verbose=verbose)
        self.brightness_checker = BrightnessChecker(verbose=verbose)
        self.contrast_checker = ContrastChecker(verbose=verbose)
        self.noise_checker = NoiseChecker(verbose=verbose)
        self.resolution_checker = ResolutionChecker(verbose=verbose)
        self.fan_pose_checker = FANPoseChecker(verbose=verbose)


        # -------- AI Engine --------
        self.ai = get_ai_engine()
        self.detector = self.ai.detect_forensic
        self.mask_classifier = self.ai.classify_mask
        self.clip_iqa = self.ai.clip_iqa

        self.log.info("[QA] Quality Assessment Engine initialized")

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def assess(self, image_path: str) -> QAReport:

        start_total = time.time()
        self.log.info("[QA] Assessment started")

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"[QA] Cannot read image: {image_path}")

        self.log.info("[QA] Step A: image loading")

        report = QAReport(image_path)

        self.log.info("[QA] Step B: running preqc")
        preqc = self._run_preqc(img)
        report.set_objective(preqc)

        self.log.info("[QA] Step C: running face qc")
        faceqc = self._run_face_qc(img)
        report.set_faces(faceqc)

        self.log.info("[QA] Step D: clip IQA")
        report.set_perceptual(self.clip_iqa.assess(image_path))

        self.log.info(f"[QA] Assessment finished ({round(time.time() - start_total, 2)}s)")
        return report


    # =========================================================
    # PRE-QC (PURE IMAGE FACTS)
    # =========================================================

    def _run_preqc(self, img):

        checks = {
            "blur": self.blur_checker,
            "brightness": self.brightness_checker,
            "contrast": self.contrast_checker,
            "noise": self.noise_checker,
            "resolution": self.resolution_checker
        }

        results = {}
        for name, checker in checks.items():
            status, details = checker.check(img)
            results[name] = {"status": status, "details": details}

        # ------------------------------------------------
        # STRUCTURED FORENSIC FACTS (FOR INTELLIGENCE)
        # ------------------------------------------------

        blur_val = results["blur"]["details"].get("variance", 0.0)
        b_mean   = results["brightness"]["details"].get("mean_intensity", 0.0)
        b_std    = results["brightness"]["details"].get("std_intensity", 0.0)

        c_std    = results["contrast"]["details"].get("std_dev", 0.0)
        c_spread = results["contrast"]["details"].get("spread", 0.0)

        noise    = results["noise"]["details"].get("noise", 0.0)
        edges    = results["noise"]["details"].get("edge_density", 0.0)

        res      = results["resolution"]["details"]

        return {

            "blur": {
                "variance": blur_val,
                "status": results["blur"]["status"]
            },

            "brightness": {
                "mean": b_mean,
                "std": b_std,
                "status": results["brightness"]["status"]
            },

            "contrast": {
                "std": c_std,
                "spread": c_spread,
                "status": results["contrast"]["status"]
            },

            "noise": {
                "noise": noise,
                "edge_density": edges,
                "status": results["noise"]["status"]
            },

            "resolution": {
                "width": res.get("width", 0),
                "height": res.get("height", 0),
                "status": results["resolution"]["status"]
            }
        }
    # =========================================================
        # FACE FACTS (NO POSE LOGIC HERE)
            # =========================================================
    def _run_face_qc(self, img):

        import torch

        self.log.info("[FACE QC] Step 1: detector start")
        self.log.info(f"[GPU] Allocated: {torch.cuda.memory_allocated()/1e9:.2f} GB")

        detections = self.detector(img)

        self.log.info(f"[FACE QC] Step 2: detector finished | faces={len(detections)}")

        h, w = img.shape[:2]
        img_area = h * w

        faces = []

        # ---------- PROCESS ALL FACES ----------
        for idx, det in enumerate(detections):

            x1, y1, x2, y2 = det["box"]

            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(w, int(x2))
            y2 = min(h, int(y2))

            if x2 <= x1 or y2 <= y1:
                continue

            face = img[y1:y2, x1:x2]
            if face.size == 0:
                continue

            fh, fw = face.shape[:2]
            if fh < 10 or fw < 10:
                continue

            gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

            blur = cv2.Laplacian(gray, cv2.CV_64F).var()
            brightness = gray.mean()

            label, conf = self.mask_classifier(face)

            faces.append({
                "bbox": [x1, y1, x2, y2],
                "width": fw,
                "height": fh,
                "area_ratio": round((fw * fh) / img_area, 4),
                "blur_variance": round(float(blur), 2),
                "brightness": round(float(brightness), 2),
                "masked": label == "Mask",
                "mask_conf": float(conf),
                "landmarks": det.get("landmarks"),
                "area": fw * fh
            })

        # ---------- RUN FAN ONCE ----------
        self.log.info("[FACE QC] Running FAN pose analysis")

        import torch
        from core.gpu_lock import GPU_LOCK

        # Free temporary detector memory before heavy FAN inference
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

        # ---- Image diagnostics ----
        if img is None:
            self.log.info("[FACE QC] ERROR: image is None before FAN")
        else:
            self.log.info(f"[FACE QC] Image shape before FAN: {img.shape}")
            self.log.info(f"[FACE QC] Image dtype: {img.dtype}")
            self.log.info(f"[FACE QC] Image min/max: {img.min()} / {img.max()}")

        try:
            with GPU_LOCK:
                fan_pose = self.fan_pose_checker.analyze(img)

            self.log.info("[FACE QC] FAN analysis completed")

        except Exception as e:
            self.log.info(f"[FACE QC] FAN crashed: {e}")
            fan_pose = None


        if fan_pose:
            yaw = fan_pose.get("yaw")
            pitch = fan_pose.get("pitch")
            roll = fan_pose.get("roll")

            pose_facts = {
                "source": "FAN",
                "faces": [{
                    "face_id": 0,
                    "status": True,
                    "yaw": yaw,
                    "pitch": pitch,
                    "roll": roll
                }],
                "pose_ok_ratio": 1.0,
                "worst_yaw": abs(yaw) if yaw is not None else None,
                "worst_pitch": abs(pitch) if pitch is not None else None,
                "worst_roll": abs(roll) if roll is not None else None
            }

            if faces:
                faces[0]["landmarks"] = fan_pose.get("landmarks")

        else:
            pose_facts = {
                "source": "FAN",
                "faces": [],
                "pose_ok_ratio": 0.0,
                "worst_yaw": None,
                "worst_pitch": None,
                "worst_roll": None,
                "status": False
            }

        self.log.info(f"[FACE QC] Faces retained: {len(faces)}")

        return {
            "detected": len(faces) > 0,
            "count": len(faces),
            "faces": faces,
            "largest_face": max(faces, key=lambda f: f["area_ratio"]) if faces else None,
            "pose": pose_facts
        }
