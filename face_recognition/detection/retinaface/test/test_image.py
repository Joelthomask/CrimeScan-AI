# retinaface/test/test_image.py
from __future__ import print_function
import os
import time
import cv2
import torch
import torch.backends.cudnn as cudnn
import numpy as np

from ..data import cfg_mnet, cfg_re50
from ..layers.functions.prior_box import PriorBox
from ..utils.nms.py_cpu_nms import py_cpu_nms
from ..models.retinaface import RetinaFace
from ..utils.box_utils import decode, decode_landm

# ==== USER SETTINGS (edit these two paths) ====
IMAGE_PATH = r"D:\Btech\Criminal_Face_Recognition_System\retinaface\test\test.jpg"
WEIGHTS_PATH = r"D:\Btech\Criminal_Face_Recognition_System\retinaface\weights\ResNet50_Final.pth"
BACKBONE = "resnet50"  # "resnet50" or "mobile0.25"
USE_CPU = False        # set True to force CPU

# Thresholds to exactly match detect.py defaults
CONFIDENCE_THRESHOLD = 0.02
NMS_THRESHOLD = 0.4
TOP_K = 5000
KEEP_TOP_K = 750
VIS_THRES = 0.6          # draw only if score >= this
SAVE_IMAGE = True
DRAW_LANDMARKS = True

# ---- helper funcs copied from detect.py ----
def check_keys(model, pretrained_state_dict):
    ckpt_keys = set(pretrained_state_dict.keys())
    model_keys = set(model.state_dict().keys())
    used_pretrained_keys = model_keys & ckpt_keys
    unused_pretrained_keys = ckpt_keys - model_keys
    missing_keys = model_keys - ckpt_keys
    print('Missing keys:{}'.format(len(missing_keys)))
    print('Unused checkpoint keys:{}'.format(len(unused_pretrained_keys)))
    print('Used keys:{}'.format(len(used_pretrained_keys)))
    assert len(used_pretrained_keys) > 0, 'load NONE from pretrained checkpoint'
    return True

def remove_prefix(state_dict, prefix):
    print("remove prefix '{}'".format(prefix))
    f = lambda x: x.split(prefix, 1)[-1] if x.startswith(prefix) else x
    return {f(k): v for k, v in state_dict.items()}

def load_model(model, pretrained_path, load_to_cpu):
    print('Loading pretrained model from {}'.format(pretrained_path))
    if load_to_cpu:
        pretrained_dict = torch.load(pretrained_path, map_location=lambda s, l: s)
    else:
        device = torch.cuda.current_device()
        pretrained_dict = torch.load(pretrained_path, map_location=lambda s, l: s.cuda(device))
    if "state_dict" in pretrained_dict.keys():
        pretrained_dict = remove_prefix(pretrained_dict['state_dict'], 'module.')
    else:
        pretrained_dict = remove_prefix(pretrained_dict, 'module.')
    check_keys(model, pretrained_dict)
    model.load_state_dict(pretrained_dict, strict=False)
    return model
# --------------------------------------------

def main():
    # pick cfg like detect.py
    if BACKBONE.lower() in ["mobile0.25", "mobilenet0.25", "mobilenet"]:
        cfg = cfg_mnet
    else:
        cfg = cfg_re50

    torch.set_grad_enabled(False)
    cudnn.benchmark = True

    device = torch.device("cpu" if USE_CPU else ("cuda" if torch.cuda.is_available() else "cpu"))

    # build + load
    net = RetinaFace(cfg=cfg, phase='test')
    net = load_model(net, WEIGHTS_PATH, load_to_cpu=(device.type == "cpu"))
    net.eval().to(device)
    print("Finished loading model!")

    # read image
    img_raw = cv2.imread(IMAGE_PATH, cv2.IMREAD_COLOR)
    if img_raw is None:
        raise FileNotFoundError(f"Image not found or unreadable: {IMAGE_PATH}")

    # EXACT preprocessing (same as detect.py)
    img = np.float32(img_raw)
    im_height, im_width, _ = img.shape
    resize = 1  # detect.py uses fixed resize=1 in your version
    scale = torch.Tensor([img.shape[1], img.shape[0], img.shape[1], img.shape[0]])

    img -= (104, 117, 123)
    img = img.transpose(2, 0, 1)
    img = torch.from_numpy(img).unsqueeze(0).to(device)
    scale = scale.to(device)

    # forward
    tic = time.time()
    loc, conf, landms = net(img)
    print('net forward time: {:.4f}s'.format(time.time() - tic))

    # decode (exactly like detect.py)
    priorbox = PriorBox(cfg, image_size=(im_height, im_width))
    priors = priorbox.forward().to(device)
    prior_data = priors.data

    boxes = decode(loc.data.squeeze(0), prior_data, cfg['variance'])
    boxes = boxes * scale / resize
    boxes = boxes.cpu().numpy()

    scores = conf.squeeze(0).data.cpu().numpy()[:, 1]

    landms = decode_landm(landms.data.squeeze(0), prior_data, cfg['variance'])
    scale1 = torch.Tensor([img.shape[3], img.shape[2], img.shape[3], img.shape[2],
                           img.shape[3], img.shape[2], img.shape[3], img.shape[2],
                           img.shape[3], img.shape[2]]).to(device)
    landms = (landms * scale1 / resize).cpu().numpy()

    # threshold filter
    inds = np.where(scores > CONFIDENCE_THRESHOLD)[0]
    boxes = boxes[inds]
    landms = landms[inds]
    scores = scores[inds]

    # top-k before NMS
    order = scores.argsort()[::-1][:TOP_K]
    boxes = boxes[order]
    landms = landms[order]
    scores = scores[order]

    # NMS
    dets = np.hstack((boxes, scores[:, np.newaxis])).astype(np.float32, copy=False)
    keep = py_cpu_nms(dets, NMS_THRESHOLD)
    dets = dets[keep, :]
    landms = landms[keep]

    # keep_top_k (optional, matches detect.py)
    dets = dets[:KEEP_TOP_K, :]
    landms = landms[:KEEP_TOP_K, :]

    # concat for drawing loop (same layout as detect.py)
    dets_all = np.concatenate((dets, landms), axis=1) if len(dets) else dets

    # draw & save
    draw_count = 0
    if SAVE_IMAGE and len(dets_all):
        img_draw = img_raw.copy()
        for b in dets_all:
            if b[4] < VIS_THRES:
                continue
            draw_count += 1
            text = "{:.4f}".format(b[4])
            b = list(map(int, b))
            # box
            cv2.rectangle(img_draw, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 2)
            cv2.putText(img_draw, text, (b[0], b[1] + 12),
                        cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255))
            # landmarks
            if DRAW_LANDMARKS and len(b) >= 15:
                cv2.circle(img_draw, (b[5],  b[6]),  1, (0, 0, 255), 4)   # right eye
                cv2.circle(img_draw, (b[7],  b[8]),  1, (0, 255, 255), 4) # left eye
                cv2.circle(img_draw, (b[9],  b[10]), 1, (255, 0, 255), 4) # nose
                cv2.circle(img_draw, (b[11], b[12]), 1, (0, 255, 0), 4)   # mouth right
                cv2.circle(img_draw, (b[13], b[14]), 1, (255, 0, 0), 4)   # mouth left

        folder, filename = os.path.split(IMAGE_PATH)
        name, ext = os.path.splitext(filename)
        out_path = os.path.join(folder, f"{name}_detected{ext}")
        cv2.imwrite(out_path, img_draw)
        print(f"Saved: {out_path}")

    print(f"Detections above VIS_THRES ({VIS_THRES}): {draw_count}")
    print(f"Raw detections after NMS (any score > {CONFIDENCE_THRESHOLD}): {len(dets)}")

if __name__ == "__main__":
    main()
