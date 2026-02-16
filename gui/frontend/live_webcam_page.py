import cv2
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox, QSizePolicy
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
import time
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QScrollArea
from collections import deque
from ..backend.live_webcam_backend import get_live_backend
from utils.logger import get_logger
LOG = get_logger()



class RecognitionDropItem(QFrame):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.person_name = name
        self.best_match = 0.0

        self.setStyleSheet("""
        QFrame {
            background-color: rgba(0,0,0,120);
            border: 1.5px solid rgba(0,246,255,120);
            border-radius: 8px;
        }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 6)
        self.main_layout.setSpacing(6)

        # ========= HEADER =========
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        self.header_btn = QPushButton(name)
        self.header_btn.setCursor(Qt.PointingHandCursor)
        self.header_btn.setStyleSheet("""
        QPushButton {
            text-align: left;
            color: #00f6ff;
            font-size: 13px;
            font-weight: 600;
            border: none;
            background: transparent;
        }
        """)

        self.arrow = QLabel("▶")
        self.arrow.setStyleSheet("color:#00f6ff; font-size:14px;")

        header_layout.addWidget(self.header_btn)
        header_layout.addStretch()
        header_layout.addWidget(self.arrow)

        header.setStyleSheet("""
        QWidget { background: transparent; }
        QWidget:hover { background: rgba(0,246,255,35); }
        """)


        self.main_layout.addWidget(header)

        # ========= CONTENT =========
        self.content = QWidget()
        self.content.setAttribute(Qt.WA_StyledBackground, False)
        self.content.setStyleSheet("background: transparent; border: none;")

        self.content.setAttribute(Qt.WA_StyledBackground, False)

        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(6, 6, 6, 6)
        self.content_layout.setSpacing(8)

        self.name_lbl = QLabel(f"Name :  {name}")
        self.match_lbl = QLabel("Match :  0 %")
        self.status_lbl = QLabel("⚠  Suspect")
        self.mask_lbl = QLabel("Mask :  No Mask ❌")

        for lbl in [self.name_lbl, self.match_lbl, self.mask_lbl]:
            lbl.setStyleSheet("""
                QLabel {
                    background: transparent;
                    border: none;
                    outline: none;
                    color: #e6faff;
                    font-size: 13px;
                    padding: 2px 0px;
                }
            """)



        self.status_lbl.setStyleSheet("""
        QLabel {
            background: rgba(255,180,60,40);
            color: #ffb84d;
            padding: 6px;
            border-radius: 6px;
            font-weight:600;
        }
        """)

        def line():
            l = QFrame()
            l.setFixedHeight(1)
            l.setStyleSheet("background: rgba(0,246,255,80);")
            return l
        self.desc = QLabel(f"Face matched with database record.\n{name} flagged as suspect.")

        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("""
        QLabel {
            background: transparent;
            border: none;
            outline: none;
            padding: 4px 0px;
            color: #cfefff;
            font-size: 12px;
        }
        """)
        self.desc.setAttribute(Qt.WA_StyledBackground, False)

        self.content_layout.addWidget(self.name_lbl)
        self.content_layout.addWidget(line())
        self.content_layout.addWidget(self.match_lbl)
        self.content_layout.addWidget(line())
        self.content_layout.addWidget(self.status_lbl)
        self.content_layout.addWidget(line())
        self.content_layout.addWidget(self.mask_lbl)
        self.content_layout.addWidget(line())
        self.content_layout.addWidget(self.desc)

        self.content.setVisible(False)
        self.main_layout.addWidget(self.content)

        self.expanded = False
        self.header_btn.clicked.connect(self.toggle)
        header.mousePressEvent = lambda e: self.toggle()
        self.status_lbl.hide()
        self.last_mask = None
    def update_mask(self, mask_label):
        if mask_label != self.last_mask:
            self.last_mask = mask_label

            if mask_label.lower() == "mask":
                self.mask_lbl.setText("Mask :  Mask 😷")
            else:
                self.mask_lbl.setText("Mask :  No Mask ❌")



    def toggle(self):
        # find the real recognized_layout safely
        container = self.parentWidget()
        layout = container.layout()

        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if isinstance(w, RecognitionDropItem) and w != self:
                w.collapse()

        self.expanded = not self.expanded
        self.content.setVisible(self.expanded)
        self.arrow.setText("▼" if self.expanded else "▶")


    def collapse(self):
        self.expanded = False
        self.content.setVisible(False)
        self.arrow.setText("▶")

    def update_match(self, percent):
        if percent > self.best_match:
            self.best_match = percent
            self.match_lbl.setText(f"Match :  {percent:.1f} %")

            if percent >= 60:
                self.status_lbl.setText("⚠  Suspect")
                self.status_lbl.show()
                self.desc.setText(
                    f"Face matched with database record.\n{self.person_name} flagged as suspect."
                )
            else:
                self.status_lbl.hide()
                self.desc.setText(
                    f"Face matched with database record.\n{self.person_name} under observation."
                )




class LiveWebcamPage(QWidget):
    def __init__(self, stacked_widget, main_menu, device="cuda"):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.main_menu = main_menu
        self.device = device
        self.last_frame = None

        LOG.info("[LIVE-UI] Live webcam page opened")
        LOG.info(f"[LIVE-UI] UI device mode set to: {device}")



        self.fps_window = deque(maxlen=30)   # last 30 frames
        self.fps = 0.0

        self.backend = None



        # --- Webcam setup ---
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.unknown_count = 0
        self.unknown_faces = {}

        # --- Layout ---
        vbox = QVBoxLayout()
        vbox.setContentsMargins(30, 10, 30, 20)
        vbox.setSpacing(10)
        # ================= FIXED TITLE =================
        self.title_label = QLabel("LIVE WEBCAM", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFixedHeight(45)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #00f6ff;
                font-size: 24px;
                font-weight: 600;
                letter-spacing: 1px;
            }
        """)

        vbox.addSpacing(15) 

        vbox.addWidget(self.title_label, alignment=Qt.AlignTop)

        # ================= GLOW DIVIDER (BELOW TITLE) =================
        self.title_divider = QFrame()
        self.title_divider.setFixedHeight(3)
        self.title_divider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.title_divider.setStyleSheet("""
        QFrame {
            border: none;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(0, 246, 255, 0),
                stop:0.2 rgba(0, 246, 255, 80),
                stop:0.5 rgba(0, 246, 255, 255),
                stop:0.8 rgba(0, 246, 255, 80),
                stop:1 rgba(0, 246, 255, 0)
            );
        }
        }
        """)
        # ---------- TOP SPACE ----------
        vbox.addSpacing(15)   # you can try 10–25 for perfect look

        vbox.addWidget(self.title_divider)


        # ================= VIDEO CONTAINER (LOCKED) =================
        self.video_container = QFrame()
        self.video_container.setFixedSize(1300, 680)   # 👈 choose once, never changes
        self.video_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)

        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)

        # --- Video label (inside locked container) ---
        self.video_label = QLabel("Webcam starting...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 3px solid qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 cyan, stop:1 #00b7ff
                );
                border-radius: 8px;
                background-color: black;
                color: white;
                font-size: 16px;
            }
        """)

        self.video_label.setFixedSize(1300, 680)  # 👈 CRITICAL (same as container)
        self.video_label.setScaledContents(True)

        video_layout.addWidget(self.video_label)
        # ---------- CENTERING SPACERS ----------
        # ---------- SPACE BETWEEN DIVIDER & VIDEO ----------
        vbox.addSpacing(20)   # try 5–15 for perfect look

        vbox.addWidget(self.video_container, alignment=Qt.AlignHCenter)
        # ================= VIDEO CONTROL BAR =================

        # ---- Back button (icon only) ----
        self.back_control_btn = QPushButton("⤺", self)   # premium return icon

        self.back_control_btn.setFixedSize(60, 60)
        self.back_control_btn.setCursor(Qt.PointingHandCursor)
        self.back_control_btn.clicked.connect(self.go_back)
        self.back_control_btn.setStyleSheet("""
        QPushButton {
            font-size: 28px;
            color: cyan;
            border-radius: 30px;
            background-color: rgba(0,0,0,160);
            border: 2.5px solid qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 cyan,
                stop:1 #00b7ff
            );
        }
        QPushButton:hover {
            background-color: rgba(0,246,255,40);
        }
        """)

        # ---- Play / Pause button ----
        self.play_pause_btn = QPushButton("⏸", self)
        self.play_pause_btn.setFixedSize(70, 70)
        self.play_pause_btn.setCursor(Qt.PointingHandCursor)
        self.play_pause_btn.clicked.connect(self.toggle_camera)
        self.play_pause_btn.setStyleSheet("""
        QPushButton {
            font-size: 30px;
            color: cyan;
            border-radius: 35px;
            background-color: rgba(0,0,0,160);
            border: 2.5px solid qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 cyan,
                stop:1 #00b7ff
            );
        }
        QPushButton:hover {
            background-color: rgba(0,246,255,40);
        }
        """)

        # ---- Capture button ----
        self.capture_btn = QPushButton("◉", self)

        self.capture_btn.setFixedSize(60, 60)
        self.capture_btn.setCursor(Qt.PointingHandCursor)
        self.capture_btn.clicked.connect(self.capture_frame)
        self.capture_btn.setStyleSheet("""
        QPushButton {
            font-size: 35px;
            color: cyan;
            border-radius: 30px;
            background-color: rgba(0,0,0,160);
            border: 2.5px solid qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 cyan,
                stop:1 #00b7ff
            );
        }
        QPushButton:hover {
            background-color: rgba(0,246,255,40);
        }
        """)
        # ---- Mask Toggle ----
        self.mask_toggle_btn = QPushButton("😷 ON", self)
        self.mask_toggle_btn.setFixedSize(90, 60)
        self.mask_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.mask_toggle_btn.clicked.connect(self.toggle_mask)
        self.mask_toggle_btn.setStyleSheet("""
        QPushButton {
            font-size: 16px;
            color: cyan;
            border-radius: 12px;
            background-color: rgba(0,0,0,160);
            border: 2px solid cyan;
        }
        QPushButton:hover {
            background-color: rgba(0,246,255,40);
        }
        """)
        # ---- Control row ----
        control_row = QHBoxLayout()
        control_row.addStretch()
        control_row.addWidget(self.back_control_btn)
        control_row.addSpacing(25)
        control_row.addWidget(self.play_pause_btn)
        control_row.addSpacing(25)
        control_row.addWidget(self.capture_btn)
        control_row.addSpacing(25)
        control_row.addWidget(self.mask_toggle_btn)


        control_row.addStretch()

        vbox.addSpacing(20)
        vbox.addLayout(control_row)


        # ---------- PUSH EVERYTHING ELSE DOWN ----------
        vbox.addStretch(1)



        # --- FPS & status tracking ---
        self.prev_time = time.time()
        self.fps = 0

        # --- Overlay container ---
        self.overlay = QFrame(self.video_label)
        self.overlay.setFixedSize(200, 70)
        self.setMinimumSize(1200, 750)

        self.overlay.move(self.video_label.width() - 220, 20)
        self.overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 160);
                border: 2px solid qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 cyan, stop:1 #00b7ff
                );
                border-radius: 10px;
            }
        """)

        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(12, 8, 12, 8)

        self.status_label = QLabel("Camera: OFF")
        self.status_label.setStyleSheet("color: #00f6ff; font-weight: bold;")

        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setStyleSheet("color: white;")

        overlay_layout.addWidget(self.status_label)
        overlay_layout.addWidget(self.fps_label)

        self.overlay.show()




        self.setLayout(vbox)
        # ================= FLOATING RECOGNITION PANEL =================
        # ================= FLOATING RECOGNITION PANEL =================
        self.details_panel = QFrame(self)
        self.details_panel.setFixedSize(272, 680)
        self.details_panel.setStyleSheet("""
        QFrame {
            background-color: rgba(0, 0, 0, 140);
            border: 3px solid qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 cyan,
                stop:1 #00b7ff
            );
            border-radius: 10px;
        }
        """)



        panel_layout = QVBoxLayout(self.details_panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(6)
        panel_layout.setAlignment(Qt.AlignTop)   # 🔥 CRITICAL

        # ---- Header ----
        title = QLabel("RECOGNITION DETAILS")
        title.setAlignment(Qt.AlignCenter)
        title.setFixedHeight(24)
        title.setStyleSheet("""
        QLabel {
            color: #00f6ff;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 1.4px;
            background: transparent;
            border: none;
        }
        """)
        panel_layout.addWidget(title, alignment=Qt.AlignTop)


        # ---- Divider (immediately under title) ----
        panel_divider = QFrame()
        panel_divider.setFixedHeight(3)
        panel_divider.setStyleSheet("""
        QFrame {
            border: none;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(0,246,255,0),
                stop:0.2 rgba(0,246,255,90),
                stop:0.5 rgba(0,246,255,255),
                stop:0.8 rgba(0,246,255,90),
                stop:1 rgba(0,246,255,0)
            );
        }
        """)
        panel_layout.addWidget(panel_divider, alignment=Qt.AlignTop)



        self.details_panel.show()
        # ---- Recognized list container ----
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
        QScrollArea {
            border: none;
            background: transparent;
        }
        QScrollArea QWidget {
            background: transparent;
        }
        """)


        self.recognized_container = QWidget()
        self.recognized_layout = QVBoxLayout(self.recognized_container)
        self.recognized_layout.setAlignment(Qt.AlignTop)
        self.recognized_layout.setSpacing(10)

        self.scroll.setWidget(self.recognized_container)
        panel_layout.addWidget(self.scroll)


        # ---- Memory to avoid duplicates ----
        self.recognized_names = set()

        # ================= FLOATING UNKNOWN PANEL (LEFT) =================
        self.unknown_panel = QFrame(self)
        self.unknown_panel.setFixedSize(272, 680)
        self.unknown_panel.setStyleSheet("""
        QFrame {
            background-color: rgba(0, 0, 0, 140);
            border: 3px solid qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 cyan,
                stop:1 #00b7ff
            );
            border-radius: 10px;
        }
        """)

        unknown_layout = QVBoxLayout(self.unknown_panel)
        unknown_layout.setContentsMargins(14, 12, 14, 12)
        unknown_layout.setSpacing(6)
        unknown_layout.setAlignment(Qt.AlignTop)

        unknown_title = QLabel("UNIDENTIFIED PERSONS")
        unknown_title.setAlignment(Qt.AlignCenter)
        unknown_title.setFixedHeight(24)

        # 🔥 Force remove any box / rounded effect
        unknown_title.setFrameStyle(QFrame.NoFrame)
        unknown_title.setStyleSheet("""
        QLabel {
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
            margin: 0px;

            color: #00f6ff;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 1.4px;
        }
        """)

        unknown_layout.addWidget(unknown_title)


        unknown_divider = QFrame()
        unknown_divider.setFixedHeight(3)
        unknown_divider.setStyleSheet("""
        QFrame {
            border: none;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(0,246,255,0),
                stop:0.2 rgba(0,246,255,90),
                stop:0.5 rgba(0,246,255,255),
                stop:0.8 rgba(0,246,255,90),
                stop:1 rgba(0,246,255,0)
            );
        }
        """)
        unknown_layout.addWidget(unknown_divider)

        self.unknown_scroll = QScrollArea()
        self.unknown_scroll.setWidgetResizable(True)
        self.unknown_scroll.setStyleSheet("""
        QScrollArea { border: none; background: transparent; }
        QScrollArea QWidget { background: transparent; }
        """)

        self.unknown_container = QWidget()
        self.unknown_layout = QVBoxLayout(self.unknown_container)
        self.unknown_layout.setAlignment(Qt.AlignTop)
        self.unknown_layout.setSpacing(10)

        self.unknown_scroll.setWidget(self.unknown_container)
        unknown_layout.addWidget(self.unknown_scroll)

        self.unknown_panel.show()

 

    def add_recognized_person(self, name, similarity, mask_label):

        for i in range(self.recognized_layout.count()):
            w = self.recognized_layout.itemAt(i).widget()
            if w.person_name == name:
                w.update_mask(mask_label)
                w.update_match(similarity)
                return

        if similarity < 50:
            return

        LOG.info(f"[LIVE-UI] Recognized | name={name} | score={similarity:.1f} | mask={mask_label}")


        item = RecognitionDropItem(name)


        self.recognized_layout.addWidget(item)
        self.recognized_names.add(name)
        item.update_match(similarity)
        item.update_mask(mask_label)




    def resizeEvent(self, event):
        super().resizeEvent(event)

        # --- Overlay top-right of video ---
        self.overlay.move(self.video_label.width() - 220, 20)


        # --- Recognition panel right side (LOCKED to video frame) ---
        panel_margin = 20

        video_pos = self.video_container.mapTo(self, self.video_container.rect().topRight())

        x = video_pos.x() + panel_margin
        y = video_pos.y()

        self.details_panel.move(x, y)
        # --- LEFT unknown panel ---
        left_margin = 20
        video_pos_left = self.video_container.mapTo(self, self.video_container.rect().topLeft())
        ux = video_pos_left.x() - self.unknown_panel.width() - left_margin
        uy = video_pos_left.y()
        self.unknown_panel.move(ux, uy)




    def go_back(self):
        LOG.info("[LIVE-UI] Operator exited live webcam page")


        if self.cap:
            self.cap.release()
            self.cap = None

        self.timer.stop()
        self.backend.shutdown()   # 🔥 ensures summary log

        self.stacked_widget.setCurrentWidget(self.main_menu)
        self.status_label.setText("Camera: OFF")
        self.fps_label.setText("FPS: 0")


    def start_camera(self):
        if self.backend is None:
            LOG.info("[LIVE-UI] Creating Live Webcam Backend (lazy init)")
            self.backend = get_live_backend(device=self.device)

        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        LOG.info("[LIVE-UI] Camera start requested (source=0, 1280x720)")


        if not self.cap.isOpened():
            LOG.info("[ERROR][LIVE-UI] Camera open FAILED")

            QMessageBox.critical(self, "Error", "Unable to access webcam.")
            self.status_label.setText("Camera: OFF")
            return

        self.timer.start(15)
        self.status_label.setText("Camera: ON")
        self.prev_time = time.time()

        LOG.info("[LIVE-UI] Camera started successfully")



    def update_frame(self):
        if self.backend is None:
            return
        if not self.cap:
            return

        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.video_label.setText("Error: Unable to read frame")
            return

        frame = cv2.flip(frame, 1)
        results = self.backend.detect_and_match(frame)

        for res in results:
            x1, y1, x2, y2 = res["box"]
            mask_label = res["mask_label"]
            mask_conf = res["mask_conf"]

            color = (0, 255, 0) if mask_label == "Mask" else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            cv2.putText(frame, f"{mask_label} ({mask_conf*100:.1f}%)",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # ---- Unknown / Known handling ----

            recognized = False

            for rank, (name, sim) in enumerate(res["matches"]):

                # ✅ Dynamic threshold
                if (mask_label == "Mask" and sim >= 28) or (mask_label != "Mask" and sim >= 50):

                    recognized = True
                    self.add_recognized_person(name, sim, mask_label)

                    cv2.putText(frame, f"{rank+1}: {name} ({sim:.1f}%)",
                                (x1, y2 + 20 + rank*20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    break


            # ---- If nobody crossed DB threshold → UNKNOWN (grouped by IoU) ----
            if not recognized:
                self.add_unknown_person(res["box"], mask_label)
                cv2.putText(frame, "Unknown",
                            (x1, y2 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 180, 255), 2)


        # --- FPS calculation ---
        current_time = time.time()
        dt = current_time - self.prev_time
        self.prev_time = current_time

        if dt > 0:
            inst_fps = 1.0 / dt
            self.fps_window.append(inst_fps)

        if len(self.fps_window) > 0:
            self.fps = sum(self.fps_window) / len(self.fps_window)

        self.fps_label.setText(f"FPS: {self.fps:.1f}")

        self.status_label.setText("Camera: ON")
        self.last_frame = frame.copy()

        if self.backend.frame_id % 2 == 0:
            self._display_frame(frame)



    def _display_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        qt_frame = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_frame))

    def closeEvent(self, event):
        LOG.info("[LIVE-UI] Live webcam page closed (window event)")


        if self.cap:
            self.cap.release()

        self.timer.stop()
        if self.backend:
            self.backend.shutdown()

        event.accept()

        self.status_label.setText("Camera: OFF")
        self.fps_label.setText("FPS: 0")

    def add_unknown_person(self, box, mask_label):

        matched_id = self._match_unknown(box)

        if matched_id is not None:
            self.unknown_faces[matched_id]["item"].update_mask(mask_label)
            self.unknown_faces[matched_id]["box"] = box
            return

        # -------- New unknown --------
        self.unknown_count += 1
        LOG.info(f"[LIVE-UI] New unknown detected | id={self.unknown_count} | mask={mask_label}")


        name = f"Unknown #{self.unknown_count}"

        item = RecognitionDropItem(name)
        self.unknown_layout.addWidget(item)

        item.match_lbl.setText("Match :  Not in Database")
        item.status_lbl.hide()
        item.desc.setText("Face not found in database.\nUnidentified individual.")
        item.update_mask(mask_label)

        self.unknown_faces[self.unknown_count] = {
            "box": box,
            "item": item
        }

    def toggle_camera(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_pause_btn.setText("▶")
            self.status_label.setText("Camera: PAUSED")
            LOG.info("[LIVE-UI] Camera paused by operator")

        else:
            if self.cap and self.cap.isOpened():
                self.timer.start(30)
                self.play_pause_btn.setText("⏸")
                self.status_label.setText("Camera: ON")
                LOG.info("[LIVE-UI] Camera resumed by operator")


    def capture_frame(self):
        if self.last_frame is None:
            QMessageBox.warning(self, "No Frame", "No frame available to capture.")
            LOG.info("[WARN][LIVE-UI] Snapshot failed (no frame)")

            return

        from PyQt5.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Capture",
            "capture.png",
            "Images (*.png *.jpg *.jpeg)"
        )

        if filename:
            cv2.imwrite(filename, self.last_frame)
            QMessageBox.information(self, "Saved", "Snapshot saved successfully.")
            LOG.info(f"[LIVE-UI] Snapshot captured and saved → {filename}")


    def _iou(self, a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0

        inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)

        return inter / float(area_a + area_b - inter)


    def _match_unknown(self, box):
        for uid, data in self.unknown_faces.items():
            if self._iou(box, data["box"]) > 0.4:
                return uid
        return None
    def toggle_mask(self):
        if self.backend is None:
            return

        enabled = not self.backend.mask_enabled
        self.backend.set_mask_enabled(enabled)

        if enabled:
            self.mask_toggle_btn.setText("😷 ON")
        else:
            self.mask_toggle_btn.setText("😷 OFF")