import os, math, random, shutil, cv2

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import (
    QFont, QPixmap, QLinearGradient, QColor,
    QPainter, QPen, QPainterPath 
)
from PyQt5.QtCore import (
    Qt, QPoint, QRectF,
    QPropertyAnimation, QParallelAnimationGroup,
    QEasingCurve, QTimer, pyqtProperty ,QSize
)
from PyQt5.QtWidgets import QGraphicsOpacityEffect
from PyQt5.QtWidgets import QCheckBox

from ..backend.image_crime_scan_backend import ImageCrimeScanBackend
from .quality_checker_page import QualityCheckerPage
from database.sqlite.criminals_db import DatabaseHandler, create_case
from auto_enhancer.adaptive_learner.learner_manager import LearnerManager

from utils.logger import get_logger
LOG = get_logger()

from utils.temp_manager import get_temp_subpath, get_session
from gui.backend.forensic_backend import ForensicBackend


class GlowingDivider(QWidget):
    def __init__(self, parent=None, color=QColor(0, 229, 255)):
        super().__init__(parent)
        self._progress = 0.0
        self.color = color

        self.setFixedHeight(18)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.anim = QPropertyAnimation(self, b"progress", self)
        self.anim.setDuration(1400)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    def start(self):
        self._progress = 0.0
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        self.show()

    def reset(self):
        self.anim.stop()
        self._progress = 0.0
        self.hide()

    def getProgress(self):
        return self._progress

    def setProgress(self, value):
        self._progress = value
        self.update()

    progress = pyqtProperty(float, getProgress, setProgress)

    def paintEvent(self, event):
        if self._progress <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        center_x = w / 2
        y = h / 2

        half_len = (w * 0.45) * self._progress

        steps = 60
        for i in range(steps):
            t = i / steps
            x = center_x - half_len + (2 * half_len * t)

            fade = math.sin(math.pi * t)

            # ===== ULTRA SOFT HALO (very wide, very subtle) =====
            halo = QColor(self.color)
            halo.setAlpha(int(40 * fade))
            painter.setPen(QPen(halo, 18, Qt.SolidLine, Qt.RoundCap))
            painter.drawPoint(QPoint(int(x), int(y)))

            # ===== OUTER GLOW =====
            outer = QColor(self.color)
            outer.setAlpha(int(90 * fade))
            painter.setPen(QPen(outer, 12, Qt.SolidLine, Qt.RoundCap))
            painter.drawPoint(QPoint(int(x), int(y)))

            # ===== MID GLOW =====
            mid = QColor(self.color)
            mid.setAlpha(int(170 * fade))
            painter.setPen(QPen(mid, 6, Qt.SolidLine, Qt.RoundCap))
            painter.drawPoint(QPoint(int(x), int(y)))

            # ===== INNER CORE (sharp) =====
            core = QColor(self.color)
            core.setAlpha(int(240 * fade))
            painter.setPen(QPen(core, 2.5, Qt.SolidLine, Qt.RoundCap))
            painter.drawPoint(QPoint(int(x), int(y)))


class AnimatedBorder(QWidget):
    def __init__(self, parent, radius=14, color="#329FCB", start_delay=400):
        super().__init__(parent)
        self.radius = radius
        self.color = QColor(color)

        self._phase = 0.0
        self._glow_phase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)

        # ⏳ Auto-start only if delay is provided
        if start_delay is not None:
            QTimer.singleShot(start_delay, self.start)

        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.resize(parent.size())
        parent.installEventFilter(self)

    def start(self):
        if not self.timer.isActive():
            self.timer.start(30)

    def stop(self):
        self.timer.stop()
        self.update()


    def _start_animation(self):
        self.timer.start(30)


    def eventFilter(self, obj, event):
        if event.type() == event.Resize:
            self.resize(obj.size())
        return False

    def _animate(self):
        self._phase += 0.0012          # 🔵 slow circular motion
        self._glow_phase += 0.05       # 🔵 breathing glow
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 🔵 perfectly aligned INSIDE border
        rect = QRectF(
            3.5, 3.5,
            self.width() - 7,
            self.height() - 7
        )

        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        glow = 0.5 + 0.5 * math.sin(self._glow_phase)
        base_alpha = int(190 + 65 * glow)   # 🔥 strong glow

        segment_length = 0.18   # 🔥 longer segments
        step = 0.003            # smooth sampling

        for i in range(4):
            start = (self._phase + i * 0.25) % 1.0
            self._draw_segment(
                painter,
                path,
                start,
                segment_length,
                step,
                base_alpha
            )

    def _draw_segment(self, painter, path, start, length, step, alpha):
        points = []
        t = 0.0

        while t <= length:
            pct = (start + t) % 1.0
            points.append(path.pointAtPercent(pct))
            t += step

        count = len(points)
        if count < 2:
            return

        for i in range(count - 1):
            # 🔵 feathered ends (smooth fade-in/out)
            fade = math.sin(math.pi * i / (count - 1))

            # 🌫 OUTER GLOW
            outer = QColor(self.color)
            outer.setAlpha(int(alpha * fade * 0.35))
            outer_pen = QPen(outer, 9)
            outer_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(outer_pen)
            painter.drawLine(points[i], points[i + 1])

            # 🔥 INNER CORE
            inner = QColor(self.color)
            inner.setAlpha(int(alpha * fade))
            inner_pen = QPen(inner, 4)
            inner_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(inner_pen)
            painter.drawLine(points[i], points[i + 1])




class GlassOverlay(QWidget):
    """
    Premium glass overlay:
    - Subtle light gradient
    - Inner highlight edge
    - Micro grain texture
    """

    def __init__(self, parent, radius=14):
        super().__init__(parent)
        self.radius = radius

        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.resize(parent.size())
        parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.Resize:
            self.resize(obj.size())
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # ============================
        # 1️⃣ GLASS LIGHT GRADIENT
        # ============================
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0.0, QColor(255, 255, 255, 18))
        gradient.setColorAt(0.4, QColor(255, 255, 255, 8))
        gradient.setColorAt(1.0, QColor(255, 255, 255, 14))

        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, self.radius, self.radius)

        # ============================
        # 2️⃣ INNER EDGE HIGHLIGHT
        # ============================
        pen = QPen(QColor(255, 255, 255, 32), 1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(
            rect.adjusted(1, 1, -1, -1),
            self.radius - 1,
            self.radius - 1
        )

        # ============================
        # 3️⃣ MICRO GRAIN TEXTURE
        # ============================
        painter.setOpacity(0.035)
        for _ in range(350):
            x = random.randint(0, rect.width() - 1)
            y = random.randint(0, rect.height() - 1)
            painter.drawPoint(x, y)
        painter.setOpacity(1.0)




class ImageCrimeScanPage(QWidget):
    def __init__(self, stacked_widget, main_menu, device="cpu"):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.main_menu = main_menu
        self.device = device

        self._recognition_done = False

        # --- Backend (DB path centralized, NOT passed) ---
        self.backend = ImageCrimeScanBackend(device=device)
        # --- Database (read-only access for UI) ---
        self.db = DatabaseHandler()

        self.image_path = None

        # === Unified forensic backend (QC + enhancement brain) ===
        self.forensic_backend = ForensicBackend(device=device, mode="forensic")
        # Adaptive learner controller
        self.learner = LearnerManager()

        self.recognition_guided_mode = False



        # === Root layout ===
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(30, 20, 30, 30)
        root_layout.setSpacing(12)

        # ===== PAGE TITLE =====
        page_title = QLabel("CRIMESCAN")
        page_title.setAlignment(Qt.AlignCenter)
        page_title.setFont(QFont("Segoe UI", 45, QFont.Bold))
        page_title.setStyleSheet("""
            QLabel {
                color: rgb(0,220,255);
                letter-spacing: 3px;
                background: transparent;
            }
        """)

        # ===== DIVIDER =====
        page_divider = QFrame()
        page_divider.setFixedHeight(2)
        page_divider.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0,0,0,0),
                    stop:0.5 rgba(0,220,255,220),
                    stop:1 rgba(0,0,0,0)
                );
            }
        """)
        root_layout.addSpacing(10)          # space above title
        root_layout.addWidget(page_title)

        root_layout.addSpacing(6)           # space between title & divider
        root_layout.addWidget(page_divider)

        root_layout.addSpacing(14)          # space after divider



        # === Main horizontal layout (split halves) ===
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)

        # ---------------- LEFT HALF ----------------
        upload_card = QFrame()
        upload_card.setFixedSize(800, 600)
        upload_card.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 120);
                border: 2px solid #329FCB;
                border-radius: 14px;
            }

            QLabel#uploadTitle {
                color: white;
            }
        """)
        self.glass = GlassOverlay(upload_card)
        self.glass.raise_()

        # === Animated Border ===
        self.upload_border = AnimatedBorder(
            upload_card,
            radius=14,
            start_delay=400   # ✅ starts 400 ms after page opens
        )
        self.upload_border.raise_()


        upload_layout = QVBoxLayout(upload_card)
        upload_layout.setContentsMargins(20, 20, 20, 20)
        upload_layout.setSpacing(0)

        upload_shadow = QGraphicsDropShadowEffect()
        upload_shadow.setOffset(0, 0)
        upload_shadow.setBlurRadius(18)
        upload_shadow.setColor(QColor(50, 159, 203, 90))
        upload_card.setGraphicsEffect(upload_shadow)

        # ================= SEARCH ICON =================
        search_icon = QLabel()
        search_icon.setAlignment(Qt.AlignCenter)
        search_icon.setStyleSheet("border: none; background: transparent;")

        icon_path = os.path.join("assets", "search.png")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            search_icon.setPixmap(pixmap)

        # Glow for icon
        icon_glow = QGraphicsDropShadowEffect()
        icon_glow.setOffset(0, 0)
        icon_glow.setBlurRadius(28)
        icon_glow.setColor(QColor(50, 159, 203, 180))
        search_icon.setGraphicsEffect(icon_glow)

        # ================= TITLE =================
        upload_title = QLabel("UPLOAD CRIME SCENE IMAGE")
        upload_title.setObjectName("uploadTitle")
        upload_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        upload_title.setAlignment(Qt.AlignCenter)
        upload_title.setStyleSheet("""
            QLabel {
                border: none;
                background: transparent;
                color: white;
                letter-spacing: 1px;
            }
        """)


        # ================= UPLOAD BUTTON =================
        self.upload_btn = QPushButton("Browse Files")
        self.upload_btn.setFixedSize(200, 48)
        self.upload_btn.setFont(QFont("Segoe UI", 12, QFont.Medium))
        self.upload_btn.setCursor(Qt.PointingHandCursor)

        self.upload_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: rgba(255, 255, 255, 18);
                border: 1.5px solid rgba(255, 255, 255, 60);
                border-radius: 8px;
                padding: 10px 18px;
                letter-spacing: 0.5px;
            }

            QPushButton:hover {
                color: #00E5FF;
                background-color: rgba(0, 229, 255, 25);
                border-color: #00E5FF;
            }

            QPushButton:pressed {
                color: #00E5FF;
                background-color: rgba(0, 229, 255, 45);
                border-color: #00E5FF;
            }
        """)
        self.upload_btn.clicked.connect(self.upload_image)

        # ================= PREMIUM GLOW (MATCHES BACK BUTTON) =================
        btn_glow = QGraphicsDropShadowEffect()
        btn_glow.setOffset(0, 0)
        btn_glow.setBlurRadius(18)
        btn_glow.setColor(QColor(0, 229, 255, 160))  # #00E5FF
        self.upload_btn.setGraphicsEffect(btn_glow)


        button_box = QFrame()
        button_box.setFixedSize(290, 95)
        button_box.setStyleSheet("""
            QFrame {
                border: 2px dashed rgba(0, 229, 255, 160);
                border-radius: 10px;
                background: transparent;
            }
        """)

        button_box_layout = QVBoxLayout(button_box)
        button_box_layout.setContentsMargins(10, 10, 10, 10)
        button_box_layout.setAlignment(Qt.AlignCenter)

        button_box_layout.addWidget(self.upload_btn)
        upload_layout.addWidget(button_box, alignment=Qt.AlignCenter)



        # ================= CENTER EVERYTHING =================
        upload_layout.addStretch(1)
        upload_layout.addWidget(search_icon, alignment=Qt.AlignCenter)
        upload_layout.addSpacing(22)
        upload_layout.addWidget(upload_title, alignment=Qt.AlignCenter)
        upload_layout.addSpacing(45)
        upload_layout.addWidget(button_box, alignment=Qt.AlignCenter)
        upload_layout.addStretch(1)

        # ================= LEFT HALF WRAPPER =================
        left_half = QVBoxLayout()
        left_half.addStretch(1)
        h_left = QHBoxLayout()
        h_left.addStretch(1)
        h_left.addWidget(upload_card)
        h_left.addStretch(1)
        left_half.addLayout(h_left)
        left_half.addStretch(1)


        # ---------------- RIGHT HALF ----------------
        result_card = QFrame()
        result_card.setFixedSize(800, 600)
        result_card.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 120);
                border: 2px solid #329FCB;
                border-radius: 14px;
            }
        """)

        # ===== Glass Texture Overlay =====
        self.result_glass = GlassOverlay(result_card, radius=14)
        self.result_glass.raise_()

        # ===== Animated Border =====
        self.result_border = AnimatedBorder(
            result_card,
            radius=14,
            start_delay=None
        )
        self.result_border.raise_()
        self.result_border.stop()

        # ===== Soft Ambient Glow =====
        result_shadow = QGraphicsDropShadowEffect()
        result_shadow.setOffset(0, 0)
        result_shadow.setBlurRadius(18)
        result_shadow.setColor(QColor(50, 159, 203, 90))
        result_card.setGraphicsEffect(result_shadow)

        # ===== Result Layout =====
        self.result_layout = QVBoxLayout(result_card)
        self.result_layout.setContentsMargins(24, 26, 24, 24)  # ⬅ more top space
        self.result_layout.setSpacing(12)
        self.result_layout.setAlignment(Qt.AlignTop)

        # ================= STATUS TEXT =================
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        self.status_label.setFont(QFont("Segoe UI", 26, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setTextFormat(Qt.RichText)
        self.status_label.setVisible(False)
        self.status_label.setFixedHeight(40)

        # ===== Glowing Divider =====
        self.status_divider = GlowingDivider(result_card)
        self.status_divider.hide()

        # ----- Status container (top-center) -----
        status_container = QWidget(result_card)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addStretch(1)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch(1)

        self.result_layout.addWidget(status_container, alignment=Qt.AlignTop)
        self.result_layout.addSpacing(10)                     # gap to divider
        self.result_layout.addWidget(self.status_divider)
        self.result_layout.addSpacing(22)                     # gap to preview

        # ================= PREVIEW BOX (FIXED POSITION, NO ANIMATION) =================
        self._preview_box = QFrame(result_card)
        self._preview_box.setFixedSize(240, 320)

        # 🔒 Hard-locked position (never moves)
        PREVIEW_LEFT_MARGIN = 48   # increase left gap
        PREVIEW_TOP = 170

        self._preview_box.move(PREVIEW_LEFT_MARGIN, PREVIEW_TOP)


        self._preview_box.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 90);
                border: 2px solid #329FCB;
                border-radius: 12px;
            }
        """)

        # Start hidden – shown only after divider animation
        self._preview_box.hide()

        # ===== Preview Image =====
        self.result_image = QLabel(self._preview_box)
        self.result_image.setAlignment(Qt.AlignCenter)
        self.result_image.setFixedSize(204, 284)
        self.result_image.setScaledContents(True)
        self.result_image.setStyleSheet("border: none; background: transparent;")

        # ---- Layout INSIDE preview box ONLY ----
        preview_layout = QVBoxLayout(self._preview_box)
        preview_layout.setContentsMargins(18, 18, 18, 18)
        preview_layout.setSpacing(0)
        preview_layout.addWidget(self.result_image)



        # ================= DETAILS BOX (RIGHT OF PREVIEW) =================
        DETAILS_LEFT_GAP = 24

        details_x = PREVIEW_LEFT_MARGIN + 240 + DETAILS_LEFT_GAP
        details_y = PREVIEW_TOP

        self.details_box = QFrame(result_card)
        self.details_box.setFixedSize(420, 320)
        self.details_box.move(details_x, details_y)

        self.details_box.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 70);
                border: 1.5px solid rgba(50, 159, 203, 140);
                border-radius: 10px;
            }
        """)

        self.details_box.hide()

        # ===== Details Text =====
        self.details_label = QLabel(self.details_box)
        self.details_label.setWordWrap(True)
        self.details_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.details_label.setFont(QFont("Segoe UI", 12))
        self.details_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 220);
                line-height: 1.5;
                background: transparent;
                border: none;
            }
        """)

        details_layout = QVBoxLayout(self.details_box)
        details_layout.setContentsMargins(16, 14, 16, 14)
        details_layout.addWidget(self.details_label)



        # ===== Right Half Wrapper =====
        right_half = QVBoxLayout()
        right_half.addStretch(1)
        h_right = QHBoxLayout()
        h_right.addStretch(1)
        h_right.addWidget(result_card)
        h_right.addStretch(1)
        right_half.addLayout(h_right)
        right_half.addStretch(1)

        main_layout.addLayout(left_half, 1)
        main_layout.addLayout(right_half, 1)
        ADAPTIVE_STYLE = """
        QCheckBox {
            color: rgba(220,220,220,230);
            spacing: 12px;
        }

        QCheckBox::indicator {
            width: 46px;
            height: 24px;
            border-radius: 12px;
            background: rgba(255,255,255,30);
            border: 1.5px solid rgba(255,255,255,60);
        }

        QCheckBox::indicator:unchecked {
            background: rgba(255,255,255,25);
        }

        QCheckBox::indicator:checked {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #00E5FF,
                stop:1 #329FCB
            );
            border: 1.5px solid #00E5FF;
        }

        QCheckBox::indicator:checked:hover {
            background-color: #00E5FF;
        }
        """        
        # ================= FORENSIC GUARD TOGGLE =================
        self.guard_toggle = QCheckBox("Forensic Safety Guard")
        self.guard_toggle.setCursor(Qt.PointingHandCursor)
        self.guard_toggle.setChecked(True)   # default ON
        self.guard_toggle.setFont(QFont("Segoe UI", 11, QFont.Medium))

        self.guard_toggle.setStyleSheet(ADAPTIVE_STYLE)

        guard_glow = QGraphicsDropShadowEffect()
        guard_glow.setOffset(0, 0)
        guard_glow.setBlurRadius(18)
        guard_glow.setColor(QColor(0, 229, 255, 140))
        self.guard_toggle.setGraphicsEffect(guard_glow)

        self.guard_toggle.stateChanged.connect(self.on_guard_mode_changed)

        # ================= ADAPTIVE LEARNING TOGGLE =================
        self.adaptive_toggle = QCheckBox("Adaptive Learner Mode")
        self.adaptive_toggle.setCursor(Qt.PointingHandCursor)
        self.adaptive_toggle.setChecked(False)
        self.adaptive_toggle.setFont(QFont("Segoe UI", 11, QFont.Medium))



        self.adaptive_toggle.setStyleSheet(ADAPTIVE_STYLE)

        adaptive_glow = QGraphicsDropShadowEffect()
        adaptive_glow.setOffset(0, 0)
        adaptive_glow.setBlurRadius(18)
        adaptive_glow.setColor(QColor(0, 229, 255, 140))
        self.adaptive_toggle.setGraphicsEffect(adaptive_glow)

        self.adaptive_toggle.stateChanged.connect(self.on_adaptive_mode_changed)

        # ---------------- BOTTOM BAR ----------------
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 10)

        self.back_btn = QPushButton("BACK")
        self.back_btn.setFixedSize(150, 50)
        self.back_btn.setFont(QFont("Segoe UI", 12, QFont.Medium))
        self.back_btn.setCursor(Qt.PointingHandCursor)

        self.back_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: rgba(255, 255, 255, 18);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #00E5FF;
                background-color: rgba(0, 229, 255, 25);
                border-color: #00E5FF;
            }
            QPushButton:pressed {
                color: #00E5FF;
                background-color: rgba(0, 229, 255, 45);
                border-color: #00E5FF;
            }
        """)

        self.back_btn.clicked.connect(self.go_back)

        bottom_bar.addStretch(1)
        bottom_bar.addWidget(self.back_btn)
        bottom_bar.addStretch(1)
        toggle_bar = QHBoxLayout()
        toggle_bar.setContentsMargins(0, 0, 0, 6)
        toggle_bar.setSpacing(14)

        toggle_bar.addStretch(1)
        toggle_bar.addWidget(self.guard_toggle)

        # separator
        sep = QLabel("|")
        sep.setStyleSheet("color: rgba(255,255,255,120); font-size:18px;")
        toggle_bar.addWidget(sep)

        toggle_bar.addWidget(self.adaptive_toggle)
        toggle_bar.addStretch(1)



        root_layout.addLayout(main_layout, 1)
        root_layout.addLayout(toggle_bar, 0)
        root_layout.addLayout(bottom_bar, 0)


    def start_typing_details(self, text, interval=18):
        self._typing_text = text
        self._typing_index = 0
        self.details_label.clear()

        if hasattr(self, "_typing_timer"):
            self._typing_timer.stop()

        self._typing_timer = QTimer(self)
        self._typing_timer.timeout.connect(self._type_next_char)
        self._typing_timer.start(interval)
    def _type_next_char(self):
        if self._typing_index >= len(self._typing_text):
            self._typing_timer.stop()
            return

        self.details_label.setText(
            self.details_label.text() + self._typing_text[self._typing_index]
        )
        self._typing_index += 1


    def set_status_text(self, status):
        BLUE = "#00E5FF"
        RED  = "#FF4D4D"

        if status == "match":
            text = f"""
            <span style="color:{BLUE}; letter-spacing:1.2px;">MATCH</span>
            <span style="color:{RED}; letter-spacing:1.2px;"> FOUND!</span>
            """
            self.result_border.start()

        elif status == "no_match":
            text = f"""
            <span style="color:{BLUE}; letter-spacing:1.2px;">NO</span>
            <span style="color:{RED}; letter-spacing:1.2px;"> MATCH!</span>
            """
            self.result_border.start()

        elif status == "no_face":
            text = f"""
            <span style="color:{RED}; letter-spacing:1.2px;">NO FACE!</span>
            """
            self.result_border.stop()

        else:
            return

        self.status_label.setText(text)
        self.status_label.setVisible(True)

        self.status_divider.start()
    def reset_result_state(self):
        self.status_label.clear()
        self.status_label.setVisible(False)

        self.status_divider.reset()
        self.result_border.stop()

        self._preview_box.hide()
        self.details_box.hide()

        if hasattr(self, "_typing_timer"):
            self._typing_timer.stop()





    # --- Upload logic ---
    def upload_image(self):
        self.reset_result_state()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Crime Image", "", "Images (*.jpg *.jpeg *.png)"
        )
        if not file_path:
            return

        LOG.info(f"[CRIMESCAN][UI] User uploaded image: {file_path}")


        temp_input_dir = get_temp_subpath("input")
        if not temp_input_dir:
            return

        try:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(temp_input_dir, filename)
            shutil.copy2(file_path, dest_path)
            self.image_path = dest_path

            # ===============================
            # Create forensic case in DB
            # ===============================
            case_id, image_id = create_case(
                self.db.conn,
                self.image_path
            )

            LOG.info(f"[CASE] Started {case_id} | Image={image_id}")

            img = cv2.imread(dest_path)
            if img is not None:
                h, w = img.shape[:2]
                if max(w, h) >= 2560:
                    scale = 1920 / max(w, h)
                    resized = cv2.resize(
                        img,
                        (int(w * scale), int(h * scale)),
                        cv2.INTER_AREA
                    )
                    cv2.imwrite(dest_path, resized)

        except Exception as e:
            LOG.info(f"[ERROR][CRIMESCAN] Copy failed: {e}")


            return
        qc_page = QualityCheckerPage(
            stacked_widget=self.stacked_widget,
            crime_scan_page=self,
            main_menu=self.main_menu,
            image_path=self.image_path
        )

        # inject unified forensic backend properly
        qc_page.set_backend(self.forensic_backend)

        # listen for enhancement page final return
        qc_page.enhancement_page.enhancementDone.connect(self.on_forensic_finished)

        self.stacked_widget.addWidget(qc_page)
        self.stacked_widget.setCurrentWidget(qc_page)

        self.forensic_backend.stop()
        self.forensic_backend.start_case(self.image_path)


 


    def _fetch_criminal_details(self, name):
        try:
            row = self.db.get_criminal_by_name(name)
            if not row:
                return None

            criminal_id = row[0]
            criminal = self.db.fetch_criminal_by_id(criminal_id)
            return criminal

        except Exception as e:
            LOG.info(f"[ERROR][CRIMESCAN][DB] {e}")


            return None

    def load_results_from_qc(self, results):
        final_image = results.get("image_path")
        detections = results.get("detections", [])

        if not final_image or not os.path.exists(final_image):
            return

        if not detections:
            self._show_result_preview(final_image, status="no_face")
            return

        best_name = None
        best_similarity = None

        for det in detections:
            matches = det.get("matches", [])
            if matches:
                best_name = matches[0][0]
                best_similarity = matches[0][1]
                break

        if best_name:
            details = self._fetch_criminal_details(best_name)
            self._show_result_preview(
                final_image,
                status="match",
                details=details,
                similarity=best_similarity
            )
        else:
            self._show_result_preview(final_image, status="no_match")
    def _show_result_preview(self, image_path, status, details=None, similarity=None):
        self.reset_result_state()
        self.set_status_text(status)

        pix = QPixmap(image_path)
        if not pix.isNull():
            self.result_image.setPixmap(pix)

        def reveal():
            self._preview_box.show()

            if details:
                text = (
                    f"Name: {details.get('name', 'N/A')}\n"
                    f"Age: {details.get('age', 'N/A')}\n"
                    f"Gender: {details.get('gender', 'N/A')}\n"
                    f"Crime: {details.get('crime', 'N/A')}\n"
                    f"Location: {details.get('location', 'N/A')}\n"
                )

                if similarity is not None:
                    text += f"\nMatch Confidence: {similarity:.2f}%"

                self.details_box.show()
                self.start_typing_details(text)

        QTimer.singleShot(
            self.status_divider.anim.duration(),
            reveal
        )

    # ==================================================
    # DIRECT recognition trigger (used when QC/enhance aborted)
    # ==================================================
    def start_recognition(self, image_path):

        # 🔒 PREVENT DUPLICATES
        if self._recognition_done:
            return

        LOG.info("[CRIMESCAN] Starting recognition on original image.")

        if not image_path or not os.path.exists(image_path):
            LOG.info("[CRIMESCAN][WARN] Invalid image path.")
            return

        self._recognition_done = True

        self.image_path = image_path

        results = self.backend.process_image(image_path)

        if not results:
            LOG.info("[CRIMESCAN] No results from recognition.")
            return

        self.load_results_from_qc(results)


    def on_forensic_finished(self, final_image_path: str):

        # reset duplicate guard
        self._recognition_done = False

        if not final_image_path:
            LOG.info("[CRIMESCAN] Forensic pipeline cancelled by user.")
            self.stacked_widget.setCurrentWidget(self)
            return

        LOG.info("[CRIMESCAN] Forensic system finished. Running recognition.")

        # Send case logs to learner
        session = get_session()
        log_path = session.get("log_path")

        print("[DEBUG] Sending case to learner:", log_path)

        if log_path:
            self.learner.process_case(log_path)
        else:
            print("[DEBUG] No log path found in session")

        # run recognition
        self.start_recognition(final_image_path)
        self.stacked_widget.setCurrentWidget(self)






    def go_back(self):
        self.reset_result_state()
        self.stacked_widget.setCurrentWidget(self.main_menu)


    def on_adaptive_mode_changed(self, state):
        enabled = state == Qt.Checked
        LOG.info(f"[CRIMESCAN][UI] Adaptive learner → {enabled}")

        # adaptive is not allowed without guard
        if enabled and not self.guard_toggle.isChecked():
            LOG.info("[CRIMESCAN][UI] Guard forced ON (adaptive requires safety)")
            self.guard_toggle.setChecked(True)

        # Toggle learner
        self.learner.set_enabled(enabled)

        if hasattr(self.forensic_backend, "set_adaptive_learning"):
            self.forensic_backend.set_adaptive_learning(enabled)


    def on_guard_mode_changed(self, state):
        enabled = state == Qt.Checked
        LOG.info(f"[CRIMESCAN][UI] Forensic guard → {enabled}")

        if hasattr(self.forensic_backend, "set_forensic_guard"):
            self.forensic_backend.set_forensic_guard(enabled)

        # adaptive cannot exist without guard
        if not enabled and self.adaptive_toggle.isChecked():
            self.adaptive_toggle.setChecked(False)
