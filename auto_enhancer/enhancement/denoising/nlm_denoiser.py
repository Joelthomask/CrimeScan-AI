import os
import cv2
from PyQt5.QtCore import QThread, pyqtSignal

from utils.logger import log_event

from typing import Optional, Dict

class NLMWorker(QThread):
    """
    NLM Denoising Executor (CLEAN)
    -------------------------------
    • No QA
    • No noise estimation
    • No auto decision
    • No skip logic
    • Executes only what Intelligence requests

    Intelligence must provide:
        strength: "low" | "medium" | "high" | "extreme"
        params: optional fine tuning dict
    """

    finished = pyqtSignal(str)

    def __init__(
        self,
        input_image_path: str,
        output_image_path: str,
        strength: str = "medium",
        params: Optional[Dict] = None
    ):


        super().__init__()
        self.input_image_path = os.path.abspath(input_image_path).replace("\\", "/")
        self.output_image_path = os.path.abspath(output_image_path).replace("\\", "/")
        self.strength = strength
        self.params = params or {}

    # -------------------------
    # MAIN EXECUTOR
    # -------------------------
    def run(self):
        try:
            log_event("DENOISE", f"NLM executor running → strength={self.strength.upper()}")

            if not os.path.exists(self.input_image_path):
                log_event("DENOISE", "Input file not found", level="ERROR")
                self.finished.emit("")
                return

            img = cv2.imread(self.input_image_path)
            if img is None:
                raise FileNotFoundError("Failed to read image")

            # =====================================================
            # Strength → default parameters
            # =====================================================

            if self.strength == "extreme":
                hColor = self.params.get("hColor", 5)
                hLuma  = self.params.get("hLuma", 5)
                tSize  = self.params.get("template", 3)
                sSize  = self.params.get("search", 21)

            elif self.strength == "high":
                hColor = self.params.get("hColor", 5)
                hLuma  = self.params.get("hLuma", 5)
                tSize  = self.params.get("template", 7)
                sSize  = self.params.get("search", 21)

            elif self.strength == "low":
                hColor = self.params.get("hColor", 3)
                hLuma  = self.params.get("hLuma", 3)
                tSize  = self.params.get("template", 7)
                sSize  = self.params.get("search", 21)

            else:  # medium (forensic safe default)
                hColor = self.params.get("hColor", 4)
                hLuma  = self.params.get("hLuma", 4)
                tSize  = self.params.get("template", 7)
                sSize  = self.params.get("search", 21)

            log_event(
                "DENOISE",
                f"NLM params → hColor={hColor}, hLuma={hLuma}, template={tSize}, search={sSize}"
            )

            # =====================================================
            # APPLY NLM
            # =====================================================

            denoised = cv2.fastNlMeansDenoisingColored(
                img,
                None,
                hColor,
                hLuma,
                tSize,
                sSize
            )

            # =====================================================
            # SAVE OUTPUT
            # =====================================================

            os.makedirs(os.path.dirname(self.output_image_path), exist_ok=True)
            cv2.imwrite(self.output_image_path, denoised)

            log_event("DENOISE", f"Executor finished → {self.output_image_path}")
            self.finished.emit(self.output_image_path)

        except Exception as e:
            log_event("DENOISE", f"Executor error → {e}", level="ERROR")
            self.finished.emit("")
