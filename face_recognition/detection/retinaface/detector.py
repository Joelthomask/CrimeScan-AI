import torch
import cv2
import numpy as np
from .models.retinaface import RetinaFace
from .layers.functions.prior_box import PriorBox
from .utils.box_utils import decode, decode_landm
from .utils.nms.py_cpu_nms import py_cpu_nms

# Import configs
from .models.net import cfg_mnet, cfg_re50


class RetinaFaceDetector:
    def __init__(self, backbone="resnet50", weights_path=None, use_cpu=False):
        # Device selection
        if use_cpu:
            self.device = torch.device("cpu")
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Choose config based on backbone
        if backbone.lower() == "resnet50":
            self.cfg = cfg_re50
        elif backbone.lower() in ["mobilenet", "mobilenet0.25", "mobile0.25"]:
            self.cfg = cfg_mnet
        else:
            raise ValueError("Backbone must be 'resnet50' or 'mobilenet0.25'")

        # Initialize RetinaFace model
        self.model = RetinaFace(cfg=self.cfg, phase="test")

        # Load weights
        if weights_path is None:
            raise ValueError("You must provide a valid weights_path to load RetinaFace")

        state_dict = torch.load(weights_path, map_location=self.device)
        if "state_dict" in state_dict:  # some checkpoints wrap weights
            state_dict = state_dict["state_dict"]
        self.model.load_state_dict(state_dict, strict=False)

        self.model.to(self.device)
        self.model.eval()

    def detect(self, img_bgr, conf_thresh=0.8, nms_thresh=0.4, top_k=5000, keep_top_k=750):
        """Detect faces in an image (BGR). Returns bboxes, scores, landmarks."""
        im_height, im_width, _ = img_bgr.shape
        scale = torch.Tensor([im_width, im_height, im_width, im_height])

        img = np.float32(img_bgr)
        img -= (104, 117, 123)  # BGR mean
        img = img.transpose(2, 0, 1)
        img = torch.from_numpy(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            loc, conf, landms = self.model(img)

        # Prior boxes
        priorbox = PriorBox(self.cfg, image_size=(im_height, im_width))
        priors = priorbox.forward().to(self.device)
        prior_data = priors.data

        # Decode boxes
        boxes = decode(loc.data.squeeze(0), prior_data, [0.1, 0.2])
        boxes = boxes * scale.to(self.device)
        boxes = boxes.cpu().numpy()

        # Decode scores
        scores = conf.data.squeeze(0).cpu().numpy()[:, 1]

        # Decode landmarks
        landms = decode_landm(landms.data.squeeze(0), prior_data, [0.1, 0.2])
        scale1 = torch.Tensor([im_width, im_height] * 5)
        landms = landms * scale1.to(self.device)
        landms = landms.cpu().numpy()

        # Filter by confidence
        inds = np.where(scores > conf_thresh)[0]
        boxes = boxes[inds]
        landms = landms[inds]
        scores = scores[inds]

        # Sort by score and keep top_k
        order = scores.argsort()[::-1][:top_k]
        boxes = boxes[order]
        landms = landms[order]
        scores = scores[order]

        # Apply NMS
        dets = np.hstack((boxes, scores[:, np.newaxis])).astype(np.float32, copy=False)
        keep = py_cpu_nms(dets, nms_thresh)
        dets = dets[keep, :][:keep_top_k]
        landms = landms[keep][:keep_top_k]

        return dets, landms

    def draw_detections(self, img_bgr, dets, landms):
        """Draw bounding boxes + landmarks on the image."""
        for b, l in zip(dets, landms):
            x1, y1, x2, y2, score = b
            if score < 0.5:
                continue
            cv2.rectangle(img_bgr, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(img_bgr, f"{score:.2f}", (int(x1), int(y1) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            for i in range(5):
                cv2.circle(img_bgr, (int(l[2 * i]), int(l[2 * i + 1])), 2, (0, 0, 255), -1)
        return img_bgr
