from typing import Optional
from utils.logger import get_logger

from auto_enhancer.intelligence.core.score_builder import ScoreBuilder, QualityScores
from auto_enhancer.intelligence.profiles.forensic_policy import ForensicPolicyEngine
from auto_enhancer.intelligence.profiles.enhancement_policy import EnhancementPolicyEngine


class IntelligenceEngine:

    MODES = ("forensic", "enhancement")

    def __init__(self, mode="forensic"):

        if mode not in self.MODES:
            raise ValueError(f"Invalid mode '{mode}'. Use {self.MODES}")

        self.mode = mode
        self.log = get_logger()

        self.score_builder = ScoreBuilder()

        self.forensic_engine = ForensicPolicyEngine()
        self.enhancement_engine = EnhancementPolicyEngine()

        self.log.info(f"[INTELLIGENCE] Engine initialized | mode={self.mode.upper()}")

    # ============================================================
    # Main entry
    # ============================================================

    def analyze(self, qa_report, round_id: int = 1, qa_results: Optional[dict] = None):
        self.log.info("[INTELLIGENCE]=============INTELLIGENCE LAYER=============")

        self.log.info(f"[INTELLIGENCE] Analysis started | round={round_id}")

        qa_results = qa_results or {}

        scores: QualityScores = self.score_builder.build(qa_report)
        self.log.info("[INTELLIGENCE] Quality scores constructed")

        # Categories come from forensic policy thresholds
        policy_ref = self.forensic_engine
        self.log.info(
            f"[INTELLIGENCE] Policy → "
            f"{policy_ref.POLICY_NAME} v{policy_ref.POLICY_VERSION}"
        )

        blur_lvl = policy_ref.blur_level(scores.sharpness_score)
        bright_lvl = policy_ref.brightness_level(scores.brightness_score)
        noise_lvl = policy_ref.noise_level(scores.noise_score)
        contrast_lvl = policy_ref.contrast_level(scores.contrast_score)
        res_lvl = policy_ref.resolution_level(scores.resolution_score)
        face_lvl = policy_ref.face_usability_level(scores.face_usability)
        overall_lvl = policy_ref.overall_quality_level(scores.overall_quality)

        # ---------- SCORE LOGGING ----------
        self.log.info("[INTELLIGENCE] ---- QUALITY SCORES ----")

        self.log.info(
            f"[INTELLIGENCE] Sharpness      : {scores.sharpness_score:.3f} | level={blur_lvl}"
        )
        self.log.info(
            f"[INTELLIGENCE] Brightness     : {scores.brightness_score:.3f} | level={bright_lvl}"
        )
        self.log.info(
            f"[INTELLIGENCE] Contrast       : {scores.contrast_score:.3f} | level={contrast_lvl}"
        )
        self.log.info(
            f"[INTELLIGENCE] Noise          : {scores.noise_score:.3f} | level={noise_lvl}"
        )
        self.log.info(
            f"[INTELLIGENCE] Resolution     : {scores.resolution_score:.3f} | level={res_lvl}"
        )
        self.log.info(
            f"[INTELLIGENCE] Face usability : {scores.face_usability:.3f} | level={face_lvl}"
        )
        self.log.info(
            f"[INTELLIGENCE] Overall        : {scores.overall_quality:.3f} | level={overall_lvl}"
        )

        faces_block = qa_results.get("faces", {})
        pose = faces_block.get("pose", {})
        largest = faces_block.get("largest_face", {})

        self.log.info("[INTELLIGENCE] ---- FACE FACTS ----")
        self.log.info(f"[INTELLIGENCE] Masked: {largest.get('masked', False)}")

        self.log.info("[INTELLIGENCE] ---- POSE FACTS ----")

        yaw_val = pose.get("worst_yaw")
        pitch_val = pose.get("worst_pitch")
        roll_val = pose.get("worst_roll")

        yaw_str = f"{yaw_val:.2f}" if yaw_val is not None else "None"
        pitch_str = f"{pitch_val:.2f}" if pitch_val is not None else "None"
        roll_str = f"{roll_val:.2f}" if roll_val is not None else "None"

        self.log.info(f"[INTELLIGENCE] Yaw   : {yaw_str}")
        self.log.info(f"[INTELLIGENCE] Pitch : {pitch_str}")
        self.log.info(f"[INTELLIGENCE] Roll  : {roll_str}")




        # Extra forensic interpretation (non-decisional)
        self.log.info(
            "[INTELLIGENCE] SCORE MEANING → "
            "Values near 1.0 = good quality | "
            "Values near 0.0 = poor quality"
        )


        # ---------- Phase ----------
        if round_id == 1:
            self.log.info("[INTELLIGENCE] Phase → STRUCTURAL RECOVERY")
        else:
            self.log.info("[INTELLIGENCE] Phase → COSMETIC REFINEMENT")

        # ---------- 2. Policy ----------
        if self.mode == "forensic":
            self.log.info("[INTELLIGENCE] Applying FORENSIC policy")

            decision = self.forensic_engine.evaluate(scores, qa_results)
            actions = getattr(decision, "recommended_actions", []) or []

            # ============================================================
            # STRUCTURED INTELLIGENCE DECISION REPORT
            # ============================================================

            self.log.info("[INTELLIGENCE] ")
            self.log.info("[INTELLIGENCE] ============================================================")
            self.log.info("[INTELLIGENCE]             INTELLIGENCE DECISION REPORT")
            self.log.info("[INTELLIGENCE] ============================================================")

            # ---------------- SUMMARY ----------------
            self.log.info("[INTELLIGENCE] ")
            self.log.info("[INTELLIGENCE] [DECISION SUMMARY]")
            self.log.info(f"[INTELLIGENCE]      • Mode           : FORENSIC")
            self.log.info(f"[INTELLIGENCE]      • Risk level     : {decision.risk_level}")
            self.log.info(f"[INTELLIGENCE]      • Confidence     : {decision.confidence:.3f}")
            self.log.info(f"[INTELLIGENCE]      • Actions count  : {len(actions)}")

            # ---------------- ACTIONS ----------------
            self.log.info("[INTELLIGENCE] ")

            if actions:
                self.log.info("[INTELLIGENCE] [RECOMMENDED ACTIONS]")

                for i, act in enumerate(actions, 1):
                    self.log.info(f"[INTELLIGENCE]      • Action #{i}")
                    self.log.info(f"[INTELLIGENCE]           Type      : {act.get('type','N/A')}")

                    if "strength" in act:
                        self.log.info(f"[INTELLIGENCE]           Strength  : {act.get('strength')}")

                    if "priority" in act:
                        self.log.info(f"[INTELLIGENCE]           Priority  : {act.get('priority')}")

                    if "params" in act:
                        self.log.info(f"[INTELLIGENCE]           Params    : {act.get('params')}")

                    self.log.info("[INTELLIGENCE] ")

            else:
                self.log.info("[INTELLIGENCE]      • No actions recommended")

            self.log.info("[INTELLIGENCE] ============================================================")

        else:
            self.log.info("[INTELLIGENCE] Applying ENHANCEMENT policy")

            decision = self.enhancement_engine.evaluate(
                scores,
                qa_results=qa_results,
                round_id=round_id
            )

            actions = getattr(decision, "recommended_actions", []) or []

            # ============================================================
            # STRUCTURED INTELLIGENCE DECISION REPORT
            # ============================================================

            self.log.info("[INTELLIGENCE] ")
            self.log.info("[INTELLIGENCE] ============================================================")
            self.log.info("[INTELLIGENCE]             INTELLIGENCE DECISION REPORT")
            self.log.info("[INTELLIGENCE] ============================================================")

            # ---------------- SUMMARY ----------------
            self.log.info("[INTELLIGENCE] ")
            self.log.info("[INTELLIGENCE] [DECISION SUMMARY]")
            self.log.info(f"[INTELLIGENCE]      • Mode           : ENHANCEMENT")
            self.log.info(f"[INTELLIGENCE]      • Confidence     : {decision.confidence:.3f}")
            self.log.info(f"[INTELLIGENCE]      • Actions count  : {len(actions)}")

            if hasattr(decision, "target_quality"):
                self.log.info(f"[INTELLIGENCE]      • Target quality: {decision.target_quality}")

            if hasattr(decision, "risk_level"):
                self.log.info(f"[INTELLIGENCE]      • Risk level    : {decision.risk_level}")

            # ---------------- ACTIONS ----------------
            self.log.info("[INTELLIGENCE] ")

            if actions:
                self.log.info("[INTELLIGENCE] [RECOMMENDED ACTIONS]")

                for i, act in enumerate(actions, 1):
                    self.log.info(f"[INTELLIGENCE]      • Action #{i}")
                    self.log.info(f"[INTELLIGENCE]           Type      : {act.get('type','N/A')}")

                    if "strength" in act:
                        self.log.info(f"[INTELLIGENCE]           Strength  : {act.get('strength')}")

                    if "priority" in act:
                        self.log.info(f"[INTELLIGENCE]           Priority  : {act.get('priority')}")

                    if "params" in act:
                        self.log.info(f"[INTELLIGENCE]           Params    : {act.get('params')}")

                    self.log.info("[INTELLIGENCE] ")

            else:
                self.log.info("[INTELLIGENCE]      • No actions recommended")

            self.log.info("[INTELLIGENCE] ============================================================")


        # ========================================================
        # ✅ ISSUE FLAGS FOR QC UI
        # ========================================================

        obj = qa_results.get("objective_facts", {})
        faces_block = qa_results.get("faces", {})

        pose = faces_block.get("pose", {})
        face = faces_block.get("largest_face", {})



        yaw_raw = pose.get("worst_yaw")
        pitch_raw = pose.get("worst_pitch")
        roll_raw = pose.get("worst_roll")

        yaw = abs(yaw_raw) if yaw_raw is not None else 0
        pitch = abs(pitch_raw) if pitch_raw is not None else 0
        roll = abs(roll_raw) if roll_raw is not None else 0

        quality_flags = {
            "blur_bad": scores.sharpness_score < 0.82,
            "brightness_bad": scores.brightness_score < 0.85,
            "contrast_bad": scores.contrast_score < 0.60,
            "resolution_bad": scores.resolution_score < 0.9,
            "noise_bad": scores.noise_score < 0.75,
            "pose_bad": (yaw > 25 or pitch > 25 or roll > 25),
            "mask_bad": face.get("masked", False)
        }

        d = decision.to_dict()
        d["quality_flags"] = quality_flags


        # ---------- 3. Package ----------
        return {
            "mode": self.mode,
            "round": round_id,
            "scores": scores.to_dict(),
            "decision": d
        }

    # ============================================================
    # Explainability
    # ============================================================

    def explain(self, qa_report, round_id: int = 1, qa_results: Optional[dict] = None):

        result = self.analyze(
            qa_report,
            round_id=round_id,
            qa_results=qa_results
        )

        d = result["decision"]

        lines = []
        lines.append("========== INTELLIGENCE REPORT ==========")
        lines.append(f"Mode        : {result['mode'].upper()}")
        lines.append(f"Round       : {round_id}")
        lines.append(f"Confidence  : {d.get('confidence', 0.0)}")
        lines.append("")

        lines.append("Planned Actions:")
        for i, act in enumerate(d.get("recommended_actions", []), 1):
            lines.append(f"  [{i}] {act}")

        lines.append("=========================================")

        report_text = "\n".join(lines)
        self.log.info("[INTELLIGENCE] Explainable report generated")

        return report_text
