import math
from dataclasses import dataclass
from typing import Dict


# ============================================================
# Score Object
# ============================================================

@dataclass
class QualityScores:
    sharpness_score: float
    noise_score: float
    brightness_score: float
    contrast_score: float
    resolution_score: float
    perceptual_score: float

    face_present: bool
    face_usability: float
    largest_face_ratio: float

    overall_quality: float

    def to_dict(self):
        return self.__dict__


# ============================================================
# Score Builder
# ============================================================

class ScoreBuilder:
    """
    Converts QA reports into normalized forensic quality scores.
    Compatible with structured QA facts.
    """

    def __init__(self):
        pass

    # ============================================================
    # Main interface
    # ============================================================

    def build(self, qa_report) -> QualityScores:
        data = qa_report.to_dict()

        obj = data.get("objective", {})
        faces = data.get("faces", {})
        perc = data.get("perceptual", {})

        # =====================================================
        # FACE-FIRST SHARPNESS
        # =====================================================

        face_block = faces.get("largest_face") or {}
        face_lap = face_block.get("blur_variance")

        if face_lap is not None:
            sharpness = self._score_sharpness(face_lap)
        else:
            blur_block = obj.get("blur", {})
            sharpness = self._score_sharpness(blur_block.get("variance", 0.0))

        # =====================================================
        # STRUCTURED OBJECTIVE FACTS
        # =====================================================

        brightness_block = obj.get("brightness", {})
        contrast_block   = obj.get("contrast", {})
        noise_block      = obj.get("noise", {})
        resolution_block = obj.get("resolution", {})

        mean_brightness = brightness_block.get("mean", 0.0)
        contrast_std    = contrast_block.get("std", 0.0)
        psnr_value      = noise_block.get("psnr", 0.0)

        width  = resolution_block.get("width", 0)
        height = resolution_block.get("height", 0)

        # =====================================================
        # OTHER SCORES
        # =====================================================

        noise = self._score_noise(psnr_value)
        brightness = self._score_brightness(mean_brightness)
        contrast = self._score_contrast(contrast_std)
        resolution = self._score_resolution(width, height)
        perceptual = self._clamp(perc.get("clip_iqa_score", 0.5))

        # =====================================================
        # FACE USABILITY
        # =====================================================

        face_present = faces.get("detected", False)
        face_usability, largest_ratio = self._score_faces(faces)

        # =====================================================
        # OVERALL FUSION
        # =====================================================

        overall = self._fuse_scores([
            sharpness,
            noise,
            brightness,
            contrast,
            resolution,
            perceptual,
            face_usability
        ])

        return QualityScores(
            sharpness_score=sharpness,
            noise_score=noise,
            brightness_score=brightness,
            contrast_score=contrast,
            resolution_score=resolution,
            perceptual_score=perceptual,
            face_present=face_present,
            face_usability=face_usability,
            largest_face_ratio=largest_ratio,
            overall_quality=overall
        )

    # ============================================================
    # 🔥 FORENSIC SHARPNESS MODEL
    # ============================================================

    def _map_face_laplacian(self, lap: float) -> float:

        if lap <= 3:
            return 0.08
        elif lap <= 7:
            return 0.18
        elif lap <= 15:
            return 0.32
        elif lap <= 30:
            return 0.48
        elif lap <= 60:
            return 0.62
        elif lap <= 120:
            return 0.74
        elif lap <= 220:
            return 0.85
        elif lap <= 400:
            return 0.92
        else:
            return 0.97

    def _score_sharpness(self, laplacian: float) -> float:
        return self._clamp(self._map_face_laplacian(max(laplacian, 0.0)))

    # ============================================================
    # OTHER METRICS
    # ============================================================

    def _score_noise(self, psnr: float) -> float:
        return self._clamp((psnr - 20) / 25)

    # ✅ FORENSIC BRIGHTNESS MODEL (DARKNESS ONLY)
    def _score_brightness(self, mean: float) -> float:
        """
        Brightness score reflects ONLY darkness.
        Bright images are not penalized.
        """

        if mean <= 0:
            return 0.0

        # ---- VERY DARK ----
        if mean < 40:
            return self._clamp(mean / 60)

        # ---- LOW LIGHT ----
        elif mean < 80:
            return self._clamp(0.65 + (mean - 40) / 100)

        # ---- ACCEPTABLE OR BRIGHT ----
        else:
            return 1.0

    def _score_contrast(self, std: float) -> float:
        if std <= 0:
            return 0.0
        score = math.log1p(std) / math.log1p(80)
        return self._clamp(score)

    def _score_resolution(self, w: int, h: int) -> float:
        long_side = max(w, h)
        if long_side >= 1024:
            return 1.0
        elif long_side >= 640:
            return 0.8
        elif long_side >= 320:
            return 0.5
        else:
            return 0.2

    def _score_faces(self, faces_block: Dict) -> tuple:
        if not faces_block.get("faces"):
            return 0.0, 0.0

        largest = faces_block.get("largest_face", {})
        ratio = float(largest.get("area_ratio", 0))

        blur = largest.get("blur_variance", 0)
        brightness = largest.get("brightness", 0)
        masked = largest.get("masked", False)

        sharp = self._score_sharpness(blur)
        light = self._score_brightness(brightness)
        mask_penalty = 0.6 if masked else 1.0

        usability = self._clamp((sharp * 0.6 + light * 0.4) * mask_penalty)
        return usability, round(ratio, 4)

    # ============================================================
    # FUSION
    # ============================================================

    def _fuse_scores(self, scores):
        product = 1
        for s in scores:
            product *= max(s, 1e-4)
        return round(self._clamp(product ** (1 / len(scores))), 4)

    # ============================================================
    # UTILS
    # ============================================================

    def _clamp(self, v: float, min_v=0.0, max_v=1.0):
        return round(max(min_v, min(max_v, float(v))), 4)
