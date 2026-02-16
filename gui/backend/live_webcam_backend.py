import numpy as np
import cv2
from pathlib import Path
from database.sqlite.criminals_db import DatabaseHandler
from gui.backend.recognition_worker import RecognitionWorker
from utils.temp_manager import get_temp_subpath
import time
from core.ai_engine import get_ai_engine
from utils.logger import get_logger
LOG = get_logger()
from collections import deque
# =========================================================
# Global singleton instance
# =========================================================
_LIVE_BACKEND_INSTANCE = None


def get_live_backend(session_paths=None, device="cuda"):
    global _LIVE_BACKEND_INSTANCE
    if _LIVE_BACKEND_INSTANCE is None:
        _LIVE_BACKEND_INSTANCE = LiveWebcamBackend(
            session_paths=session_paths,
            device=device,
            _internal=True
        )
    return _LIVE_BACKEND_INSTANCE


def l2_normalize(x: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(x)
    if norm == 0:
        return x
    return x / norm


class LiveWebcamBackend:
    _initialized = False

    def __init__(self, session_paths=None, device="cuda", _internal=False):
        global _LIVE_BACKEND_INSTANCE

        # 🔒 Reuse already-initialized backend
        if LiveWebcamBackend._initialized:
            if _LIVE_BACKEND_INSTANCE is not None:
                self.__dict__ = _LIVE_BACKEND_INSTANCE.__dict__
            return

        LiveWebcamBackend._initialized = True
        _LIVE_BACKEND_INSTANCE = self

        self.device = device
        self.session_paths = session_paths

        LOG.info("[LIVE] Initializing Live Webcam Backend...")

        # 🔥 REQUIRED (crash fix)
        self.frame_id = 0

        # Performance config
        self.resize_w = 640
        self.resize_h = 360
        self.detect_interval = 4
        self.recognition_interval = 5

        # --- Tracking layer ---
        self.trackers = {}
        self.tracker_boxes = {}
        self.tracker_fail_count = 0
        self.max_tracker_fail = 10
        self.detect_interval = 4

        # --- AI Engine (shared) ---
        self.ai = get_ai_engine()

        # 🔥 LIVE PIPELINE USES SCRFD
        self.detector = self.ai.live_detector
        self.classifier = self.ai.mask_classifier
        # Mask detection enabled by default
        self.mask_enabled = True
        self.embedder = self.ai.face_embedder

        # --- Database ---
        self.db = DatabaseHandler()

        self.all_embeddings = self.db.fetch_all_embeddings()
        LOG.info("[LIVE] Cached DB embeddings: %d", len(self.all_embeddings))

        self.id_name_map = {}
        for criminal_id, _ in self.all_embeddings:
            criminal = self.db.fetch_criminal_by_id(criminal_id)
            if criminal:
                self.id_name_map[criminal_id] = criminal["name"]

        self.recog_worker = RecognitionWorker(self.embedder, self.find_match)
        self.recog_worker.result_ready.connect(self._on_recognition_result)
        self.recog_worker.start()

        # --- Identity persistence ---
        self.last_identities = {}
        self.next_track_id = 0
        self.identity_life = 10

        # --- Session folders (SAFE) ---
        self.detected_dir = get_temp_subpath("livewebcam/detected_faces")
        self.recognized_dir = get_temp_subpath("livewebcam/recognized")

        LOG.info("[LIVE] Session webcam folders ready.")
        LOG.info("       Detected : %s", self.detected_dir)

        LOG.info("       Recognized: %s", self.recognized_dir)


        # --- Save control ---
        self.saved_people = set()


        # --- Last results (for skipped frames) ---
        self.last_results = []


        # store last embeddings per face index
        self.embedding_buffers = {}
        self.embedding_buffer_size = 5   # number of frames to average

    # ---------------- COSINE SIMILARITY ----------------
    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return -1
        return float(np.dot(l2_normalize(a), l2_normalize(b)))

    def _box_moved(self, old, new, thresh=0.15):
        ox1, oy1, ox2, oy2 = old
        nx1, ny1, nx2, ny2 = new

        oa = (ox2 - ox1) * (oy2 - oy1)
        na = (nx2 - nx1) * (ny2 - ny1)

        if oa == 0 or na == 0:
            return True

        inter_x1 = max(ox1, nx1)
        inter_y1 = max(oy1, ny1)
        inter_x2 = min(ox2, nx2)
        inter_y2 = min(oy2, ny2)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return True

        inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        iou = inter / float(oa + na - inter)

        return iou < (1 - thresh)

    # ---------------- IOU (for identity linking) ----------------
    def _iou(self, a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        return inter / float(area_a + area_b - inter)

    def _assign_id(self, box):
        for tid, data in self.last_identities.items():
            if self._iou(box, data["box"]) > 0.4:
                return tid
        self.next_track_id += 1
        return self.next_track_id


    def set_mask_enabled(self, enabled: bool):
        self.mask_enabled = enabled
        LOG.info(f"[LIVE] Mask detection enabled: {enabled}")
 # ---------------- MATCHING ----------------
    def find_match(self, embedding, masked=False):
        if not self.all_embeddings:
            return []

        best_match = None
        best_score = -1.0

        for criminal_id, db_emb in self.all_embeddings:
            if db_emb is None:
                continue

            score = self.cosine_similarity(embedding, db_emb)
            if score > best_score:
                best_score = score
                best_match = self.id_name_map.get(criminal_id)

        if best_match is None:
            return []

        return [(best_match, float(best_score * 100))]


    # ---------------- DETECTION + MATCH ----------------
    def detect_and_match(self, frame):
        import time

        if self.frame_id % 30 == 0:
            LOG.info("\n[DBG] ===== detect_and_match called =====")

        t_total_start = time.time()

        if frame is None or frame.size == 0:
            return self.last_results

        self.frame_id += 1

        h0, w0 = frame.shape[:2]

        if self.frame_id % 30 == 0:
            LOG.info(f"[DBG] Frame ID: {self.frame_id} | Shape: {h0}x{w0}")

        # -------- Skip detection frames --------
        if self.frame_id % self.detect_interval != 0:
            return self.last_results

        # -------- Resize frame --------
        small = cv2.resize(frame, (self.resize_w, self.resize_h))
        scale_x = w0 / self.resize_w
        scale_y = h0 / self.resize_h

        # -------- Detection --------
        t_det_start = time.time()
        try:
            detections = self.detector.detect(small)
        except Exception:
            return self.last_results

        if self.frame_id % 30 == 0:
            LOG.info(f"[PERF] SCRFD: {(time.time()-t_det_start)*1000:.2f} ms | faces: {len(detections)}")

        # -------- Collect faces --------
        face_crops = []
        boxes_scaled = []

        for det in detections:

            try:
                x1, y1, x2, y2 = det["box"]
            except Exception:
                continue

            x1 = int(x1 * scale_x)
            y1 = int(y1 * scale_y)
            x2 = int(x2 * scale_x)
            y2 = int(y2 * scale_y)

            x1 = max(0, min(x1, w0 - 1))
            y1 = max(0, min(y1, h0 - 1))
            x2 = max(0, min(x2, w0 - 1))
            y2 = max(0, min(y2, h0 - 1))

            if x2 - x1 < 40 or y2 - y1 < 40:
                continue

            face_crop = frame[y1:y2, x1:x2]
            if face_crop.size == 0:
                continue

            # -------- Alignment --------
            if "landmarks" in det:
                lm = det["landmarks"]
                le, re = lm["left_eye"], lm["right_eye"]

                dy, dx = re[1] - le[1], re[0] - le[0]
                angle = np.degrees(np.arctan2(dy, dx))

                center = (face_crop.shape[1] // 2,
                        face_crop.shape[0] // 2)

                rot = cv2.getRotationMatrix2D(center, angle, 1.0)
                face_crop = cv2.warpAffine(
                    face_crop,
                    rot,
                    (face_crop.shape[1], face_crop.shape[0])
                )

            if face_crop.size == 0:
                continue

            face_crops.append(face_crop)
            boxes_scaled.append((x1, y1, x2, y2))

        # -------- No faces --------
        if not face_crops:
            self.last_results = []
            return []

        # -------- Batch mask --------
        if self.mask_enabled:
            mask_results = self.classifier.classify_batch(face_crops)
        else:
            mask_results = [("No Mask", 1.0)] * len(face_crops)

        # -------- Batch embeddings --------
        embeddings = self.embedder.get_embeddings_batch(face_crops)

        results = []

        # -------- Matching loop --------
        for i, ((x1, y1, x2, y2), (label, conf), emb) in enumerate(
                zip(boxes_scaled, mask_results, embeddings)):

            if emb is not None:
                if i not in self.embedding_buffers:
                    self.embedding_buffers[i] = deque(
                        maxlen=self.embedding_buffer_size
                    )

                self.embedding_buffers[i].append(emb)
                embedding = np.mean(self.embedding_buffers[i], axis=0)
            else:
                embedding = None

            matches = []
            if embedding is not None:
                matches = self.find_match(
                    embedding,
                    masked=(label == "Mask")
                )

            results.append({
                "box": (x1, y1, x2, y2),
                "mask_label": label,
                "mask_conf": conf,
                "matches": matches
            })

        self.last_results = results

        if self.frame_id % 30 == 0:
            LOG.info(
                f"[PERF] TOTAL detect_and_match: "
                f"{(time.time()-t_total_start)*1000:.2f} ms | "
                f"results: {len(results)}"
            )

        return results


    def _on_recognition_result(self, tid, result):

        if tid not in self.last_identities:
            return

        entry = self.last_identities[tid]

        if result is None:
            entry["life"] -= 1
            if entry["life"] <= 0:
                entry["name"] = "Unknown"
                entry["conf"] = 0.0
            return

        name, score = result
        masked = (entry.get("last_mask") == "Mask")

        if (masked and score >= 28) or (not masked and score >= 50):
            entry["name"] = name
            entry["conf"] = score
            entry["life"] = self.identity_life

    def shutdown(self):
        self.recog_worker.stop()
        self.recog_worker.wait()
