from dataclasses import dataclass
from typing import List, Dict
from auto_enhancer.intelligence.core.score_builder import QualityScores
from typing import Optional
import json
import os

# ============================================================
# Decision Object
# ============================================================

@dataclass
class ForensicDecision:
    allow_enhancement: bool
    risk_level: str                 # SAFE | MODERATE | CRITICAL
    recommended_actions: List[Dict]
    forensic_notes: List[str]
    confidence: float

    def to_dict(self):
        return self.__dict__


# ============================================================
# Forensic Policy Engine (Recognition-First)
# ============================================================

class ForensicPolicyEngine:

    POLICY_NAME = "Forensic Recognition Policy"
    POLICY_VERSION = "1.0"



    def __init__(self):
        self.SAFE_QUALITY = 0.78
        self.MODERATE_QUALITY = 0.55
        self.learned_policy = self._load_learned_policy()

    def evaluate(self, scores: QualityScores, qa_results: dict) -> ForensicDecision:

        actions = []
        notes = []

        notes.append("=== FORENSIC MODE ACTIVE ===")
        notes.append("Goal → Maximize face recognition confidence")

        # =================================================
        # 1. RISK
        # =================================================

        if scores.overall_quality >= self.SAFE_QUALITY:
            risk = "SAFE"
        elif scores.overall_quality >= self.MODERATE_QUALITY:
            risk = "MODERATE"
        else:
            risk = "CRITICAL"

        # =================================================
        # 2. POSE CHECK
        # =================================================

        faces_block = qa_results.get("faces", {})
        pose_facts = faces_block.get("pose", {})

        worst_roll = pose_facts.get("worst_roll")

        if worst_roll is not None:
            R = abs(worst_roll)

            if R >= 7:
                actions.append({"type": "pose", "priority": 0})

        # =================================================
        # 3. BRIGHTNESS (CATEGORY NORMALIZED)
        # =================================================

        b = scores.brightness_score

        # Category mapping now consistent:
        # LOW brightness   -> strong correction needed
        # MEDIUM brightness -> moderate correction
        # HIGH brightness  -> mild correction

        if b < 0.45:
            actions.append({
                "type": "brightness",
                "level": "LOW",
                "params": {
                    "exposure": 1.32,
                    "shadow": 0.55,
                    "clahe": True,
                    "clahe_clip": 1.18,
                    "mix": (0.35, 0.65),
                    "saturation": 1.08
                },
                "priority": 1
            })

        elif b < 0.75:
            actions.append({
                "type": "brightness",
                "level": "MEDIUM",
                "params": {
                    "exposure": 1.20,
                    "shadow": 0.38,
                    "clahe": False,
                    "saturation": 1.06
                },
                "priority": 1
            })

        elif b < 0.95:
            actions.append({
                "type": "brightness",
                "level": "HIGH",
                "params": {
                    "gamma": 1.22,
                    "saturation": 1.03
                },
                "priority": 1
            })

        # =================================================
        # 4. CONTRAST
        # =================================================

        if scores.contrast_score < 0.55:
            actions.append({
                "type": "contrast",
                "priority": 2,
                "params": {
                    "mode": "clahe",
                    "clip_limit": 1.8,
                    "tile_grid": (8, 8)
                }
            })

        # =================================================
        # 5. BLUR HANDLING
        # =================================================

        s = scores.sharpness_score

        if s < 0.25:
            strength = "ultra"
        elif s < 0.40:
            strength = "high"
        elif s < 0.60:
            strength = "medium"
        elif s < 0.72:
            strength = "low"
        else:
            strength = None

        if strength:
            actions.append({
                "type": "deblur",
                "strength": strength,
                "priority": 2
            })

        # =================================================
        # 6. SUPER RESOLUTION (GFPGAN GATED)
        # =================================================

        if scores.face_present:
            if scores.sharpness_score <= 0.50 and scores.largest_face_ratio > 0.10:
                actions.append({
                    "type": "super_resolution",
                    "priority": 5
                })

        # =================================================
        # 7. NOISE REDUCTION
        # =================================================

        if scores.noise_score < 0.30:
            actions.append({
                "type": "denoise",
                "strength": "low",
                "priority": 3
            })

        # =================================================
        # CONFIDENCE
        # =================================================

        confidence = round(
            min(1.0, 0.50 + (scores.overall_quality * 0.5)), 3
        )

        return ForensicDecision(
            allow_enhancement=len(actions) > 0,
            risk_level=risk,
            recommended_actions=self._apply_learned_priorities(actions),
            forensic_notes=notes,
            confidence=confidence
        )



    # ============================================================
    # CATEGORY HELPERS
    # Used only for logging & learner
    # No policy behavior change
    # ============================================================

    # -------------------------
    # Brightness level
    # -------------------------
    def brightness_level(self, score: float) -> str:
        if score < 0.45:
            return "LOW"
        elif score < 0.75:
            return "MEDIUM"
        else:
            return "HIGH"


    # -------------------------
    # Blur level (from sharpness)
    # LOW sharpness = HIGH blur
    # -------------------------
    def blur_level(self, sharpness: float) -> str:
        if sharpness < 0.40:
            return "HIGH"
        elif sharpness < 0.60:
            return "MEDIUM"
        else:
            return "LOW"


    # -------------------------
    # Noise level
    # -------------------------
    def noise_level(self, noise_score: float) -> str:
        if noise_score < 0.30:
            return "LOW"
        elif noise_score < 0.60:
            return "MEDIUM"
        else:
            return "HIGH"


    # -------------------------
    # Contrast level
    # -------------------------
    def contrast_level(self, contrast_score: float) -> str:
        if contrast_score < 0.45:
            return "LOW"
        elif contrast_score < 0.70:
            return "MEDIUM"
        else:
            return "HIGH"


    # -------------------------
    # Resolution quality level
    # -------------------------
    def resolution_level(self, resolution_score: float) -> str:
        if resolution_score < 0.45:
            return "LOW"
        elif resolution_score < 0.70:
            return "MEDIUM"
        else:
            return "HIGH"


    # -------------------------
    # Face usability level
    # -------------------------
    def face_usability_level(self, usability: float) -> str:
        if usability < 0.40:
            return "LOW"
        elif usability < 0.65:
            return "MEDIUM"
        else:
            return "HIGH"


    # -------------------------
    # Overall quality level
    # -------------------------
    def overall_quality_level(self, overall: float) -> str:
        if overall < self.MODERATE_QUALITY:
            return "LOW"
        elif overall < self.SAFE_QUALITY:
            return "MEDIUM"
        else:
            return "HIGH"


    # -------------------------
    # Pose severity level
    # -------------------------


    def pose_level(self, roll_abs: Optional[float]) -> str:
        if roll_abs is None:
            return "UNKNOWN"

        if roll_abs >= 10:
            return "HIGH"
        elif roll_abs >= 5:
            return "MEDIUM"
        else:
            return "LOW"
    # ============================================================
    # Learned policy loader
    # ============================================================
    def _load_learned_policy(self):
        path = os.path.join("adaptive_learner", "learned_policy.json")


        if not os.path.exists(path):
            return {}

        try:
            with open(path, "r") as f:
                data = json.load(f)

            print("[POLICY] Learned policy loaded")
            return data

        except Exception as e:
            print(f"[POLICY] Failed loading learned policy: {e}")
            return {}
    # ============================================================
    # Apply learned priorities
    # ============================================================
    def _apply_learned_priorities(self, actions):

        if not self.learned_policy:
            return sorted(actions, key=lambda x: x.get("priority", 999))


        learned_priorities = self.learned_policy.get(
            "recommended_priorities", {}
        )

        bad_actions = set(
            self.learned_policy.get("bad_actions", [])
        )

        filtered = []

        for act in actions:
            t = act["type"]

            # skip harmful actions
            if t in bad_actions:
                continue

            if t in learned_priorities:
                act["priority"] = learned_priorities[t]

            filtered.append(act)

        return sorted(filtered, key=lambda x: x["priority"])
