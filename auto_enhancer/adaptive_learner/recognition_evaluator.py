# forensic/recognition/recognition_evaluator.py

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
import sys
import os
from contextlib import redirect_stdout

from core.ai_engine import get_ai_engine
from database.sqlite.criminals_db import DatabaseHandler


# ============================================================
# Result objects
# ============================================================

@dataclass
class FaceRecognitionMetrics:
    face_index: int
    bbox: list
    masked: bool

    best_id: Optional[str]
    best_similarity: float
    second_similarity: float
    margin: float

    face_confidence: float
    embedding_quality: float
    final_score: float


@dataclass
class RecognitionReport:
    faces: List[FaceRecognitionMetrics]
    best_face: Optional[FaceRecognitionMetrics]
    warnings: List[str]


# ============================================================
# Evaluator
# ============================================================

class RecognitionEvaluator:
    """
    Recognition Evaluator (Forensic Scoring Engine)

    - Detects faces
    - Runs embedding
    - Compares against DB
    - Computes forensic confidence score
    - Selects best forensic face
    """

    def __init__(self, device="cpu"):
        self.device = device

        self.ai = get_ai_engine()
        self.detector = self.ai.detect_forensic
        self.classifier = self.ai.classify_mask
        self.embedder = self.ai.get_embedding

        self.db = DatabaseHandler()


    # -----------------------------
    # Public API
    # -----------------------------

    def evaluate(self, image: np.ndarray, silent: bool = False) -> RecognitionReport:

        warnings = []
        results = []

        detections = self.detector(image)
        if not detections:
            return RecognitionReport(faces=[], best_face=None, warnings=["no_face_detected"])

        for idx, det in enumerate(detections):

            x1, y1, x2, y2 = det["box"]
            face_crop = image[y1:y2, x1:x2]

            if face_crop.size == 0:
                continue

            if silent:
                with open(os.devnull, "w") as f, redirect_stdout(f):
                    label, conf = self.classifier(face_crop)
            else:
                label, conf = self.classifier(face_crop)

            masked = (label == "Mask")

            if silent:
                with open(os.devnull, "w") as f, redirect_stdout(f):
                    embedding = self.embedder(face_crop, masked=masked)
            else:
                embedding = self.embedder(face_crop, masked=masked)

            if embedding is None:
                continue

            sims = self._compare_with_db(embedding)

            if not sims:
                best_sim = 0.0
                second_sim = 0.0
                best_id = None
            else:
                best_id, best_sim = sims[0]
                second_sim = sims[1][1] if len(sims) > 1 else 0.0

            margin = max(0.0, best_sim - second_sim)

            embedding_quality = self._estimate_embedding_quality(face_crop)

            final_score = self._build_final_score(
                best_sim, margin, conf, embedding_quality
            )

            metrics = FaceRecognitionMetrics(
                face_index=idx,
                bbox=det["box"],
                masked=masked,
                best_id=best_id,
                best_similarity=best_sim,
                second_similarity=second_sim,
                margin=margin,
                face_confidence=float(conf),
                embedding_quality=float(embedding_quality),
                final_score=float(final_score)
            )

            results.append(metrics)

        if not results:
            return RecognitionReport(faces=[], best_face=None, warnings=["no_valid_faces"])

        best_face = max(results, key=lambda x: x.final_score)

        return RecognitionReport(
            faces=results,
            best_face=best_face,
            warnings=warnings
        )


    # -----------------------------
    # Core scoring
    # -----------------------------

    def _compare_with_db(self, embedding: np.ndarray):
        all_embeddings = self.db.fetch_all_embeddings()
        if not all_embeddings:
            return []

        scores = []

        for criminal_id, db_emb in all_embeddings:
            if db_emb is None or db_emb.size == 0:
                continue

            sim = float(np.dot(embedding, db_emb) /
                        (np.linalg.norm(embedding) * np.linalg.norm(db_emb) + 1e-8))

            criminal = self.db.fetch_criminal_by_id(criminal_id)
            if criminal:
                scores.append((criminal["name"], sim * 100))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


    def _estimate_embedding_quality(self, face: np.ndarray) -> float:
        """
        Fast forensic proxies:
        - blur
        - brightness
        - contrast
        - face size
        """

        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = min(blur_score / 120.0, 1.0)

        brightness = np.mean(gray) / 255.0
        brightness_score = 1.0 - abs(brightness - 0.5) * 2

        contrast = np.std(gray) / 128.0
        contrast_score = min(contrast, 1.0)

        h, w = gray.shape[:2]
        size_score = min((h * w) / (140 * 140), 1.0)

        quality = (
            0.30 * blur_score +
            0.25 * brightness_score +
            0.25 * contrast_score +
            0.20 * size_score
        )

        return float(max(0.0, min(1.0, quality)))


    def _build_final_score(self, sim, margin, face_conf, emb_quality):
        sim_n = sim / 100.0
        margin_n = margin / 100.0

        final = (
            0.55 * sim_n +
            0.25 * margin_n +
            0.10 * face_conf +
            0.10 * emb_quality
        )

        return float(max(0.0, min(1.0, final)))
