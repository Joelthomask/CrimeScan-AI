# face_recognition/embedding/InsightFace/arcface_embedder.py

import onnxruntime as ort
import numpy as np
import cv2

class ArcFaceEmbedder:
    def __init__(self, model_path, device="cuda"):
        """
        Wrapper around ArcFace ONNX model for embedding extraction.
        """
        providers = ["CUDAExecutionProvider"] if device == "cuda" else ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def preprocess(self, face, size=(112, 112)):
        """
        Preprocess BGR face image for ArcFace.
        """
        face = cv2.resize(face, size)
        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        face = face.astype(np.float32) / 127.5 - 1.0  # normalize [-1, 1]
        face = np.transpose(face, (2, 0, 1))  # HWC -> CHW
        return np.expand_dims(face, axis=0)

    def l2_normalize(self, x, eps=1e-10):
        """
        L2-normalize the embedding vector.
        """
        return x / (np.linalg.norm(x) + eps)

    def get_embedding(self, face):
        """
        Returns 512-D embedding from ArcFace.
        """
        inp = self.preprocess(face)
        emb = self.session.run([self.output_name], {self.input_name: inp})[0].ravel()
        return self.l2_normalize(emb)
