from dataclasses import dataclass
from typing import List, Dict
from auto_enhancer.intelligence.core.score_builder import QualityScores


# ============================================================
# Decision Object
# ============================================================

@dataclass
class EnhancementDecision:
    allow_enhancement: bool
    target_quality: str
    recommended_actions: List[Dict]
    enhancement_notes: List[str]
    confidence: float

    def to_dict(self):
        return self.__dict__


# ============================================================
# Enhancement Policy Engine (Visual Quality Only)
# ============================================================

class EnhancementPolicyEngine:
    """
    Visual quality improvement engine.

    Round-1 → Structural repair
    Round-2 → Cosmetic refinement

    No forensic/recognition logic allowed here.
    """

    def __init__(self):

        self.ULTRA_TARGET = 0.85
        self.HIGH_TARGET = 0.70
        self.MEDIUM_TARGET = 0.50

        self.ROUND2_STOP_QUALITY = 0.82


    # ------------------------------------------------
    # Main evaluation
    # ------------------------------------------------

    def evaluate(
        self,
        scores: QualityScores,
        qa_results: dict,
        round_id: int = 1
    ) -> EnhancementDecision:

        actions = []
        notes = []

        # =================================================
        # 1. Target quality decision
        # =================================================

        if scores.overall_quality >= self.ULTRA_TARGET:
            target = "ULTRA"
            notes.append("Image already high quality.")
        elif scores.overall_quality >= self.HIGH_TARGET:
            target = "HIGH"
            notes.append("Minor improvement possible.")
        elif scores.overall_quality >= self.MEDIUM_TARGET:
            target = "MEDIUM"
            notes.append("Moderate recovery needed.")
        else:
            target = "LOW"
            notes.append("Full restoration needed.")

        # =================================================
        # 2. Round mode
        # =================================================

        aggressive = round_id == 1

        if aggressive:
            notes.append("Round-1 structural repair active.")
        else:
            notes.append("Round-2 cosmetic refinement active.")

            if scores.overall_quality >= self.ROUND2_STOP_QUALITY:
                notes.append("Cosmetic round skipped (quality high).")
                return EnhancementDecision(
                    allow_enhancement=False,
                    target_quality=target,
                    recommended_actions=[],
                    enhancement_notes=notes,
                    confidence=round(min(1.0, 0.55 + (1 - scores.overall_quality)), 3)
                )

        # =================================================
        # 3. Blur / Sharpness
        # =================================================

        s = scores.sharpness_score
        strength = None

        if aggressive:
            if s < 0.30:
                strength = "ultra"
            elif s < 0.50:
                strength = "high"
            elif s < 0.70:
                strength = "medium"
            elif s < 0.82:
                strength = "low"

        if strength:
            actions.append({
                "type": "deblur",
                "strength": strength,
                "priority": 1
            })
            notes.append(f"Deblur scheduled ({strength}).")

        # =================================================
        # 4. Noise Reduction
        # =================================================

        noise = qa_results.get("noise", {}).get("noise")

        if noise is not None:
            if aggressive:
                if noise >= 9:
                    strength = "extreme"
                elif noise >= 6.5:
                    strength = "high"
                elif noise >= 4.5:
                    strength = "medium"
                elif noise >= 3:
                    strength = "low"
                else:
                    strength = None
            else:
                strength = "low" if noise >= 4.5 else None

            if strength:
                actions.append({
                    "type": "denoise",
                    "strength": strength,
                    "priority": 2
                })
                notes.append(f"Denoise scheduled ({strength}).")

        # =================================================
        # 5. Brightness Correction
        # =================================================

        brightness = qa_results.get("brightness", {})
        mean = brightness.get("mean")

        if mean is not None and aggressive:

            if mean < 25:
                level = "EXTREME"
            elif mean < 60:
                level = "DARK"
            elif mean < 118:
                level = "MEDIUM"
            else:
                level = None

            if level:
                actions.append({
                    "type": "brightness",
                    "level": level,
                    "priority": 3
                })
                notes.append(f"Brightness correction ({level}).")

        # =================================================
        # 6. Contrast Enhancement
        # =================================================

        contrast = qa_results.get("contrast", {})
        std = contrast.get("std")
        spread = contrast.get("spread")

        if std is not None and spread is not None:

            strength = None

            if aggressive:
                if std < 22 or spread < 55:
                    strength = "extreme"
                elif std < 32 or spread < 75:
                    strength = "high"
                elif std < 48 or spread < 95:
                    strength = "medium"
                elif std < 60 or spread < 115:
                    strength = "low"
            else:
                if std < 35 or spread < 80:
                    strength = "low"

            if strength:
                actions.append({
                    "type": "contrast",
                    "strength": strength,
                    "priority": 4
                })
                notes.append(f"Contrast enhancement ({strength}).")

        # =================================================
        # 7. Super Resolution
        # =================================================

        if aggressive and scores.resolution_score < 0.70:
            scale = self._decide_scale(scores.resolution_score)

            if scale > 1:
                actions.append({
                    "type": "superres",
                    "scale": scale,
                    "priority": 5
                })
                notes.append(f"Super-resolution x{scale} scheduled.")

        # =================================================
        # 8. Cosmetic-only safety
        # =================================================

        if not aggressive:
            actions = [
                a for a in actions
                if a["type"] in ("brightness", "contrast", "denoise", "deblur")
            ]

        # =================================================
        # 9. Order pipeline
        # =================================================

        actions = sorted(actions, key=lambda x: x["priority"])

        confidence = round(min(1.0, 0.45 + (1 - scores.overall_quality)), 3)

        return EnhancementDecision(
            allow_enhancement=len(actions) > 0,
            target_quality=target,
            recommended_actions=actions,
            enhancement_notes=notes,
            confidence=confidence
        )

    # ------------------------------------------------
    # Resolution scaling logic
    # ------------------------------------------------

    def _decide_scale(self, score: float) -> int:
        if score < 0.35:
            return 4
        elif score < 0.55:
            return 2
        else:
            return 1
