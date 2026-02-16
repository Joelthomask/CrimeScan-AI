from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np

class RecognitionWorker(QThread):
    result_ready = pyqtSignal(int, object)  
    # emits: (track_id, (name, score) or None)

    def __init__(self, embedder, matcher):
        super().__init__()
        self.embedder = embedder
        self.matcher = matcher
        self.jobs = []
        self.running = True

    def submit(self, track_id, face_crop, masked):
        self.jobs.append((track_id, face_crop.copy(), masked))

    def run(self):
        while self.running:
            if not self.jobs:
                self.msleep(5)
                continue

            track_id, face, masked = self.jobs.pop(0)

            embedding = self.embedder.get_embedding(face, masked=masked)
            if embedding is None:
                self.result_ready.emit(track_id, None)
                continue

            matches = self.matcher(embedding, masked=masked)
            if matches:
                self.result_ready.emit(track_id, matches[0])
            else:
                self.result_ready.emit(track_id, None)

    def stop(self):
        self.running = False
