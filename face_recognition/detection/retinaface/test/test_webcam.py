import cv2
from ..detector import RetinaFaceDetector


detector = RetinaFaceDetector(
    backbone="mobilenet0.25",
    weights_path="D:/Btech/Criminal_Face_Recognition_System/retinaface/weights/mobilenet0.25_Final.pth",
    device="cuda"
)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    dets, landms = detector.detect(frame, conf_thresh=0.8)
    frame = detector.draw_detections(frame, dets, landms)

    cv2.imshow("Webcam - RetinaFace", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
