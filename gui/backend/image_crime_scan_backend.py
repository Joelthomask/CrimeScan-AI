import os
import numpy as np
import cv2
from datetime import datetime
from utils.logger import get_logger
LOG = get_logger()

from database.sqlite.criminals_db import DatabaseHandler
from core.ai_engine import get_ai_engine

MATCH_THRESHOLD = 40.0  # percent


class ImageCrimeScanBackend:
    """
    Backend for Crime Scan Page:
    - Detection + Mask Classification + Embedding + DB Matching
    - Prepares payload for QualityCheckerPage
    """

    def __init__(self, device="cpu"):
        self.device = device

        # --- Shared AI Engine ---
        self.ai = get_ai_engine()

        # 🔥 Forensic path (RetinaFace ResNet)
        self.detector = self.ai.detect_forensic
        self.classifier = self.ai.classify_mask
        self.embedder = self.ai.get_embedding

        # --- Database (centralized, single source of truth) ---
        self.db = DatabaseHandler()

    # ---------------- MATCHING ----------------
    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two embeddings"""
        if a is None or b is None:
            return -1
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)

    def find_match(
        self,
        embedding,
        masked=False,
        normal_threshold=0.6,
        masked_threshold=0.35,
        top_n=2
    ):
        """Compare embedding against DB and return best match(s)."""

        all_embeddings = self.db.fetch_all_embeddings()
        if not all_embeddings:
            return []

        best_name = None
        best_score = -1.0

        for criminal_id, db_emb in all_embeddings:
            if db_emb is None or db_emb.size == 0:
                continue

            score = self.cosine_similarity(embedding, db_emb) * 100

            if score > best_score:
                criminal = self.db.fetch_criminal_by_id(criminal_id)
                if criminal:
                    best_score = score
                    best_name = criminal["name"]

        if best_score < MATCH_THRESHOLD:
            return []

        return [(best_name, best_score)]

    # ---------------- QC PREP ----------------
    def prepare_for_qc(self, image_path):
        logs = []

        if not os.path.exists(image_path):
            err = f"[ERROR] Image not found: {image_path}"
            LOG.info(f"[ERROR][CRIMESCAN] {err}")
            return {"error": err, "log": [err]}

        img = cv2.imread(image_path)
        if img is None:
            err = f"[ERROR] Failed to read image: {image_path}"
            LOG.info(f"[ERROR][CRIMESCAN] {err}")
            return {"error": err, "log": [err]}

        h, w = img.shape[:2]
        info = f"[INFO] Loaded image successfully ({w}x{h})"
        LOG.info(f"[CRIMESCAN] {info}")
        logs.append(info)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logs.append(f"[INFO] Timestamp: {timestamp}")
        LOG.info(f"[CRIMESCAN] Timestamp: {timestamp}")

        payload = {
            "image_path": image_path,
            "log": logs,
            "redirect_to": "QualityCheckerPage",
            "back_to": "CrimeScanPage",
            "image": img,
        }

        return payload

    # ---------------- MAIN PIPELINE ----------------
    def process_image(self, image_path):

        results = {
            "image_path": image_path,
            "detections": [],
            "qc_input": {},
            "log": []
        }

        img = cv2.imread(image_path)
        if img is None:
            err_msg = f"[ERROR] Failed to load image: {image_path}"
            LOG.info(f"[ERROR][CRIMESCAN] {err_msg}")
            return {"error": err_msg}

        LOG.info(f"[CRIMESCAN] Loaded image: {image_path}")
        results["log"].append(f"[INFO] Loaded image: {image_path}")

        detections = self.detector(img)
        if not detections:
            warn_msg = "[WARN] No faces detected."
            LOG.info(f"[WARN][CRIMESCAN] {warn_msg}")
            results["log"].append(warn_msg)
            return results

        LOG.info(f"[CRIMESCAN] Detected {len(detections)} face(s).")
        results["log"].append(f"[INFO] Detected {len(detections)} face(s).")

        packaged_faces = []
        for idx, det in enumerate(detections):

            x1, y1, x2, y2 = det["box"]
            face_crop = img[y1:y2, x1:x2]
            if face_crop.size == 0:
                warn_msg = f"[WARN] Face {idx} crop is empty, skipping."
                LOG.info(f"[WARN][CRIMESCAN] {warn_msg}")
                results["log"].append(warn_msg)
                continue

            label, conf = self.classifier(face_crop)
            masked = (label == "Mask")

            LOG.info(f"[CRIMESCAN] Face {idx}: Mask={masked} ({label}, {conf:.2f})")
            results["log"].append(f"[INFO] Face {idx}: Mask={masked} ({label}, {conf:.2f})")

            embedding = self.embedder(face_crop, masked=masked)
            if embedding is None:
                err_msg = f"[ERROR] Failed to extract embedding for Face {idx}"
                LOG.info(f"[ERROR][CRIMESCAN] {err_msg}")
                results["log"].append(err_msg)
                continue

            results["log"].append(f"[INFO] Extracted embedding for Face {idx}.")

            matches = self.find_match(embedding, masked=masked)
            if matches:
                for rank, (name, similarity_percent) in enumerate(matches):
                    match_msg = f"[MATCH {rank + 1}] Face {idx}: {name} (Similarity={similarity_percent:.1f}%)"
                    LOG.info(f"[CRIMESCAN] {match_msg}")
                    results["log"].append(match_msg)
            else:
                no_match_msg = f"[NO MATCH] Face {idx}: Unknown"
                LOG.info(f"[CRIMESCAN] {no_match_msg}")
                results["log"].append(no_match_msg)

            results["detections"].append({
                "index": idx,
                "bbox": det["box"],
                "mask_label": label,
                "mask_conf": conf,
                "masked": masked,
                "embedding": embedding.tolist() if embedding is not None else None,
                "matches": matches if matches else []
            })

            packaged_faces.append({
                "index": idx,
                "bbox": det["box"],
                "face_crop": face_crop,
                "mask_conf": conf,
                "masked": masked
            })

        results["qc_input"] = {
            "image": img,
            "faces": packaged_faces
        }
        results["redirect_to"] = "QualityCheckerPage"
        results["back_to"] = "CrimeScanPage"

        return results
