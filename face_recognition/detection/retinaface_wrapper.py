import cv2
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from pathlib import Path
import sys
from utils.logger import get_logger
LOG = get_logger()

# -------------------------------
# Paths
# -------------------------------
BASE_DIR = Path(__file__).parent
RETINAFACE_ROOT = BASE_DIR / "retinaface"
RESNET_MODEL_PATH = RETINAFACE_ROOT / "weights/ResNet50_Final.pth"
MOBILENET_MODEL_PATH = RETINAFACE_ROOT / "weights/MobileNet0.25_Final.pth"
MASK_MODEL_PATH = RETINAFACE_ROOT / "weights/mobilenet_mask.pth.tar"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------------------
# Ensure retinaface repo is importable
# -------------------------------
RETINAFACE_PATH_STR = str(RETINAFACE_ROOT.resolve())
if RETINAFACE_PATH_STR not in sys.path:
    sys.path.insert(0, RETINAFACE_PATH_STR)

# -------------------------------
# Import RetinaFace modules
# -------------------------------
from .retinaface.models.retinaface import RetinaFace
from .retinaface.utils.box_utils import decode, decode_landm
from .retinaface.layers.functions.prior_box import PriorBox
from .retinaface.utils.nms.py_cpu_nms import py_cpu_nms
from .retinaface.data.config import cfg_mnet, cfg_re50

# Mask classifier model
from .retinaface.models.mobilenet_mask_classifier import get_model

# -------------------------------
# Face Detector
# -------------------------------
class FaceDetector:
    def __init__(self, network='resnet50', conf_thresh=0.6, nms_thresh=0.4, padding_ratio=0.1):
        self.CONF_THRESH = conf_thresh
        self.NMS_THRESH = nms_thresh
        self.PADDING_RATIO = padding_ratio
        self.NETWORK = network

        # Select config and weights
        if network == 'resnet50':
            self.cfg = cfg_re50
            model_path = RESNET_MODEL_PATH
        elif network == 'mobilenet0.25':
            self.cfg = cfg_mnet
            model_path = MOBILENET_MODEL_PATH
        else:
            raise ValueError(f"Unsupported network '{network}'")

        # Load RetinaFace
        self.detector = RetinaFace(cfg=self.cfg, phase='test')
        ckpt = torch.load(model_path, map_location=DEVICE)
        raw_rf = ckpt.get('state_dict', ckpt)
        rf_state = {k.replace('module.', ''): v for k, v in raw_rf.items()}
        self.detector.load_state_dict(rf_state, strict=False)
        self.detector.to(DEVICE).eval()

    def detect(self, frame, max_size=1024):
        orig_h, orig_w = frame.shape[:2]
        scale_factor = 1.0

        if max(orig_h, orig_w) > max_size:
            scale_factor = max_size / max(orig_h, orig_w)
            new_w, new_h = int(orig_w * scale_factor), int(orig_h * scale_factor)
            frame_resized = cv2.resize(frame, (new_w, new_h))
            LOG.info(f"[INFO] Downscaled {orig_w}x{orig_h} -> {new_w}x{new_h} for detection")
        else:
            frame_resized = frame

        h, w = frame_resized.shape[:2]
        img = frame_resized.astype(np.float32)
        img -= (104, 117, 123)
        img = img.transpose(2, 0, 1)
        img_tensor = torch.from_numpy(img).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            loc, conf, landms = self.detector(img_tensor)

        scale = torch.Tensor([w, h, w, h]).to(DEVICE)
        priorbox = PriorBox(self.cfg, image_size=(h, w))
        priors = priorbox.forward().to(DEVICE)

        boxes = decode(loc.squeeze(0), priors.data, self.cfg['variance'])
        boxes = (boxes * scale).cpu().numpy()
        scores = conf.squeeze(0)[:, 1].cpu().numpy()

        landms = decode_landm(landms.squeeze(0), priors.data, self.cfg['variance'])
        scale1 = torch.Tensor([w, h] * 5).to(DEVICE)
        landms = (landms * scale1).cpu().numpy()

        keep_inds = np.where(scores > self.CONF_THRESH)[0]
        boxes, scores, landms = boxes[keep_inds], scores[keep_inds], landms[keep_inds]

        order = scores.argsort()[::-1]
        boxes, scores, landms = boxes[order], scores[order], landms[order]

        dets = np.hstack((boxes, scores[:, np.newaxis])).astype(np.float32)
        keep = py_cpu_nms(dets, self.NMS_THRESH)
        dets = dets[keep]

        result = []
        for i, det in enumerate(dets):
            if det[4] < self.CONF_THRESH:
                continue

            x1, y1, x2, y2 = map(int, det[:4])

            if scale_factor != 1.0:
                x1 = int(x1 / scale_factor)
                y1 = int(y1 / scale_factor)
                x2 = int(x2 / scale_factor)
                y2 = int(y2 / scale_factor)

            bw, bh = x2 - x1, y2 - y1
            px, py = int(bw * self.PADDING_RATIO), int(bh * self.PADDING_RATIO)
            x1c, y1c = max(0, x1 - px), max(0, y1 - py)
            x2c, y2c = min(orig_w, x2 + px), min(orig_h, y2 + py)

            # ---------- LANDMARKS ----------
            lm = landms[i].reshape(-1, 2)

            if scale_factor != 1.0:
                lm = lm / scale_factor

            landmarks = {
                "left_eye": tuple(map(int, lm[0])),
                "right_eye": tuple(map(int, lm[1])),
                "nose": tuple(map(int, lm[2])),
                "mouth_left": tuple(map(int, lm[3])),
                "mouth_right": tuple(map(int, lm[4]))
            }

            result.append({
                "box": (x1c, y1c, x2c, y2c),
                "score": float(det[4]),
                "landmarks": landmarks
            })

        return result

# -------------------------------
# Mask Classifier
# -------------------------------
class MaskClassifier(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.model = get_model(num_classes=2, pretrained=False, fine_tune=False, device=DEVICE)
        ckpt = torch.load(MASK_MODEL_PATH, map_location=DEVICE)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.to(DEVICE).eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])

    def preprocess_face(self, face_img):
        pil = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
        return self.transform(pil).unsqueeze(0).to(DEVICE)

    def classify(self, face_img):
        tensor = self.preprocess_face(face_img)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        idx = int(np.argmax(probs))
        label = 'Mask' if idx == 0 else 'No Mask'
        confidence = float(probs[idx])
        return label, confidence
    def classify_batch(self, face_list):
        if not face_list:
            return []

        tensors = [self.preprocess_face(f) for f in face_list]
        batch = torch.cat(tensors, dim=0)

        with torch.no_grad():
            logits = self.model(batch)
            probs = torch.softmax(logits, dim=1).cpu().numpy()

        results = []
        for p in probs:
            idx = int(np.argmax(p))
            label = 'Mask' if idx == 0 else 'No Mask'
            results.append((label, float(p[idx])))

        return results

# -------------------------------
# Optional webcam test
# -------------------------------
def run_webcam():
    detector = FaceDetector(network='mobilenet0.25')  # updated default
    classifier = MaskClassifier()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        LOG.info("❌ Could not open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        faces = detector.detect(frame)
        for f in faces:
            x1, y1, x2, y2 = f['box']
            face_crop = frame[y1:y2, x1:x2]
            if face_crop.size == 0:
                continue
            label, conf = classifier.classify(face_crop)
            color = (0, 255, 0) if label == 'Mask' else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{label}: {conf*100:.1f}%", (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.imshow("Live Mask Detector", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_webcam()
