from dataclasses import dataclass
import time

from auto_enhancer.adaptive_learner.recognition_evaluator import RecognitionEvaluator
from utils.logger import log_event

from typing import Optional

# ============================================================
# Decision Object
# ============================================================

@dataclass
class GuardDecision:
    step_name: str
    before_score: float
    after_score: float
    before_similarity: Optional[float]
    after_similarity: Optional[float]
    model_name: str

    delta_score: float
    delta_similarity: float
    accepted: bool
    elapsed_ms: float


# ============================================================
# Forensic Guard (PERMANENT SAFETY LAYER)
# ============================================================

class ForensicGuard:
    """
    Forensic Safety Gate (Permanent Layer)

    Primary objective:
    - NEVER allow identity similarity to degrade

    Secondary objective:
    - Keep composite forensic stability (final_score)

    This guard MUST remain even when adaptive learning is removed.
    """

    def __init__(
        self,
        device="cpu",
        score_epsilon=0.01,
        similarity_epsilon=0.5  # % tolerance for noise
    ):
        self.device = device
        self.score_epsilon = score_epsilon
        self.similarity_epsilon = similarity_epsilon
        self._baseline_eval = None
        self.actions_tried = 0
        self.actions_accepted = 0
        self.actions_rejected = 0
        self.start_score = 0.0

        self.evaluator = RecognitionEvaluator(device=device)

        # --- persistent state ---
        self.best_report = None
        self.best_score = 0.0
        self.baseline_similarity = 0.0


    # ============================================================
    # Case lifecycle (called ONCE per image)
    # ============================================================

    def start_case(self, image):
        self.actions_tried = 0
        self.actions_accepted = 0
        self.actions_rejected = 0
        self.start_score = self.best_score

        log_event("GUARD", "="*60)
        log_event("GUARD", "        INITIAL FORENSIC GUARD RECOGNITION REPORT")
        log_event("GUARD", "="*60)

        log_event("GUARD", "")
        log_event("GUARD", "[RECOGNITION STATUS]")
        log_event("GUARD", f"     • Recognition started : {time.strftime('%H:%M:%S')}")

        report = self.evaluator.evaluate(image, silent=True)

        self.best_report = report

        best_face = report.best_face
        self.best_score = best_face.final_score if best_face else 0.0
        self.baseline_similarity = best_face.best_similarity if best_face else 0.0

        if not report.faces:
            log_event("GUARD", "     • Status              : No faces detected", level="WARNING")
            log_event("GUARD", "="*60)
            return self.best_score

        log_event("GUARD", f"     • Status              : Completed")
        log_event("GUARD", f"     • Recognition ended   : {time.strftime('%H:%M:%S')}")

        # ---------------- MODEL INFO ----------------
        log_event("GUARD", "")
        log_event("GUARD", "[MODEL INFO]")

        mask_flag = any(f.masked for f in report.faces)
        model_used = "ArcFace" if not mask_flag else "ArcFace (masked pipeline)"

        log_event("GUARD", f"     • Mask detected       : {mask_flag}")
        log_event("GUARD", f"     • Embedding model     : {model_used}")

        # ---------------- DETECTION SUMMARY ----------------
        log_event("GUARD", "")
        log_event("GUARD", "[DETECTION SUMMARY]")
        log_event("GUARD", f"     • Faces detected      : {len(report.faces)}")

        # ---------------- FACE ANALYSIS ----------------
        log_event("GUARD", "")
        log_event("GUARD", "[FACE ANALYSIS]")

        for f in report.faces:
            log_event("GUARD", f"     • Face index          : {f.face_index}")
            log_event("GUARD", f"     • Identity            : {f.best_id}")
            log_event("GUARD", f"     • Best similarity     : {round(f.best_similarity,2)}")
            log_event("GUARD", f"     • Second similarity   : {round(f.second_similarity,2)}")
            log_event("GUARD", f"     • Similarity margin   : {round(f.margin,2)}")
            log_event("GUARD", f"     • Masked              : {f.masked}")
            log_event("GUARD", f"     • Face confidence     : {round(f.face_confidence,2)}")
            log_event("GUARD", f"     • Embedding quality   : {round(f.embedding_quality,2)}")
            log_event("GUARD", f"     • Final score         : {round(f.final_score,4)}")
            log_event("GUARD", "")

        # ---------------- BASELINE METRICS ----------------
        log_event("GUARD", "[BASELINE METRICS]")
        log_event("GUARD", f"     • Baseline similarity : {round(self.baseline_similarity,2)}")
        log_event("GUARD", f"     • Baseline score      : {round(self.best_score,4)}")

        log_event("GUARD", "")
        log_event("GUARD", "="*60)
        log_event("GUARD", "          BASELINE LOCKED FOR CASE")
        log_event("GUARD", "="*60)



    # ============================================================
    # Safety gate (per enhancement)
    # ============================================================
    def check_step(self, step_name, before_image, after_image, model_name="Unknown"):


        t0 = time.time()

        report_after = self.evaluator.evaluate(after_image, silent=True)

        best_face_after = report_after.best_face
        best_face_before = (
            self.best_report.best_face
            if self.best_report and self.best_report.best_face
            else None
        )

        after_score = best_face_after.final_score if best_face_after else 0.0
        before_score = self.best_score

        after_similarity = best_face_after.best_similarity if best_face_after else 0.0
        before_similarity = best_face_before.best_similarity if best_face_before else 0.0

        delta_score = after_score - before_score
        delta_similarity = after_similarity - before_similarity

        # ========================================================
        # 🔐 FORENSIC ACCEPTANCE RULE (CRITICAL FIX)
        # ========================================================

        accepted = (
            after_similarity >= (self.baseline_similarity - self.similarity_epsilon)
            and delta_score >= -self.score_epsilon
        )

        elapsed_ms = (time.time() - t0) * 1000

        decision = GuardDecision(
            step_name=step_name,
            before_score=before_score,
            after_score=after_score,
            before_similarity=before_similarity,
            after_similarity=after_similarity,
            delta_score=delta_score,
            delta_similarity=delta_similarity,
            accepted=accepted,
            elapsed_ms=elapsed_ms,
            model_name=model_name
        )


        # ============================================================
        # FORENSIC STEP REPORT LOGGING
        # ============================================================

        log_event("GUARD", "")
        log_event("GUARD", "="*60)
        log_event("GUARD", f"        ENHANCEMENT STEP REPORT : {step_name.upper()}")
        log_event("GUARD", "="*60)
        log_event("GUARD", "")
        log_event("GUARD", "[MODEL INFO]")
        log_event("GUARD", f"     • Enhancement type : {step_name.upper()}")
        log_event("GUARD", f"     • Model used      : {model_name}")

        log_event("GUARD", "")
        log_event("GUARD", "[STEP INFO]")
        log_event("GUARD", f"     • Step name           : {step_name.upper()}")
        log_event("GUARD", f"     • Processing time     : {round(elapsed_ms,2)} ms")

        log_event("GUARD", "")
        log_event("GUARD", "[SIMILARITY ANALYSIS]")
        log_event("GUARD", f"     • Before similarity   : {round(before_similarity,2)}")
        log_event("GUARD", f"     • After similarity    : {round(after_similarity,2)}")
        log_event("GUARD", f"     • Similarity change   : {round(delta_similarity,2)}")

        log_event("GUARD", "")
        log_event("GUARD", "[SCORE ANALYSIS]")
        log_event("GUARD", f"     • Before score        : {round(before_score,4)}")
        log_event("GUARD", f"     • After score         : {round(after_score,4)}")
        log_event("GUARD", f"     • Score change        : {round(delta_score,4)}")

        log_event("GUARD", "")
        log_event("GUARD", "[FORENSIC DECISION]")
        log_event("GUARD", f"     • Identity preserved  : {after_similarity >= (self.baseline_similarity - self.similarity_epsilon)}")
        log_event("GUARD", f"     • Score acceptable    : {delta_score >= -self.score_epsilon}")
        log_event("GUARD", f"     • Final decision      : {'ACCEPTED' if accepted else 'REJECTED'}")

        if accepted:
            log_event("GUARD", "")
            log_event("GUARD", "     ✅ Enhancement accepted")
            log_event("GUARD", "     • State updated as new forensic reference")
        else:
            log_event("GUARD", "")
            log_event("GUARD", "     ⚠️ Enhancement rejected")
            log_event("GUARD", "     • Rollback to previous forensic state")
            log_event(
                "GUARD",
                "     • Reason             : Identity/score degradation",
                level="WARNING"
            )

        log_event("GUARD", "")
        log_event("GUARD", "="*60)
        log_event("GUARD", "              STEP EVALUATION COMPLETE")
        log_event("GUARD", "="*60)

        # ---------- STATE UPDATE ----------
        if accepted:
            self.best_score = after_score
            self.best_report = report_after
        else:
            log_event(
                "GUARD",
                f"{step_name.upper()} rejected → rollback",
                level="WARNING"
            )
        self.actions_tried += 1

        if accepted:
            self.actions_accepted += 1
        else:
            self.actions_rejected += 1

        return accepted, decision
    def log_case_summary(self):
        net_improvement = self.best_score - self.start_score

        # --- similarity metrics ---
        final_face = (
            self.best_report.best_face
            if self.best_report and self.best_report.best_face
            else None
        )

        final_similarity = (
            final_face.best_similarity if final_face else 0.0
        )

        similarity_improvement = (
            final_similarity - self.baseline_similarity
        )

        log_event("GUARD", "")
        log_event("GUARD", "="*60)
        log_event("GUARD", "          FORENSIC GUARD CASE SUMMARY")
        log_event("GUARD", "="*60)

        log_event("GUARD", f"• Actions tried        : {self.actions_tried}")
        log_event("GUARD", f"• Accepted actions     : {self.actions_accepted}")
        log_event("GUARD", f"• Rejected actions     : {self.actions_rejected}")

        log_event("GUARD", "")
        log_event("GUARD", f"• Best score reached   : {round(self.best_score,4)}")
        log_event("GUARD", f"• Final score          : {round(self.best_score,4)}")
        log_event("GUARD", f"• Net improvement      : {net_improvement:+.4f}")

        log_event("GUARD", "")
        log_event("GUARD", f"• Baseline similarity  : {round(self.baseline_similarity,2)}")
        log_event("GUARD", f"• Final similarity     : {round(final_similarity,2)}")
        log_event("GUARD", f"• Similarity improvement: {similarity_improvement:+.2f}")

        log_event("GUARD", "="*60)
