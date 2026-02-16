# auto_enhancer/quality_assessment/models/clip_iqa.py

import torch
import clip
import cv2
import numpy as np
from PIL import Image
from utils.logger import get_logger
LOG = get_logger()


class CLIPIQA:
    """
    Deep perceptual image quality model using CLIP.
    Outputs a human-aligned quality score between 0 and 1.
    """

    def __init__(self, device="cuda"):
        self.device = device if torch.cuda.is_available() else "cpu"

        LOG.info("[CLIP-IQA] Loading CLIP model...")
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        self.model.eval()

        # Fixed quality prompts (used in many CLIP-IQA works)
        self.prompts = [
            "a high quality photo",
            "a good quality image",
            "a sharp and clear photo",
            "a low quality photo",
            "a blurry and noisy image",
            "a very poor quality photo"
        ]

        with torch.no_grad():
            text_tokens = clip.tokenize(self.prompts).to(self.device)
            self.text_features = self.model.encode_text(text_tokens)
            self.text_features = self.text_features / self.text_features.norm(dim=-1, keepdim=True)

        LOG.info("[CLIP-IQA] Model ready on", self.device)

    # --------------------------------------------------

    def assess(self, image_path: str):
        """
        Returns:
            {
                "clip_iqa_score": float (0–1),
                "raw_similarities": dict
            }
        """

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img)
        image_input = self.preprocess(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(image_input)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ self.text_features.T).softmax(dim=-1)[0]

        sims = similarity.detach().cpu().numpy()

        result = dict(zip(self.prompts, sims.tolist()))

        # Positive vs negative quality separation
        positive = np.mean([result[self.prompts[0]],
                             result[self.prompts[1]],
                             result[self.prompts[2]]])

        negative = np.mean([result[self.prompts[3]],
                             result[self.prompts[4]],
                             result[self.prompts[5]]])

        # Normalize into 0–1 forensic quality score
        quality_score = float(positive / (positive + negative + 1e-8))

        return {
            "clip_iqa_score": round(quality_score, 4),
            "raw_similarities": result
        }
