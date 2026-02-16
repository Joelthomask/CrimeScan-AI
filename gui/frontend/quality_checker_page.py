from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QSpacerItem, QSizePolicy
)

from PyQt5.QtGui import QFont, QPainter, QColor, QBrush, QPen, QLinearGradient
from PyQt5.QtCore import Qt, QRectF, QPointF
from gui.backend.forensic_backend import ForensicBackend
from utils.logger import get_logger
LOG = get_logger()

from gui.frontend.enhancement_page import AutoEnhancementPage

from PyQt5.QtCore import QTimer



class QualityCheckerPage(QWidget):
    def __init__(self, stacked_widget=None, crime_scan_page=None, main_menu=None, image_path=None):

        super().__init__()

        # === Core attributes ===
        self.image_path = image_path
        self.pipeline_started = False


        self.stacked_widget = stacked_widget
        self.crime_scan_page = crime_scan_page
        self.main_menu = main_menu


        LOG.info("[QC UI] QualityCheckerPage initialized.")
        self.results = {}
        self.raw_issue_map = {}
        self.decision_map = {}

        self.backend = None
        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._on_timer_tick)
        self.auto_seconds = 10
        self.timer_active = False


        # === Auto Enhancement Page ===
        self.enhancement_page = AutoEnhancementPage()
        self.stacked_widget.addWidget(self.enhancement_page)



        # === Other UI / State setup ===
        # === Other UI / State setup ===
        self.active_btn = None
        self.active_check = 0

        self.preqc_titles = ["BLUR", "BRIGHTNESS", "RESOLUTION", "CONTRAST", "NOISE"]
        self.postqc_titles = ["MASK", "POSE"]

        self.preqc_status = [True] * len(self.preqc_titles)
        self.postqc_status = [True] * len(self.postqc_titles)

        self.preqc_status_text = ["Starting QC..."] * len(self.preqc_titles)
        self.postqc_status_text = ["Starting QC..."] * len(self.postqc_titles)

        self.current_titles = self.preqc_titles
        self.current_status = self.preqc_status
        self.current_status_text = self.preqc_status_text

        self.check_boxes = []

        # ✅ NEW — PREVENT CRASHES
        self.postqc_issue_map = {
            "mask": "QC not ready",
            "pose": "QC not ready"
        }

        self.postqc_ready = False   # blocks early PostQC clicks

        self.init_ui()




    # ================== UI Setup ==================
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === TOP BUTTONS ===
        self.button_panel_top = QWidget()
        self.button_panel_top.setStyleSheet("background: transparent;")
        top_layout = QHBoxLayout(self.button_panel_top)
        top_layout.setContentsMargins(0, 25, 0, 0)
        top_layout.setSpacing(25)
        top_layout.setAlignment(Qt.AlignCenter)

        self.preqc_btn = QPushButton("PreQC")
        self.postqc_btn = QPushButton("PostQC")

        for btn in [self.preqc_btn, self.postqc_btn]:
            btn.setFont(QFont("Segoe UI", 11))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(130, 45)

        self.set_button_style(self.preqc_btn, active=True)
        self.set_button_style(self.postqc_btn, active=False)
        self.active_btn = self.preqc_btn

        self.preqc_btn.clicked.connect(lambda: self.toggle_section(self.preqc_btn))
        self.postqc_btn.clicked.connect(lambda: self.toggle_section(self.postqc_btn))

        top_layout.addWidget(self.preqc_btn)
        top_layout.addWidget(self.postqc_btn)
        main_layout.addWidget(self.button_panel_top)
        self.postqc_btn.setEnabled(False)

        # === TITLE ===
        main_layout.addSpacerItem(QSpacerItem(0, 24, QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.title_label = QLabel("QUALITY CHECKER")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: white; background: transparent; font-size: 44px; font-weight: 700;")
        main_layout.addWidget(self.title_label, alignment=Qt.AlignCenter)

        # === PARAGRAPH AREA ===
        main_layout.addSpacerItem(QSpacerItem(0, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.desc_label = QLabel("")

        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMinimumHeight(120)

        # 🔥 Allow it to scale with window
        self.desc_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        # 🔥 Remove hard width cap
        # (this was causing clipping)
        # self.desc_label.setMaximumWidth(1000)

        self.desc_label.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                background: transparent;
                font-size: 16px;
                line-height: 1.5;
                padding-left: 120px;
                padding-right: 120px;
            }
        """)

        main_layout.addWidget(self.desc_label, alignment=Qt.AlignCenter)

        # === STATUS LABEL ===
        main_layout.addSpacerItem(QSpacerItem(0, 105, QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.status_label = QLabel("Status")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: white; font-size: 22px; font-weight: 600; background: transparent;")
        main_layout.addWidget(self.status_label, alignment=Qt.AlignCenter)



        # === BOTTOM PANEL (Boxes) ===
        main_layout.addSpacerItem(QSpacerItem(0, 45, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.bottom_panel = QWidget()
        self.bottom_panel.setStyleSheet("background: transparent;")
        self.bottom_layout = QHBoxLayout(self.bottom_panel)
        self.bottom_layout.setContentsMargins(240, 0, 240, 0)
        self.bottom_layout.setSpacing(6)
        self.create_check_boxes(self.preqc_titles)
        main_layout.addWidget(self.bottom_panel)

        # === BACK/NEXT BUTTONS ===
        self.button_panel_bottom = QWidget()
        self.button_panel_bottom.setStyleSheet("background: transparent; border: none;")
        button_layout = QHBoxLayout(self.button_panel_bottom)
        button_layout.setSpacing(30)
        button_layout.setContentsMargins(0, 60, 0, 40)
        button_layout.setAlignment(Qt.AlignCenter)

        self.back_btn = QPushButton("BACK")
        self.next_btn = QPushButton("NEXT")
        self.start_btn = QPushButton("START")

        for btn in [self.back_btn, self.next_btn]:
            btn.setFixedSize(150, 55)
            btn.setFont(QFont("Segoe UI", 12, QFont.Medium))

        self.back_btn.setStyleSheet("""
        QPushButton {
            color: white;
            background-color: rgba(255, 255, 255, 20);
            border: 1px solid rgba(255,255,255,60);
            border-radius: 6px;
        }

        QPushButton:hover {
            color: rgb(0,220,255);
            border-color: rgb(0,220,255);
            background-color: rgba(0,220,255,30);
        }
        """)


        self.next_btn.setStyleSheet("""
            QPushButton {
                color: black;
                font-weight: 600;
                border: none;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 rgb(0, 255, 255),
                                            stop:1 rgb(0, 180, 255));
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 rgb(0, 220, 255),
                                            stop:1 rgb(0, 140, 255));
            }
        """)
        self.start_btn.setFixedSize(150, 55)
        self.start_btn.setFont(QFont("Segoe UI", 12, QFont.Medium))
        self.start_btn.setCursor(Qt.PointingHandCursor)

        self.start_btn.setStyleSheet("""
            QPushButton {
                color: black;
                font-weight: 600;
                border: none;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 rgb(0, 255, 255),
                                            stop:1 rgb(0, 180, 255));
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 rgb(0, 220, 255),
                                            stop:1 rgb(0, 140, 255));
            }
        """)




        self.start_btn.hide()
        self.start_btn.clicked.connect(self.handle_enhance)
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.start_btn)

        main_layout.addWidget(self.button_panel_bottom, alignment=Qt.AlignCenter)

        # Connect back/next
        self.back_btn.clicked.connect(self.go_back)
        self.next_btn.clicked.connect(self.next_check)
    def load_results(self):
        if getattr(self, "_results_loaded", False):
            return

        self._results_loaded = True

        qc = self.qc_report
        intel = self.intelligence_preview or {}

        decision = intel.get("decision", {})
        quality_flags = decision.get("quality_flags", {})

        actions = decision.get("recommended_actions", [])

        # ---------------------------
        # BUILD DECISION MAP FIRST
        # ---------------------------
        self.decision_map = self.build_decision_map(qc, intel)


        # ---------------------------
        # PRE-QC (USE POLICY FLAGS)
        # ---------------------------
        for idx, key in enumerate(self.preqc_titles):

            k = key.lower()
            flagged = quality_flags.get(f"{k}_bad", False)

            if flagged:
                self.preqc_status[idx] = False
                self.preqc_status_text[idx] = "Issue detected"
            else:
                self.preqc_status[idx] = True
                self.preqc_status_text[idx] = "OK"

            self.raw_issue_map[k] = self.preqc_status_text[idx]


        # ---------------------------
        # POST-QC (MASK + POSE)
        # ---------------------------

        # MASK
        masked = quality_flags.get("mask_bad", False)
        self.postqc_status[0] = not masked
        self.postqc_status_text[0] = "Mask detected" if masked else "No mask"

        # POSE
        bad_pose = quality_flags.get("pose_bad", False)
        self.postqc_status[1] = not bad_pose
        self.postqc_status_text[1] = "Bad pose" if bad_pose else "Pose OK"

        # Map for description panel
        self.postqc_issue_map = {
            "mask": self.postqc_status_text[0],
            "pose": self.postqc_status_text[1]
        }


        # ---------------------------
        # INITIAL DISPLAY (PREQC FIRST)
        # ---------------------------
        self.current_titles = self.preqc_titles
        self.current_status = self.preqc_status
        self.current_status_text = self.preqc_status_text

        self.create_check_boxes(self.current_titles)
        self.update_check_display(0)

        # 🔥 FORCE POSTQC DATA TO BE READY
        self.postqc_ready = True
        self.postqc_btn.setEnabled(True)

        LOG.info("[QC UI] QC UI UPDATED WITH RESULTS")






    def update_check_display(self, idx):
        if idx < 0 or idx >= len(self.current_titles):
            return

        self.active_check = idx

        # ❌ DO NOT show metric words in status label
        # Status label is now only for system messages
        if self.current_status[idx]:
            self.status_label.setStyleSheet("color: cyan; font-size: 22px; font-weight: 600;")
        else:
            self.status_label.setStyleSheet("color: red; font-size: 22px; font-weight: 600;")

        key = self.current_titles[idx].lower()
        if key in ["mask", "pose"]:
            self.on_postqc_clicked(key)
        else:
            self.on_metric_clicked(key)


        self.update()



    # ================== Navigation ==================
    def next_check(self):
        # Move to next check
        if self.active_check + 1 < len(self.current_titles):
            self.update_check_display(self.active_check + 1)
        else:
            # Switch section
            if self.active_btn == self.preqc_btn:
                self.toggle_section(self.postqc_btn)
                self.update_check_display(0)
            else:
                LOG.info("[INFO] All checks completed")
    def go_back(self):

        LOG.info("[QC UI] User aborted forensic pipeline. HARD stopping...")

        # --------------------------------------------------
        # 1️⃣ HARD STOP BACKEND (thread + engine)
        # --------------------------------------------------
        if self.backend:
            try:
                self.backend.stop()
            except Exception as e:
                LOG.info("[QC UI][WARN] Backend stop error:", e)

            self.backend = None

        # --------------------------------------------------
        # 2️⃣ STOP QC AUTO TIMER
        # --------------------------------------------------
        if self.timer_active:
            self.auto_timer.stop()
            self.timer_active = False
            self.releaseKeyboard()

        # --------------------------------------------------
        # 3️⃣ HARD RESET ENHANCEMENT PAGE
        # --------------------------------------------------
        try:
            if self.enhancement_page:

                if self.enhancement_page.final_timer.isActive():
                    self.enhancement_page.final_timer.stop()

                self.enhancement_page.final_timer_active = False
                self.enhancement_page.results_ready = False
                self.enhancement_page.current_step_index = 0
                self.enhancement_page.active_module = None

        except Exception as e:
            LOG.info("[QC UI][WARN] Enhancement reset error:", e)

        # --------------------------------------------------
        # 4️⃣ Restore original image reference
        # --------------------------------------------------
        if self.crime_scan_page:
            self.crime_scan_page.image_path = self.image_path

        # --------------------------------------------------
        # 5️⃣ Navigate back safely
        # --------------------------------------------------
        if self.crime_scan_page:
            self.stacked_widget.setCurrentWidget(self.crime_scan_page)
        else:
            self.stacked_widget.setCurrentWidget(self.main_menu)

        # --------------------------------------------------
        # 6️⃣ OPTIONAL: restart recognition
        # (Remove if it causes re-entry issues)
        # --------------------------------------------------
        if self.crime_scan_page and self.image_path:
            try:
                self.crime_scan_page.start_recognition(self.image_path)
            except Exception as e:
                LOG.info("[QC UI][WARN] Recognition restart failed:", e)


    # ================== Section Toggle ==================
    def toggle_section(self, clicked_button):

        # 🚫 Block PostQC before QC ready
        if clicked_button == self.postqc_btn and not self.postqc_ready:
            LOG.info("[QC UI] PostQC blocked — QC not ready yet")
            return

        # 🚫 Block switching during timer/QC
        # Allow switching after QC results are ready
        if self.timer_active and not self.postqc_ready:
            LOG.info("[QC UI] Section switch blocked during QC")
            return

        if self.active_btn == clicked_button:
            return

        self.set_button_style(self.active_btn, active=False)
        self.set_button_style(clicked_button, active=True)
        self.active_btn = clicked_button

        self.desc_label.setText("")
        self.status_label.setText("QC Completed — Review & Continue")
        self.status_label.setStyleSheet(
            "color: cyan; font-size: 22px; font-weight: 600;"
        )

        if clicked_button == self.preqc_btn:
            self.current_titles = self.preqc_titles
            self.current_status = self.preqc_status
            self.current_status_text = self.preqc_status_text

            self.bottom_layout.setSpacing(5)
            self.bottom_layout.setContentsMargins(240, 0, 240, 0)

        else:
            self.current_titles = self.postqc_titles
            self.current_status = self.postqc_status
            self.current_status_text = self.postqc_status_text

            self.bottom_layout.setSpacing(15)
            self.bottom_layout.setContentsMargins(600, 0, 600, 0)

        if len(self.check_boxes) != len(self.current_titles):
            self.create_check_boxes(self.current_titles)

        self.update_check_display(0)


        # ================== Handle Enhance ==================
    def handle_enhance(self):

        if self.pipeline_started:
            LOG.info("[QC UI] Enhancement already started — ignoring")
            return

        self.pipeline_started = True


        # stop timer if still running
        if self.timer_active:
            self.auto_timer.stop()
            self.timer_active = False
            self.releaseKeyboard()

        if not self.image_path or not self.backend:
            self.pipeline_started = False
            return

        LOG.info("[QC UI] User confirmed — starting automatic forensic enhancement")

        # setup enhancement page
        self.enhancement_page.set_backend(self.backend)
        self.enhancement_page.set_image(self.image_path)

        # pass planned steps
        self.enhancement_page.prepare_sections(self.planned_steps)

        # start pipeline
        self.backend.continue_pipeline()

        # switch UI
        self.stacked_widget.setCurrentWidget(self.enhancement_page)


    # ================== Paint Boxes ==================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        offset_y = self.bottom_panel.y()
        offset_x = self.bottom_panel.x()

        for i, box in enumerate(self.check_boxes):
            rect = QRectF(offset_x + box.x(), offset_y + box.y(), box.width(), box.height())
            gradient = QLinearGradient(QPointF(rect.left(), rect.top()), QPointF(rect.right(), rect.bottom()))
            if self.current_status[i]:
                gradient.setColorAt(0, QColor(0, 230, 255, 180))
                gradient.setColorAt(1, QColor(0, 160, 255, 180))

            else:
                gradient.setColorAt(0, QColor(255, 100, 100, 160))
                gradient.setColorAt(1, QColor(255, 0, 0, 160))
            pen = QPen(QBrush(gradient), 2)
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.drawRoundedRect(rect, 12, 12)

        painter.end()

    # ================== Boxes ==================
    def create_check_boxes(self, titles):
        for i in reversed(range(self.bottom_layout.count())):
            widget = self.bottom_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.check_boxes = []

        for idx, title in enumerate(titles):
            label = QLabel(title, self.bottom_panel)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 14px;
                    font-weight: 500;
                }
                QLabel:hover {
                    color: rgb(0,220,255);

            """)
            label.setCursor(Qt.PointingHandCursor)
            label.setFixedSize(180, 180)

            if title.upper() in ["MASK", "POSE"]:
                label.mousePressEvent = lambda e, k=title.lower(): self.on_postqc_clicked(k)
            else:
                label.mousePressEvent = lambda e, k=title.lower(): self.on_metric_clicked(k)


            self.check_boxes.append(label)
            self.bottom_layout.addWidget(label, alignment=Qt.AlignCenter)

    # ================== Button Styles ==================
    def set_button_style(self, button, active=False):
        if active:
            button.setStyleSheet("""
                QPushButton {
                    color: rgb(0,220,255);
                    font-weight: 600;
                    background: transparent;
                    border: 1px solid cyan;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: rgba(0,255,255,50); }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: 1px solid rgba(255,255,255,60);
                    border-radius: 6px;
                }
                QPushButton:hover {
                    color: rgb(0,220,255);
                    border-color: rgb(0,220,255);

                }
            """)
    # ================== Backend Slots ==================

    def on_qc_ready(self, qc_report, intelligence_preview, planned_steps):
        self.planned_steps = planned_steps

        # Store raw data
        self.qc_report = qc_report
        self.intelligence_preview = intelligence_preview
        self.decision_map = self.build_decision_map(qc_report, intelligence_preview)

        self.results = {
            "preqc": qc_report.get("objective", {}),
            "postqc": qc_report
        }


        self.load_results()

        paragraph = self.build_intelligence_paragraph(qc_report, intelligence_preview)


        self.status_label.setText("QC Completed — Review & Continue")
        self.status_label.setStyleSheet("color: cyan; font-size: 22px; font-weight: 600;")

        # Show continue button (reuse enhance button)
        # Show Start button after full QC
        self.start_btn.setText("START")
        self.start_btn.show()
        self.start_auto_timer()

    def set_backend(self, backend: ForensicBackend):
        self.backend = backend
        self.backend.qc_ready.connect(self.on_qc_ready)
        self.backend.status.connect(self.on_backend_status)
        self.backend.error.connect(self.on_backend_error)

    def on_postqc_clicked(self, metric: str):

        if not self.postqc_ready:
            LOG.info("[QC UI] PostQC click blocked — QC not ready")
            return


        metric = metric.lower()
        raw_text = self.postqc_issue_map.get(metric, "Unknown")

        bad_words = ["mask", "bad", "no", "detected", "failed"]
        is_bad = any(w in raw_text.lower() for w in bad_words)

        header = f"{metric.upper()} — ISSUE DETECTED" if is_bad else f"{metric.upper()} — OK"

        if metric == "mask":
            body = (
                "Face covering detected. Facial features may be obstructed."
                if is_bad else
                "No face covering detected. Face is clear."
            )

        elif metric == "pose":
            body = (
                "Head pose is not suitable for forensic recognition."
                if is_bad else
                "Head pose is suitable for forensic recognition."
            )

        else:
            body = raw_text

        text = f"""
    {header}

    ----------------------
    FACE QUALITY FACT
    {body}
    """

        self.desc_label.setText(text.strip())



    def on_backend_status(self, text):
        if text:
            LOG.info(f"[BACKEND] {text}")


        self.status_label.setText(text)

    def build_intelligence_paragraph(self, qc_report: dict, intel: dict) -> str:

        planned = [a.get("name") for a in intel.get("planned_actions", [])]
        risk = intel.get("risk_level", "UNKNOWN")
        confidence = round(intel.get("confidence", 0), 3)
        phase = intel.get("phase", "UNKNOWN")

        obj = qc_report.get("objective", {})

        problems = []

        if obj.get("blur", {}).get("variance", 999) < 50:
            problems.append("blur")

        if obj.get("brightness", {}).get("mean", 999) < 110:
            problems.append("brightness")

        if obj.get("contrast", {}).get("std", 999) < 20:
            problems.append("contrast")

        if max(
            obj.get("resolution", {}).get("width", 0),
            obj.get("resolution", {}).get("height", 0)
        ) < 900:
            problems.append("resolution")

        if obj.get("noise", {}).get("noise", 0) > 15:
            problems.append("noise")

        problems_txt = ", ".join(problems) if problems else "no critical quality issues"

        if planned:
            action_txt = "Planned enhancement actions: " + ", ".join(planned)
        else:
            action_txt = "No automatic enhancement will be applied."

        return (
            f"Quality assessment detected {problems_txt}.\n\n"
            f"{action_txt}\n\n"
            f"Forensic risk level: {risk}\n"
            f"Confidence: {confidence}\n"
            f"Phase: {phase}"
        )

    def build_decision_map(self, qc_report: dict, intelligence: dict):

        decision_map = {
            "blur": "Skipped",
            "brightness": "Skipped",
            "contrast": "Skipped",
            "noise": "Skipped",
            "resolution": "Skipped"
        }

        if not intelligence:
            return decision_map

        decision = intelligence.get("decision", {})
        actions = decision.get("recommended_actions", [])

        for act in actions:

            t = act.get("type", "").lower()

            if t == "deblur":
                decision_map["blur"] = "Needs enhancement"

            elif t == "denoise":
                decision_map["noise"] = "Needs enhancement"

            elif t == "contrast":
                decision_map["contrast"] = "Needs enhancement"

            elif t in ["illumination_correction", "brightness", "relight"]:
                decision_map["brightness"] = "Needs enhancement"

            elif t in ["super_resolution", "face_restore", "gfpgan"]:
                decision_map["resolution"] = "Needs enhancement"

        return decision_map



    def on_metric_clicked(self, key):

        key = key.lower()

        raw_text = self.raw_issue_map.get(key, "Unknown")
        decision_text = self.decision_map.get(key, "No enhancement")

        # ---------- HEADER LOGIC BASED ON INTELLIGENCE ----------
        d = decision_text.lower()

        if "needs" in d:
            header = f"{key.upper()} — ENHANCEMENT PLANNED"

        elif "blocked" in d:
            header = f"{key.upper()} — BLOCKED BY POLICY"

        elif "no enhancement" in d:
            header = f"{key.upper()} — SKIPPED"

        else:
            header = f"{key.upper()} — REVIEW"

        # ---------- DESCRIPTION ----------
        text = f"""
    {header}

    ----------------------
    RAW QUALITY FACT
    Raw facts: {raw_text}

    ----------------------
    INTELLIGENCE DECISION
    System decision: {decision_text}
    """

        self.desc_label.setText(text.strip())






    def on_backend_error(self, msg):
        LOG.info(f"[FORENSIC][ERROR] {msg}")

        self.status_label.setText("Forensic engine error occurred.")
        self.status_label.setStyleSheet("color: red; font-size: 22px; font-weight: 600;")


    def start_auto_timer(self):
        self.auto_seconds = 10
        self.timer_active = True
        self.start_btn.setText(f"{self.auto_seconds}s")
        self.auto_timer.start(1000)
        self.grabKeyboard()   # enable ESC detection


    def _on_timer_tick(self):
        if not self.timer_active:
            return

        self.auto_seconds -= 1

        if self.auto_seconds <= 0:
            self.auto_timer.stop()
            self.timer_active = False
            self.releaseKeyboard()
            self.handle_enhance()
        else:
            self.start_btn.setText(f"Continuing in {self.auto_seconds}s")


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.timer_active:
            self.auto_timer.stop()
            self.timer_active = False
            self.releaseKeyboard()
            self.start_btn.setText("CONTINUE")
            LOG.info("[QC UI] Auto-continue cancelled by user (ESC)")
        else:
            super().keyPressEvent(event)
