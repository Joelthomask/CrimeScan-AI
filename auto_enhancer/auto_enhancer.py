# auto_enhancer/auto_enhancer.py

import os
import time
from pathlib import Path
from datetime import datetime

from utils.logger import init_logger, get_logger, log_event
from utils.temp_manager import get_temp_subpath
from core.ai_engine import get_ai_engine

# ===== FACTS LAYER =====
from auto_enhancer.quality_assessment.core.qa_engine import QualityAssessmentEngine

# ===== INTELLIGENCE LAYER =====
from auto_enhancer.intelligence.core.intelligence_engine import IntelligenceEngine

# ===== ENHANCEMENT MODULES =====
from auto_enhancer.enhancement.deblurring.HI_Diff.hidiff_wrapper import HiDiffWrapper
from auto_enhancer.enhancement.brightness.clahe_brightness_wrapper import CLAHEWrapper
from auto_enhancer.enhancement.contrast.clahe_contrast_wrapper import CLAHEContrastWrapper
from auto_enhancer.enhancement.denoising.nlm_denoiser import NLMWorker
from auto_enhancer.enhancement.pose.pose_correction_wrapper import PoseCorrector
from auto_enhancer.enhancement.resolution.GFPGAN.gfpgan_wrapper import GFPGANWrapper


class AutoEnhancer:
    """
    Auto Enhancer Orchestrator (Forensic + Enhancement Pipeline Core)
    Supports controlled 2-pass enhancement refinement.
    """

    ACTION_MAP = {
        "illumination_correction": "brightness",
        "relight": "brightness",

        "deblur": "deblur",
        "denoise": "denoise",
        "contrast": "contrast",
        "pose": "pose",

        # 🔥 GFPGAN-based super resolution / restoration
        "super_resolution": "super_resolution",
        "face_restore": "super_resolution",
        "gfpgan": "super_resolution",
    }

    MODEL_MAP = {
        "deblur": "HiDiff",
        "brightness": "CLAHE",
        "contrast": "CLAHE",
        "denoise": "NLM",
        "pose": "FaceCorrector",
        "super_resolution": "GFPGAN",
    }

    MAX_ENHANCEMENT_ROUNDS = 2   # 🔒 hard safety limit

    def __init__(self, device="cuda", mode="forensic"):

        try:
            session_root = get_temp_subpath("").parent
            init_logger(session_root)
        except Exception:
            pass

        self.log = get_logger()
        self.device = device
        self.mode = mode.lower()

        # ---- Core systems ----
        self.qa = QualityAssessmentEngine(device=device)
        self.brain = IntelligenceEngine(mode=self.mode)

        # ---- Central AI engine ----
        self.ai = get_ai_engine()

        # ---- Enhancement modules ----
        self.deblurrer = HiDiffWrapper()
        self.brightness = CLAHEWrapper()
        self.contrast = CLAHEContrastWrapper()
        self.pose_corrector = PoseCorrector()
        self.gfpgan = GFPGANWrapper()







        log_event("ENGINE", f"AutoEnhancer ready | mode={self.mode} | device={device}")

    # =====================================================
    # PUBLIC ENTRY
    # =====================================================
    # =====================================================
    # GLOBAL INPUT NORMALIZATION  🔥
    # =====================================================

    def _normalize_input_image(self, image_path: str, max_side=1024) -> str:
        """
        Global forensic normalization.
        • Caps resolution
        • Ensures consistent working domain
        • All QA + enhancement uses this output
        """

        import cv2

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")

        h, w = img.shape[:2]
        long_side = max(h, w)

        if long_side > max_side:
            scale = max_side / long_side
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

            log_event(
                "ENGINE",
                f"Global normalize → {w}x{h} → {new_w}x{new_h}"
            )

        out_dir = get_temp_subpath("normalized")
        out_path = os.path.join(out_dir, os.path.basename(image_path))

        cv2.imwrite(out_path, img)
        return out_path
    # =====================================================
    # QC ONLY STAGE (for QC UI preview)
    # =====================================================

    def run_qc_stage(self, image_path: str):
        """
        Runs:
        - global normalization
        - 🔒 forensic guard baseline recognition (NEW)
        - initial QA
        - first intelligence analysis

        NO enhancement is applied here.
        QC UI can be shown while QA runs.
        """

        from auto_enhancer.forensic_guard.forensic_guard import ForensicGuard
        import cv2

        image_path = os.path.abspath(image_path)

        # ---------- GLOBAL NORMALIZATION ----------
        image_path = self._normalize_input_image(image_path)



        # =====================================================
        # 🔒 FORENSIC GUARD BASELINE (BEFORE QA)  🔥
        # =====================================================

        guard_on = getattr(self, "forensic_guard_enabled", False)

        if guard_on:
            log_event("GUARD", "Forensic Safety Guard → ENABLED")
            guard = ForensicGuard(device=self.device)

            base_img = cv2.imread(image_path)
            guard.start_case(base_img)

            # 🔒 store guard for reuse in AutoEnhancer
            self._forensic_guard = guard

        else:
            log_event("GUARD", "Forensic Safety Guard → DISABLED (QC stage)")

        # =====================================================
        # INITIAL QA (may be slow — UI already redirected)
        # =====================================================
        log_event("ENGINE", "QUALITY ASSESSMENT STARTED")
        qa_before = self.qa.assess(image_path)
        self.log.info("\n" + qa_before.to_console_report("INITIAL"))

        log_event("ENGINE", "QUALITY ASSESSMENT COMPLETED")
        intel = self.brain.analyze(
            qa_before,
            round_id=1,
            qa_results=qa_before.to_dict()   # ✅ FIXED
        )
        self.last_qa_obj = qa_before


        # 🔥 STORE FOR BACKEND/QC UI
        self.last_intelligence = intel
        self.last_qa = qa_before.to_dict()


        return self.last_qa, self.last_intelligence



    def run_full_pipeline(self, image_path: str, step_callback=None):

        from auto_enhancer.forensic_guard.forensic_guard import ForensicGuard
        import cv2
        import os
        import time

        start_total = time.time()
        start_total = time.time()
        step_timings = []

        image_path = os.path.abspath(image_path)

        # ---------- GLOBAL NORMALIZATION ----------
        image_path = self._normalize_input_image(image_path)
        log_event("ENGINE", f"Normalized input → {image_path}")

        log_event("ENGINE", "===========================AUTO-ENHANCEMENT STARTED===========================")
        log_event("ENGINE", f"Input → {image_path}")

        # =====================================================
        # 🔒 FORENSIC GUARD SETUP
        # =====================================================

        guard_on = getattr(self, "forensic_guard_enabled", False)
        guard = None

        if guard_on:
            log_event("GUARD", "Forensic Safety Guard → ENABLED")
            guard = getattr(self, "_forensic_guard", None)

            if guard:
                log_event("GUARD", "Reusing forensic guard from QC stage")
                log_event("GUARD", f"Baseline recognition score → {round(guard.best_score,4)}")
        else:
            log_event("GUARD", "Forensic Safety Guard → DISABLED (raw pipeline)")

        # =====================================================
        # INITIAL QA (ONLY ONCE)
        # =====================================================

        current_path = image_path

        if self.mode == "forensic" and hasattr(self, "last_qa_obj"):
            current_qa = self.last_qa_obj
        else:
            current_qa = self.qa.assess(image_path)

        current_faces = current_qa.faces.get("faces", [])

        # =====================================================
        # PLAN ONCE
        # =====================================================

        if self.mode == "forensic" and hasattr(self, "last_intelligence"):
            intel = self.last_intelligence
        else:
            intel = self.brain.analyze(
                current_qa,
                round_id=1,
                qa_results=current_qa.to_dict()
            )
            self.last_intelligence = intel

        decision = intel.get("decision", {})
        plan = decision.get("recommended_actions", [])

        self._log_intelligence_plan(decision, 1)

        if not plan:
            log_event("ENGINE", "No enhancement plan. Exiting.")
            return current_path

        # =====================================================
        # EXECUTE PLAN SEQUENTIALLY
        # =====================================================

        for step in plan:

            raw_type = step["type"]
            step_type = self.ACTION_MAP.get(raw_type, raw_type)

            stage_start = time.time()

            if step_type == "deblur":
                out = self._run_deblur(current_path, step)

            elif step_type == "super_resolution":
                out = self._run_superres(current_path)


            elif step_type == "brightness":
                out = self._run_brightness(current_path, step)

            elif step_type == "contrast":
                out = self._run_contrast(current_path, step)

            elif step_type == "denoise":
                out = self._run_denoise(current_path, step)

            elif step_type == "pose":
                out = self._run_pose(current_path, current_faces)

            else:
                continue

            elapsed = round(time.time() - stage_start, 2)
            log_event("AUTO-ENHANCER", f"{step_type.upper()} completed in {elapsed}s")

            step_timings.append((step_type, elapsed))

            # =====================================================
            # 🔒 FORENSIC SAFETY CHECK
            # =====================================================

            if guard:
                before_img = cv2.imread(current_path)
                after_img = cv2.imread(out)

                model_name = self.MODEL_MAP.get(step_type, "Unknown")

                accepted, decision = guard.check_step(
                    step_type,
                    before_img,
                    after_img,
                    model_name=model_name
                )


                self.last_guard_result = {
                    "step": step_type,
                    "accepted": accepted,
                    "before_similarity": decision.before_similarity,
                    "after_similarity": decision.after_similarity,
                    "delta_similarity": decision.delta_similarity,
                }

                # ❌ REJECTED → notify once
                if not accepted:
                    if step_callback:
                        step_callback(step_type, current_path)
                    continue

            # ---------- ACCEPTED OUTPUT ----------
            current_path = out

            # ✅ SINGLE CALLBACK
            if step_callback:
                step_callback(step_type, current_path)

        # =====================================================
        # FINISH
        # =====================================================

        total_time = round(time.time() - start_total, 2)

        log_event("ENGINE", "")
        log_event("ENGINE", "="*60)
        log_event("ENGINE", "        ENHANCEMENT TIMING SUMMARY")
        log_event("ENGINE", "="*60)

        for name, t in step_timings:
            log_event("ENGINE", f"• {name.upper():<15}: {t:.2f} s")

        log_event("ENGINE", "")
        log_event("ENGINE", f"• Total enhancement time : {total_time:.2f} s")
        log_event("ENGINE", "="*60)

        log_event("ENGINE", f"UI AUTO-PIPELINE FINISHED in {total_time}s")

        log_event("ENGINE", "============================================================")
        # 🔒 Guard final summary
        if guard:
            guard.log_case_summary()

        return current_path


    def enhance(self, image_path: str):

        start_total = time.time()
        image_path = os.path.abspath(image_path)
        # ---------- GLOBAL NORMALIZATION ----------
        image_path = self._normalize_input_image(image_path)
        log_event("ENGINE", f"Normalized input → {image_path}")


        log_event("ENGINE", "============================================================")
        log_event("ENGINE", "AUTO-ENHANCEMENT PIPELINE STARTED")
        log_event("ENGINE", f"Input → {image_path}")

        report = {
            "meta": {
                "input_image": image_path,
                "mode": self.mode,
                "started_at": datetime.now().isoformat()
            },
            "quality_before": None,
            "intelligence": [],
            "steps": [],
            "outputs": {},
            "quality_after": None,
            "final_image": None
        }

        # =====================================================
        # 1. INITIAL QA
        # =====================================================

        log_event("QA", "Initial quality assessment started")
        qa_before = self.qa.assess(image_path)
        report["quality_before"] = qa_before.to_dict()
        log_event("QA", "Initial quality assessment completed")

        self.log.info("\n" + qa_before.to_console_report("INITIAL"))

        # =====================================================
        # 2. ENHANCEMENT ROUNDS
        # =====================================================

        current_path = image_path
        current_qa = qa_before
        current_faces = qa_before.faces.get("faces", []) 
        rounds = 1 if self.mode == "forensic" else self.MAX_ENHANCEMENT_ROUNDS

        for round_id in range(1, rounds + 1):

            log_event("ENGINE", f"---------- ENHANCEMENT ROUND {round_id} ----------")

            # 🔥 round-aware intelligence
            intel = self.brain.analyze(
            current_qa,
            round_id=round_id,
            qa_results=current_qa.objective
            )


            report["intelligence"].append(intel)

            decision = intel.get("decision", {})
            plan = decision.get("recommended_actions", [])

            self._log_intelligence_plan(decision, round_id)

            if not plan:
                log_event("ENGINE", f"No actions in round {round_id}. Stopping early.")
                break

            # ---------- EXECUTE PLAN ----------
            for idx, step in enumerate(plan, 1):

                raw_type = step["type"]
                step_type = self.ACTION_MAP.get(raw_type, raw_type)

                log_event(
                    "AUTO-ENHANCER",
                    f"[R{round_id}] STEP {idx}/{len(plan)} → {raw_type.upper()} mapped to {step_type.upper()}"
                )

                stage_start = time.time()

                if step_type == "deblur":
                    current_path = self._run_deblur(current_path, step)


                elif step_type == "super_resolution":
                    current_path = self._run_superres(current_path)

                elif step_type == "brightness":
                    current_path = self._run_brightness(current_path, step)

                elif step_type == "contrast":
                    current_path = self._run_contrast(current_path, step)
                elif step_type == "denoise":
                    current_path = self._run_denoise(current_path, step)


                elif step_type == "pose":
                    current_path = self._run_pose(current_path, current_faces)

                else:
                    log_event("AUTO-ENHANCER", f"Unknown step ignored → {step_type}", level="WARNING")
                    continue

                elapsed = round(time.time() - stage_start, 2)

                report["steps"].append({
                    "round": round_id,
                    "type": step_type,
                    "output": current_path,
                    "time": elapsed
                })

                log_event("AUTO-ENHANCER", f"{step_type.upper()} completed in {elapsed}s")

            # ---------- QA AFTER ROUND ----------
            current_qa = self.qa.assess(current_path)
            current_faces = current_qa.faces.get("faces", [])   # 🔥 UPDATE QA FACES
            self.log.info("\n" + current_qa.to_console_report(f"ROUND-{round_id}"))


        # =====================================================
        # 3. FINAL QA
        # =====================================================

        log_event("QA", "Final quality assessment started")
        qa_after = self.qa.assess(current_path)
        report["quality_after"] = qa_after.to_dict()
        report["final_image"] = current_path
        log_event("QA", "Final quality assessment completed")

        self.log.info("\n" + qa_after.to_console_report("FINAL"))

        # =====================================================
        # END PIPELINE
        # =====================================================

        report["meta"]["finished_at"] = datetime.now().isoformat()
        total_time = round(time.time() - start_total, 2)

        log_event("ENGINE", f"AUTO-ENHANCEMENT PIPELINE FINISHED in {total_time}s")
        log_event("ENGINE", "============================================================")

        return report

    # =====================================================
    # INTELLIGENCE LOGGING
    # =====================================================

    def _log_intelligence_plan(self, decision: dict, round_id: int):

        actions = decision.get("recommended_actions", [])

        log_event("INTELLIGENCE", f"[ROUND {round_id}] Allow enhancement → {decision.get('allow_enhancement', True)}")
        log_event("INTELLIGENCE", f"[ROUND {round_id}] Confidence        → {decision.get('confidence', 0.0)}")

        if "risk_level" in decision:
            log_event("INTELLIGENCE", f"[ROUND {round_id}] Risk level        → {decision.get('risk_level')}")
        if "target_quality" in decision:
            log_event("INTELLIGENCE", f"[ROUND {round_id}] Target quality    → {decision.get('target_quality')}")

        if not actions:
            log_event("INTELLIGENCE", f"[ROUND {round_id}] Planned actions   → None")
            return

        log_event("INTELLIGENCE", f"[ROUND {round_id}] Planned actions   → {len(actions)} stages")

        for i, act in enumerate(actions, 1):
            step = act.get("type", "unknown").upper()
            extras = ", ".join([f"{k}={v}" for k, v in act.items() if k != "type"])
            log_event("INTELLIGENCE", f"  [{i}] {step:<10} | {extras}")

    # =====================================================
    # MODULE EXECUTORS
    # =====================================================

    def _run_deblur(self, image_path, step):
        log_event("ENGINE", f"DEBLUR stage started (HI-DIFF) | strength={step.get('strength')}")

        return self.deblurrer.enhance(
            image_path,
            strength=step.get("strength", "medium")
        )


    def _run_superres(self, image_path):
        if not self.gfpgan:
            self.log.warning("GFPGAN not initialized — skipping")
            return image_path

        out_dir = get_temp_subpath("superres")

        return self.gfpgan.enhance_image(
            image_path,
            {
                "cropped_faces": out_dir,
                "restored_faces": out_dir,
                "cmp": out_dir,
                "restored_imgs": out_dir,
            }
        )



    def _run_pose(self, image_path, faces):
        log_event("ENGINE", "POSE correction stage started (forensic roll-only)")

        out_dir = get_temp_subpath("autoenhancement/pose")
        os.makedirs(out_dir, exist_ok=True)

        out = os.path.join(out_dir, os.path.basename(image_path))

        # 🔥 PASS QA FACES (WITH LANDMARKS)
        return self.pose_corrector.correct(image_path, out, faces)




    def _run_brightness(self, image_path, step):
        log_event("ENGINE", "BRIGHTNESS enhancement stage started (CLAHE)")

        out_dir = get_temp_subpath("autoenhancement/brightness")
        out = os.path.join(out_dir, os.path.basename(image_path))

        return self.brightness.enhance_brightness(
            image_path,
            out,
            step.get("level"),
            step.get("params", {})
        )


    def _run_contrast(self, image_path, step):
        log_event("ENGINE", "CONTRAST enhancement stage started (CLAHE)")

        out_dir = get_temp_subpath("autoenhancement/contrast")
        out = os.path.join(out_dir, os.path.basename(image_path))

        return self.contrast.enhance_contrast(
            image_path,
            out,
            step.get("strength", "medium"),
            step.get("params", {})
        )


    def _run_denoise(self, image_path, step):
        log_event("ENGINE", "DENOISE stage started (NLM forensic)")

        out_dir = get_temp_subpath("autoenhancement/noise")
        out = os.path.join(out_dir, os.path.basename(image_path))

        strength = step.get("strength", "medium")
        params = step.get("params", {})


        worker = NLMWorker(
            image_path,
            out,
            strength=strength,
            params=params
        )
        worker.run()

        return out

