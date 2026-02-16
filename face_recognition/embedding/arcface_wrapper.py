# face_recognition/embedding/arcface_wrapper.py

import numpy as np
import cv2
import onnxruntime as ort
import os

class HybridFaceEmbedder:

    def __init__(self,
                arcface_model=None,
                device="cuda"):

        """
        Hybrid wrapper updated: uses ArcFace for both masked and unmasked faces.
        """
        self.device = device
        if arcface_model is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))

            arcface_model = os.path.join(
                base_dir,
                "InsightFace",
                "models",
                "buffalo_l",
                "w600k_r50.onnx"
            )

        # ----------------- ArcFace (ONNX) -----------------
        so = ort.SessionOptions()
        so.log_severity_level = 3   # hide warnings

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.arc_sess = ort.InferenceSession(
            arcface_model,
            sess_options=so,
            providers=providers
        )

        self.arc_input_name = self.arc_sess.get_inputs()[0].name

    # ----------------- Preprocessing -----------------
    @staticmethod
    def preprocess_arcface(face_img, size=(112, 112)):
        img = cv2.resize(face_img, size)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
        img = (img / 127.5) - 1.0
        img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
        img = np.expand_dims(img, axis=0)
        return img

    @staticmethod
    def l2_normalize(x, eps=1e-10):
        return x / (np.linalg.norm(x) + eps)

    # ----------------- ArcFace Embedding -----------------
    def arcface_embed(self, face_img):
        img = self.preprocess_arcface(face_img)
        emb = self.arc_sess.run(None, {self.arc_input_name: img.astype(np.float32)})[0]
        return self.l2_normalize(emb.flatten())

    # ----------------- Unified Embedding -----------------
    def get_embedding(self, face_img, masked=False):
        """
        Always returns ArcFace embedding, ignores masked flag.
        """

        return self.arcface_embed(face_img)
    def get_embeddings_batch(self, faces):
        if not faces:
            return []

        imgs = [self.preprocess_arcface(f) for f in faces]
        batch = np.concatenate(imgs, axis=0).astype(np.float32)

        embs = self.arc_sess.run(None, {self.arc_input_name: batch})[0]

        return [self.l2_normalize(e.flatten()) for e in embs]
