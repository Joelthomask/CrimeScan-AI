import cv2
import os
import numpy as np
from database.sqlite.criminals_db import DatabaseHandler
from utils.logger import get_logger
LOG = get_logger()

# 🔥 Central engine
from core.ai_engine import get_ai_engine

# =========================================================
# Global singleton instance
# =========================================================
_ENROLLMENT_INSTANCE = None


def get_enrollment_pipeline(log_callback=None, base_folder="criminal_gallery/custom"):
    global _ENROLLMENT_INSTANCE
    if _ENROLLMENT_INSTANCE is None:
        _ENROLLMENT_INSTANCE = EnrollmentPipeline(
            log_callback=log_callback,
            base_folder=base_folder,
            _internal=True
        )
    return _ENROLLMENT_INSTANCE


class EnrollmentPipeline:
    _initialized = False

    def __init__(self, log_callback=None, base_folder="criminal_gallery/custom", _internal=False):
        global _ENROLLMENT_INSTANCE

        # 🔒 If already initialized, reuse existing object state
        if EnrollmentPipeline._initialized:
            if _ENROLLMENT_INSTANCE is not None:
                self.__dict__ = _ENROLLMENT_INSTANCE.__dict__
            return

        EnrollmentPipeline._initialized = True
        _ENROLLMENT_INSTANCE = self

        LOG.info("[ENROLL][INIT] Initializing Enrollment Pipeline...")

        # 🔥 AI Engine (already warmed)
        self.ai = get_ai_engine()

        self.detector = self.ai.forensic_detector
        self.classifier = self.ai.mask_classifier
        self.embedder = self.ai.face_embedder

        # --- Database handler ---
        self.db = DatabaseHandler()

        # --- Logging callback ---
        self.log_callback = log_callback

        # --- Base folder ---
        self.base_folder = base_folder
        os.makedirs(self.base_folder, exist_ok=True)

        LOG.info(f"[ENROLL][INIT] Storage folder : {self.base_folder}")
        LOG.info("[ENROLL][INIT] Enrollment pipeline ready.")

    # -------------------------------------------------
    # Internal logger
    # -------------------------------------------------
    def _log(self, message):
        tag_msg = f"[ENROLL] {message}"
        if self.log_callback:
            self.log_callback(tag_msg)
        else:
            LOG.info(tag_msg)

    # -------------------------------------------------
    # Criminal DB handler
    # -------------------------------------------------
    def _get_or_create_criminal(self, name, age, crime, height, otherinfo, folder):
        existing = self.db.get_criminal_by_name(name)

        if existing:
            self._log(f"[DB] Criminal '{name}' exists. Using existing ID.")
            return existing[0]

        self._log(f"[DB] Creating new criminal profile: {name}")

        return self.db.insert_criminal(
            name=name,
            age=age,
            crime=crime,
            height=height,
            other_info=otherinfo,
            image_folder=folder
        )

    # -------------------------------------------------
    # Embedding extractor
    # -------------------------------------------------
    def _get_embedding(self, face_np, masked=False):
        emb = self.embedder.get_embedding(face_np, masked=masked)

        if emb is not None:
            emb = emb.astype(np.float32)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb /= norm

        return emb

    # =================================================
    # SINGLE IMAGE ENROLLMENT
    # =================================================
    def enroll_from_image(self, image_path, name, age, crime, height, otherinfo):

        self._log(f"[START] Processing image → {os.path.basename(image_path)} | Person: {name}")

        img = cv2.imread(image_path)
        if img is None:
            self._log(f"[ERROR] Failed to read image: {image_path}")
            return

        detections = self.detector.detect(img)
        if not detections:
            self._log(f"[WARN] No face detected in: {os.path.basename(image_path)}")
            return

        criminal_folder = os.path.join(self.base_folder, name)
        os.makedirs(criminal_folder, exist_ok=True)

        saved_image_path = os.path.join(criminal_folder, os.path.basename(image_path))
        cv2.imwrite(saved_image_path, img)

        criminal_id = self._get_or_create_criminal(
            name, age, crime, height, otherinfo, criminal_folder
        )

        for idx, det in enumerate(detections):
            x1, y1, x2, y2 = det["box"]
            face_crop = img[y1:y2, x1:x2]

            if face_crop.size == 0:
                self._log(f"[WARN] Face {idx} crop empty. Skipped.")
                continue

            label, conf = self.classifier.classify(face_crop)
            masked = (label == "Mask")

            self._log(f"[FACE {idx}] Masked={masked} | Conf={conf:.2f}")

            emb = self._get_embedding(face_crop, masked=masked)
            if emb is None:
                self._log(f"[WARN] Embedding extraction failed for face {idx}")
                continue

            face_filename = os.path.join(
                criminal_folder,
                f"{os.path.splitext(os.path.basename(image_path))[0]}_face{idx}.jpg"
            )

            cv2.imwrite(face_filename, face_crop)
            self.db.insert_embedding(criminal_id, emb)

            self._log(f"[FACE {idx}] Saved + embedded")

        self._log(f"[SUCCESS] {name} enrolled with {len(detections)} face(s)")

    # =================================================
    # MULTI IMAGE ENROLLMENT
    # =================================================
    def enroll_multiple_images(self, image_paths, name, age, crime, height, otherinfo):

        self._log(f"[START] Enrolling {name} from {len(image_paths)} images")

        criminal_folder = os.path.join(self.base_folder, name)
        os.makedirs(criminal_folder, exist_ok=True)

        criminal_id = self._get_or_create_criminal(
            name, age, crime, height, otherinfo, criminal_folder
        )

        for img_idx, img_path in enumerate(image_paths):

            self._log(f"[IMAGE {img_idx}] Processing → {os.path.basename(img_path)}")

            img = cv2.imread(img_path)
            if img is None:
                self._log(f"[ERROR] Failed to read image: {img_path}")
                continue

            detections = self.detector.detect(img)
            if not detections:
                self._log(f"[WARN] No face detected in: {os.path.basename(img_path)}")
                continue

            for face_idx, det in enumerate(detections):

                x1, y1, x2, y2 = det["box"]
                face_crop = img[y1:y2, x1:x2]

                if face_crop.size == 0:
                    self._log(f"[WARN] Empty crop face {face_idx}")
                    continue

                label, conf = self.classifier.classify(face_crop)
                masked = (label == "Mask")

                self._log(f"[FACE {face_idx}] Masked={masked} | Conf={conf:.2f}")

                emb = self._get_embedding(face_crop, masked=masked)
                if emb is None:
                    self._log(f"[WARN] Embedding failed for face {face_idx}")
                    continue

                face_filename = os.path.join(
                    criminal_folder,
                    f"{os.path.splitext(os.path.basename(img_path))[0]}_face{face_idx}.jpg"
                )

                cv2.imwrite(face_filename, face_crop)
                self.db.insert_embedding(criminal_id, emb)

                self._log(f"[FACE {face_idx}] Saved + embedded")

        self._log(f"[SUCCESS] {name} enrolled from {len(image_paths)} images")
