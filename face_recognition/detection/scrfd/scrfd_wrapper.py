import cv2
import numpy as np
import onnxruntime as ort
from utils.logger import get_logger
LOG = get_logger()


class SCRFDONNXDetector:
    def __init__(self, model_path, conf_thres=0.5, nms_thres=0.4, input_size=640):
        self.conf_thres = conf_thres
        self.nms_thres = nms_thres
        self.input_size = input_size

        self.session = ort.InferenceSession(
            model_path,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]

        # SCRFD heads config
        self.fmc = 3
        self.strides = [8, 16, 32]
        self.num_anchors = 2

        self.mean = 127.5
        self.std = 128.0
        self.center_cache = {}

        LOG.info("[SCRFD-ONNX] Loaded:", model_path)
        LOG.info("[SCRFD-ONNX] Providers:", self.session.get_providers())

    # --------------------------------------------------

    def _preprocess(self, img):
        img = cv2.resize(img, (self.input_size, self.input_size))
        blob = cv2.dnn.blobFromImage(
            img,
            1.0 / self.std,
            (self.input_size, self.input_size),
            (self.mean, self.mean, self.mean),
            swapRB=True
        )
        return blob

    # --------------------------------------------------

    def _distance2bbox(self, points, distance):
        x1 = points[:, 0] - distance[:, 0]
        y1 = points[:, 1] - distance[:, 1]
        x2 = points[:, 0] + distance[:, 2]
        y2 = points[:, 1] + distance[:, 3]
        return np.stack([x1, y1, x2, y2], axis=-1)

    # --------------------------------------------------

    def detect(self, image):
        h0, w0 = image.shape[:2]
        blob = self._preprocess(image)

        outputs = self.session.run(self.output_names, {self.input_name: blob})

        scores_list, bboxes_list = [], []
        input_h = blob.shape[2]
        input_w = blob.shape[3]

        for idx, stride in enumerate(self.strides):
            scores = outputs[idx].reshape(-1)
            bbox_preds = outputs[idx + self.fmc].reshape(-1, 4) * stride

            height = input_h // stride
            width = input_w // stride
            key = (height, width, stride)

            if key in self.center_cache:
                anchor_centers = self.center_cache[key]
            else:
                anchor_centers = np.stack(np.mgrid[:height, :width][::-1], axis=-1)
                anchor_centers = (anchor_centers * stride).reshape((-1, 2)).astype(np.float32)
                if self.num_anchors > 1:
                    anchor_centers = np.stack([anchor_centers] * self.num_anchors, axis=1).reshape((-1, 2))
                self.center_cache[key] = anchor_centers

            pos_inds = np.where(scores > self.conf_thres)[0]
            if len(pos_inds) == 0:
                continue

            bboxes = self._distance2bbox(anchor_centers, bbox_preds)
            scores_list.append(scores[pos_inds])
            bboxes_list.append(bboxes[pos_inds])

        if not scores_list:
            return []

        scores = np.concatenate(scores_list)
        bboxes = np.concatenate(bboxes_list)

        # scale back to original frame
        scale_x = w0 / self.input_size
        scale_y = h0 / self.input_size
        bboxes[:, 0] *= scale_x
        bboxes[:, 2] *= scale_x
        bboxes[:, 1] *= scale_y
        bboxes[:, 3] *= scale_y

        dets = np.hstack((bboxes, scores[:, None])).astype(np.float32)
        keep = self._nms(dets, self.nms_thres)

        results = []
        for i in keep:
            x1, y1, x2, y2, sc = dets[i]
            results.append({
                "box": (int(x1), int(y1), int(x2), int(y2)),
                "score": float(sc)
            })

        return results

    # --------------------------------------------------

    def _nms(self, dets, thresh):
        x1, y1, x2, y2, scores = dets.T
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(ovr <= thresh)[0]
            order = order[inds + 1]

        return keep
