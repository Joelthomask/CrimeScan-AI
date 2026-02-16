# gui/frontend/auto_enhancement_page.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QGraphicsDropShadowEffect
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QEvent ,QRectF, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QLinearGradient, QBrush, QPainterPath, QKeyEvent
from PyQt5.QtWidgets import QLabel
from gui.backend.forensic_backend import ForensicBackend
from gui.frontend.loading_bar import LoadingBar

from utils.logger import get_logger
LOG = get_logger()

class ImageBox(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._rollback = False

        self.setFixedSize(260, 360)

        # IMAGE
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setGeometry(12, 12, self.width()-24, self.height()-80)
        self.image_label.setStyleSheet("border-radius:14px;")

        # SIMILARITY LABEL (⬅️ MISSING)
        self.info_label = QLabel("", self)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setGeometry(0, self.height()-60, self.width(), 20)
        self.info_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 13px;
                background: transparent;
            }
        """)

        # ROLLBACK LABEL
        self.rollback_label = QLabel("ROLLBACK", self)
        self.rollback_label.setAlignment(Qt.AlignCenter)
        self.rollback_label.setGeometry(0, self.height()-35, self.width(), 20)
        self.rollback_label.setStyleSheet("""
            QLabel {
                color: red;
                font-weight: bold;
                font-size: 14px;
                background: transparent;
            }
        """)
        self.rollback_label.hide()

    # ---------- Visual State ----------
    def set_rollback(self, state: bool):
        self._rollback = state
        self.rollback_label.setVisible(state)
        self.update()
    # ---------- Compatibility Stub ----------
    def set_info(self, similarity=None):
        if similarity is None:
            self.info_label.setText("")
        else:
            self.info_label.setText(f"Similarity: {similarity:.1f}%")




    # ---------- Image ----------
    def set_image(self, path):
        pix = QPixmap(path)
        if pix.isNull():
            return

        # 🔥 crop-to-fill (no black bars, no stretch)
        scaled = pix.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(scaled)


    # ---------- Custom Paint ----------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(1.5, 1.5, self.width()-3, self.height()-3)

        gradient = QLinearGradient(0, 0, self.width(), self.height())

        if self._rollback:
            gradient.setColorAt(0.0, QColor(255, 60, 60))
            gradient.setColorAt(1.0, QColor(180, 0, 0))
        else:
            gradient.setColorAt(0.0, QColor(0, 230, 255))
            gradient.setColorAt(1.0, QColor(0, 160, 255))


        pen = QPen(QBrush(gradient), 4)   # 🔥 thick border
        painter.setPen(pen)
        painter.setBrush(QColor(20, 20, 20, 220))

        painter.drawRoundedRect(rect, 22, 22)
class SectionBox(QFrame):
    def __init__(self, name, parent=None):
        super().__init__(parent)

        self.name = name
        self.active = False
        self.pix = None

        self.setFixedSize(150, 95)
        self.setStyleSheet("""
        QFrame {
            background-color: rgba(25, 25, 25, 200);
            border-radius: 14px;
            border: 2px solid #444;
        }
        """)

    def set_icon(self, path):
        pix = QPixmap(path)
        if pix.isNull():
            return
        self.pix = pix
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())

        if self.pix:
            scaled = self.pix.scaled(
                rect.size().toSize(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            painter.setClipPath(self._rounded_clip(rect))
            painter.drawPixmap(rect.toRect(), scaled)

        painter.fillRect(rect.toRect(), QColor(0, 0, 0, 35))
        painter.setPen(Qt.white)
        painter.drawText(rect.toRect(), Qt.AlignCenter, self.name)

    def _rounded_clip(self, rect):
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        return path


    def set_active(self, state: bool):
        self.active = state

        if state:
            self.setStyleSheet("""
            QFrame {
                border-radius: 14px;
                border: 3px solid rgb(0,200,255);
                background-color: rgba(30, 40, 40, 150);
            }
            """)
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(55)
            glow.setColor(QColor(0, 200, 255))
            glow.setOffset(0, 0)
            self.setGraphicsEffect(glow)
        else:
            self.setStyleSheet("""
            QFrame {
                background-color: rgba(25, 25, 25, 200);
                border-radius: 14px;
                border: 2px solid #444;
            }
            """)
            self.setGraphicsEffect(None)

# --- Main Page ---
class AutoEnhancementPage(QWidget):
    enhancementDone = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        LOG.info("[AUTO-ENHANCE UI] AutoEnhancementPage initialized.")
        self.backend = None
        # --- BEFORE / AFTER IMAGE BOXES ---
        self.before_box = ImageBox("BEFORE")
        self.after_box = ImageBox("ENHANCED")
        self.section_state = {}
        # format:
        # {
        #   module: {
        #       "before": str,
        #       "after": str,
        #       "before_sim": float | None,
        #       "after_sim": float | None,
        #       "rollback": bool
        #   }
        # }
        self.step_guard_results = {}  
        # format:
        # {
        #   module: {
        #       "rollback": bool,
        #       "before_sim": float | None,
        #       "after_sim": float | None
        #   }
        # }

        # --- Final auto-confirm timer ---
        self.final_timer = QTimer(self)
        self.final_timer.timeout.connect(self._on_final_timer_tick)
        self.final_seconds = 30
        self.final_timer_active = False
        self.results_ready = False
        self.planned_steps = []
        self.current_step_index = 0

        self.input_path = None
        self.output_path = None

        self.active_module = None
        self.target_progress = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._animate_progress)
        self.progress_timer.start(16)

        # === Layout ===
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        # --- TITLE ---
        title_label = QLabel("AUTO FORENSIC ENHANCEMENT")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
        QLabel {
            color: rgb(0, 220, 255);
            font-size: 40px;
            font-weight: bold;
            letter-spacing: 1.2px;
            padding-top: 3px;   /* small gap from window */
        }
        """)

        main_layout.addWidget(title_label)
        main_layout.addSpacing(0.5)
        # --- CYAN DIVIDER ---
        divider = QFrame()
        divider.setFixedHeight(4)
        divider.setStyleSheet("""
        QFrame {
            border: none;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(0,200,255,0),
                stop:0.25 rgba(0,200,255,160),
                stop:0.5 rgba(0,160,255,255),
                stop:0.75 rgba(0,200,255,160),
                stop:1 rgba(0,200,255,0)
            );
            margin-left: 40px;
            margin-right: 40px;
        }
        """)

        main_layout.addWidget(divider)
        main_layout.addSpacing(15)

        # --- SECTION BOXES (visual, always visible) ---
        section_layout = QHBoxLayout()
        section_layout.setAlignment(Qt.AlignCenter)
        section_layout.setSpacing(24)

        self.section_boxes = {}

        section_names = [
            ("deblur", "BLUR"),
            ("brightness", "BRIGHTNESS"),
            ("contrast", "CONTRAST"),
            ("denoise", "NOISE"),
            ("superres", "RESOLUTION"),
            ("pose", "POSE")
        ]

        for key, label in section_names:
            icons = {
                "deblur": "assets/icons/blur.jpeg",
                "brightness": "assets/icons/brightness.jpeg",
                "contrast": "assets/icons/contrast.jpeg",
                "denoise": "assets/icons/noise.jpeg",
                "superres": "assets/icons/resolution.jpeg",
                "pose": "assets/icons/pose.jpeg",
            }

            box = SectionBox(label)
            box.set_icon(icons[key])

            box.mousePressEvent = lambda e, k=key: self.switch_section(k)
            self.section_boxes[key] = box
            section_layout.addWidget(box)


        # gap above sections
        main_layout.addSpacing(1)
        main_layout.addLayout(section_layout)

        # --- LOADING BAR UNDER MODULE BOXES ---
        self.loading_bar = LoadingBar("assets/bar_texture.png")
        self.loading_bar.setFixedHeight(18)
        self.loading_bar.setFixedWidth(600)

        main_layout.addWidget(self.loading_bar, alignment=Qt.AlignCenter)

        main_layout.addSpacing(10)


        # --- IMAGE BOXES (moved near bottom, above buttons) ---
        image_box_layout = QHBoxLayout()
        image_box_layout.setAlignment(Qt.AlignCenter)
        image_box_layout.setSpacing(60)

        image_box_layout.addWidget(self.before_box)
        image_box_layout.addWidget(self.after_box)



        main_layout.addLayout(image_box_layout)

        # Add vertical gap below boxes (before buttons)
        main_layout.addSpacing(20)


        # --- Bottom Buttons ---
        # --- Bottom Action Buttons ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setAlignment(Qt.AlignCenter)
        bottom_layout.setSpacing(40)

        # ---- ROLLBACK BUTTON (visual only) ----
        self.rollback_btn = QPushButton("ROLLBACK")
        self.rollback_btn.setFixedSize(160, 60)
        self.rollback_btn.setEnabled(False)  # visual only
        self.rollback_btn.setStyleSheet("""
        QPushButton {
            color: rgb(0,220,255);
            font-size: 16px;
            font-weight: bold;
            background: transparent;
            border-radius: 14px;
            border: 3px solid rgb(0,200,255);
        }

        QPushButton:hover {
            background: rgba(0,200,255,40);
        }

        QPushButton:pressed {
            background: rgba(0,200,255,70);
        }
        """)

        # ---- CONFIRM BUTTON (always visually active) ----
        self.confirm_btn = QPushButton("CONFIRM")
        self.confirm_btn.setFixedSize(180, 60)
        self.confirm_btn.setStyleSheet("""
        QPushButton {
            color: black;
            font-size: 16px;
            font-weight: bold;
            border-radius: 14px;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 rgb(0,255,255),
                stop:1 rgb(0,180,255)
            );
        }
        QPushButton:hover {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 rgb(0,220,255),
                stop:1 rgb(0,140,255)
            );
        }
        """)

        self.confirm_btn.clicked.connect(self.auto_return)

        bottom_layout.addWidget(self.rollback_btn)
        bottom_layout.addWidget(self.confirm_btn)

        # --- Wrap buttons so they sit JUST ABOVE the warning banner ---
        buttons_wrapper = QFrame()
        buttons_wrapper_layout = QVBoxLayout(buttons_wrapper)
        buttons_wrapper_layout.setContentsMargins(0, 0, 0, 8)  # 👈 gap above banner
        buttons_wrapper_layout.addLayout(bottom_layout)

        main_layout.addWidget(buttons_wrapper)

        # --- ROLLBACK WARNING BANNER ---
        warning_bar = QFrame()
        warning_bar.setFixedHeight(42)
        warning_bar.setStyleSheet("""
        QFrame {
            background-color: rgba(10, 10, 10, 200);
        }
        """)

        warning_layout = QHBoxLayout(warning_bar)
        warning_layout.setContentsMargins(20, 0, 20, 0)

        warning_label = QLabel(
            "WARNING: Rollback will restore the original image and cancel all enhancements performed."
        )
        warning_label.setAlignment(Qt.AlignCenter)
        warning_label.setStyleSheet("""
        QLabel {
            color: #b0cfd4;
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 0.4px;
        }
        """)

        warning_layout.addWidget(warning_label)
        main_layout.addWidget(warning_bar)

        # Enable ESC key events
        self.setFocusPolicy(Qt.StrongFocus)


    def set_backend(self, backend):
        self.backend = backend

        # 🔥 HARD disconnect to prevent duplicates
        try:
            self.backend.step_update.disconnect(self.on_step_update)
        except:
            pass
        try:
            self.backend.finished.disconnect(self.on_finished)
        except:
            pass
        try:
            self.backend.status.disconnect(self.update_status)
        except:
            pass

        # ✅ connect only once
        self.backend.step_update.connect(self.on_step_update)
        self.backend.finished.connect(self.on_finished)
        self.backend.status.connect(self.update_status)
        self.backend.rollback_detected.connect(self.on_rollback_detected)
    def on_step_update(self, module, image_path):

        before_path = self.input_path
        if module in self.section_state:
            before_path = self.section_state[module]["before"]

        # ---------- STEP-SCOPED GUARD RESULT ----------
        guard = self.step_guard_results.get(module, {})
        rollback = guard.get("rollback", False)
        before_sim = guard.get("before_sim")
        after_sim = guard.get("after_sim")

        # ---------- FREEZE RESULT ----------
        self.section_state[module] = {
            "before": before_path,
            "after": image_path,
            "before_sim": before_sim,
            "after_sim": after_sim,
            "rollback": rollback
        }

        # ---------- ACTIVATE ONLY THIS MODULE ----------
        self.active_module = module
        for key, box in self.section_boxes.items():
            box.set_active(key == module)

        # ---------- UPDATE PREVIEWS ----------
        self.before_box.set_image(before_path)
        self.after_box.set_image(image_path)

        if rollback:
            self.after_box.set_rollback(True)
            self.before_box.set_info(before_sim)
            self.after_box.set_info(after_sim)
            self.rollback_btn.setEnabled(True)
        else:
            self.after_box.set_rollback(False)
            self.before_box.set_info()
            self.after_box.set_info()
        # ---- UPDATE LOADING BAR ----
        self.completed_steps += 1

        if self.total_steps > 0:
            progress = int(
                self.completed_steps / self.total_steps * 100
            )
            self.target_progress = progress




    def switch_section(self, module):
        # 🔒 forbid switching entirely after pipeline finishes
        if self.results_ready:
            return

    def on_finished(self, final_path):
        self.results_ready = True
        self.output_path = final_path

        # 🔒 force last section active
        if self.section_order:
            last = self.section_order[-1]
            self.active_module = last
            for key, box in self.section_boxes.items():
                box.set_active(key == last)
        LOG.info("[AUTO-ENHANCE UI] Pipeline fully completed")

        self.target_progress = 100

        self.loading_bar.finish()

        self.start_final_timer()




    # ---------- Standard Methods ----------
    def set_image(self, image_path: str):
        self.input_path = image_path
        self.output_path = image_path


        self.active_module = None
        self.before_box.set_image(image_path)
        self.after_box.set_image(image_path)

        # guard OFF → no info
        self.before_box.set_info()
        self.after_box.set_info()




    def update_status(self, text: str):
        LOG.info(f"[BACKEND] {text}")


        if "rejected → rollback" in text.lower():
            # show rollback banner
            self.rollback_banner.show()

            # remove rejected enhanced image
            self.after_box.set_image(self.before_box.image_label.pixmap())
            self.after_box.set_rollback(True)
    def auto_return(self):
        # 🔒 If user already left this page, do nothing
        if not self.isVisible():
            LOG.info("[AUTO-ENHANCE UI] Page hidden, skipping auto-return.")
            return

        if self.final_timer.isActive():
            self.final_timer.stop()

        self.final_timer_active = False

        if not self.results_ready:
            return

        LOG.info("[AUTO-ENHANCE UI] Returning to CrimeScan")

        # Emit result to CrimeScan
        self.enhancementDone.emit(self.output_path)

    def hideEvent(self, event):
        # Stop review timer when user leaves page
        if self.final_timer_active:
            self.final_timer.stop()
            self.final_timer_active = False
            LOG.info("[AUTO-ENHANCE UI] Timer stopped (page hidden).")

        super().hideEvent(event)
    def manual_return(self):

        LOG.info("[AUTO-ENHANCE UI] User aborted enhancement. Stopping engine...")

        # ---- stop final review timer ----
        if self.final_timer_active:
            self.final_timer.stop()
            self.final_timer_active = False
            self.releaseKeyboard()

        # ---- HARD STOP forensic backend ----
        if self.backend:
            try:
                self.backend.stop()
            except Exception as e:
                LOG.info("[AUTO-ENHANCE UI][WARN] Failed to stop backend:", e)

        # ---- DO NOT return enhanced image ----
        # returning None means "cancelled"
        # return original image so CrimeScan can continue normally
        self.enhancementDone.emit(self.output_path)



    def prepare_sections(self, planned_steps):
        self.section_order = planned_steps[:]
        self.current_step_index = 0
        self.results_ready = False

        self.total_steps = len(planned_steps)
        self.completed_steps = 0
        self.loading_bar.progress = 0


        for box in self.section_boxes.values():
            box.set_active(False)

        if self.section_order:
            self.active_module = self.section_order[0]
            self.section_boxes[self.active_module].set_active(True)

            # 🔒 force identical previews
            self.before_box.set_image(self.input_path)
            self.after_box.set_image(self.input_path)
            self.before_box.set_info()
            self.after_box.set_info()
            self.after_box.set_rollback(False)





    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape and self.final_timer_active:
            # ESC = cancel auto-confirm, allow review
            self.cancel_final_timer()
            LOG.info("[AUTO-ENHANCE UI] Auto-confirm timer cancelled. Review mode enabled.")
        else:
            super().keyPressEvent(event)


    def start_final_timer(self):
        self.final_seconds = 30
        self.final_timer_active = True

        self.confirm_btn.setEnabled(True)
        self.confirm_btn.setText(f"CONFIRM ({self.final_seconds}s)")

        self.final_timer.start(1000)
    def _animate_progress(self):
        current = self.loading_bar.progress
        target = self.target_progress

        if current < target:
            self.loading_bar.progress += min(0.6, target - current)
            self.loading_bar.update()

    def _on_final_timer_tick(self):
        if not self.final_timer_active:
            return

        self.final_seconds -= 1

        if self.final_seconds <= 0:
            self.final_timer.stop()
            self.final_timer_active = False
            self.confirm_btn.setText("CONFIRM")
            self.auto_return()
        else:
            self.confirm_btn.setText(f"CONFIRM ({self.final_seconds}s)")


    def cancel_final_timer(self):
        if self.final_timer_active:
            self.final_timer.stop()
            self.final_timer_active = False

            # Restore CONFIRM button to normal state
            self.confirm_btn.setText("CONFIRM")

            # 🔒 Important: do NOT auto-return
            # User is now in manual review mode
    def on_rollback_detected(self, module, data):
        # cache rollback for this module
        self.step_guard_results[module] = {
            "rollback": True,
            "before_sim": data.get("before_similarity"),
            "after_sim": data.get("after_similarity")
        }

        # show rollback only if this module is currently active
        if module != self.active_module:
            return

        self.rollback_btn.setEnabled(True)
        self.after_box.set_rollback(True)
        self.before_box.set_info(data.get("before_similarity"))
        self.after_box.set_info(data.get("after_similarity"))
