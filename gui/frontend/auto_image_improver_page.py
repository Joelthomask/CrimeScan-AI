import os, math, random, shutil, cv2
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import (
    QFont, QPixmap, QLinearGradient, QColor,
    QPainter, QPen, QPainterPath
)
from PyQt5.QtCore import (
    Qt, QPoint, QRectF, QPropertyAnimation,
    QEasingCurve, QTimer, pyqtProperty
)

from gui.backend.auto_image_improver_backend import AutoImageImproverBackend
from utils.logger import get_logger
LOG = get_logger()

from utils.temp_manager import get_temp_subpath, get_session
from PyQt5.QtGui import QBrush
from utils.font_manager import get_font
from PyQt5.QtWidgets import QScrollArea

# --- Before/After Slider Widget (same as before) ---
class BeforeAfterSlider(QWidget):
    def __init__(self, before_path=None, after_path=None, parent=None):
        super().__init__(parent)
        self.before_img = QPixmap(before_path) if before_path else QPixmap()
        self.after_img = QPixmap(after_path) if after_path else QPixmap()
        self.slider_pos = self.width() // 2
        self.dragging = False
        self.setMinimumSize(500, 350)
        self.setAttribute(Qt.WA_TranslucentBackground)  # allow rounded border look

    def set_images(self, before_path, after_path):
        self.before_img = QPixmap(before_path) if before_path else QPixmap()
        self.after_img = QPixmap(after_path) if after_path else QPixmap()
        self.update()


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # --- Define a square area inside widget ---
        side = min(self.width(), self.height()) - 4  # keep it square, leave margin for border
        x = (self.width() - side) // 2
        y = (self.height() - side) // 2
        border_rect = QRectF(x, y, side, side)

        # --- Gradient border ---
        gradient = QLinearGradient(border_rect.topLeft(), border_rect.bottomRight())
        gradient.setColorAt(0, QColor(0, 255, 255))
        gradient.setColorAt(1, QColor(0, 180, 255))
        pen = QPen(QBrush(gradient), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.black)
        painter.drawRoundedRect(border_rect, 20, 20)  # rounded square look

        # --- Clip strictly to rounded square ---
        painter.setClipPath(self._rounded_clip_path(border_rect, 20))

        if self.before_img.isNull() or self.after_img.isNull():
            painter.drawText(border_rect, Qt.AlignCenter, "No Images Loaded")
            return

        # Scale images to FILL the box (cropping if needed)
        before_scaled = self.before_img.scaled(border_rect.size().toSize(),
                                            Qt.KeepAspectRatioByExpanding,
                                            Qt.SmoothTransformation)
        after_scaled = self.after_img.scaled(border_rect.size().toSize(),
                                            Qt.KeepAspectRatioByExpanding,
                                            Qt.SmoothTransformation)

        # Center images inside the square
        bx = border_rect.x() + (border_rect.width() - before_scaled.width()) / 2
        by = border_rect.y() + (border_rect.height() - before_scaled.height()) / 2
        ax = border_rect.x() + (border_rect.width() - after_scaled.width()) / 2
        ay = border_rect.y() + (border_rect.height() - after_scaled.height()) / 2

        # Draw before fully
        painter.drawPixmap(int(bx), int(by), before_scaled)

        # Draw after clipped
        clip_rect = QRectF(border_rect.x(), border_rect.y(), self.slider_pos - x, border_rect.height())
        painter.setClipRect(clip_rect, Qt.IntersectClip)
        painter.drawPixmap(int(ax), int(ay), after_scaled)
        painter.setClipping(False)

        # --- Slider line ---
        pen = QPen(QColor(255, 255, 255), 2)
        painter.setPen(pen)
        painter.drawLine(self.slider_pos, border_rect.top(), self.slider_pos, border_rect.bottom())

        # --- Slider handle ---
        brush = QBrush(QColor(0, 255, 255))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(self.slider_pos, int(border_rect.center().y())), 10, 10)


    def _rounded_clip_path(self, rect, radius):
        from PyQt5.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path

    def mousePressEvent(self, event):
        if abs(event.x() - self.slider_pos) < 20:
            self.dragging = True

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.slider_pos = max(0, min(event.x(), self.width()))
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def resizeEvent(self, event):
        self.slider_pos = self.width() // 2
        super().resizeEvent(event)
# --

class PolicyToggle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 42)
        self.mode = "forensic"

        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.mode = "enhancement" if self.mode == "forensic" else "forensic"
        self.update()
        if hasattr(self.parent(), "on_policy_changed"):
            self.parent().on_policy_changed(self.mode)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        # ---- Track ----
        grad = QLinearGradient(0, 0, rect.width(), 0)
        grad.setColorAt(0, QColor(0, 246, 255, 140))
        grad.setColorAt(1, QColor(0, 180, 255, 140))

        p.setBrush(grad)
        p.setPen(QPen(QColor(0, 246, 255, 200), 1.5))
        p.drawRoundedRect(rect, 21, 21)

        # ---- Knob ----
        knob_x = rect.left() + 6 if self.mode == "forensic" else rect.right() - 36
        knob = QRectF(knob_x, rect.top() + 4, 32, 32)

        p.setBrush(QColor(0, 255, 255))
        p.setPen(Qt.NoPen)
        p.drawEllipse(knob)

        # ---- Labels ----
        p.setPen(QColor(220, 250, 255))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))

        left_color = QColor(0,255,255) if self.mode == "forensic" else QColor(160,160,160)
        right_color = QColor(0,255,255) if self.mode == "enhancement" else QColor(160,160,160)

        p.setPen(left_color)
        p.drawText(QRectF(0,0,150,42), Qt.AlignCenter, "FORENSIC")

        p.setPen(right_color)
        p.drawText(QRectF(150,0,150,42), Qt.AlignCenter, "ENHANCEMENT")


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





class AutoImageImproverPage(QWidget):

    def __init__(self, stacked_widget, main_menu, device="cpu"):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.main_menu = main_menu
        self.device = device

        self.session_paths = get_session()
        self.policy_mode = "forensic"   # default
        self.backend = AutoImageImproverBackend(device=device, mode=self.policy_mode)



        self.image_path = None


        # === Root layout ===
        # === Root layout ===
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(30, 20, 30, 30)
        root_layout.setSpacing(14)

        # ===== PAGE TITLE =====
        page_title = QLabel("IMAGE IMPROVER")
        page_title.setAlignment(Qt.AlignCenter)
        page_title.setFont(QFont("Segoe UI", 36, QFont.Bold))
        page_title.setStyleSheet("""
        QLabel {
            color: rgb(0,220,255);
            letter-spacing: 3px;
            background: transparent;
        }
        """)

        # ===== DIVIDER =====
        page_divider = QFrame()
        page_divider.setFixedHeight(4)
        page_divider.setStyleSheet("""
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

        root_layout.addSpacing(8)
        root_layout.addWidget(page_title)
        root_layout.addSpacing(6)
        root_layout.addWidget(page_divider)
        root_layout.addSpacing(12)


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
        upload_title = QLabel("UPLOAD IMAGE FOR ENHANCMENT")
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

        # ===== Animated Border (ambient) =====
        self.result_border = AnimatedBorder(result_card, radius=14, start_delay=None)
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
        self.result_layout.setContentsMargins(26, 22, 26, 22)
        self.result_layout.setSpacing(12)
        self.result_layout.setAlignment(Qt.AlignTop)

        # ================= TITLE =================
        self.title_label = QLabel("AI ENHANCE")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Segoe UI", 26, QFont.Bold))
        self.title_label.setStyleSheet("""
            QLabel {
                color: #00E5FF;
                letter-spacing: 4px;
                background: transparent;
                border: none;
            }
        """)

        self.result_layout.addWidget(self.title_label)
        self.result_layout.addSpacing(4)

        # ================= DIVIDER =================
        self.ai_divider = GlowingDivider(result_card)
        self.ai_divider.start()
        self.result_layout.addWidget(self.ai_divider)
        self.result_layout.addSpacing(4)

        # ================= BEFORE / AFTER PREVIEW =================
        self.before_after = BeforeAfterSlider(parent=result_card)
        self.before_after.setMinimumSize(340, 240)
        self.before_after.setFixedSize(360, 240)
        self.result_layout.addWidget(self.before_after, alignment=Qt.AlignCenter)
        self.result_layout.setStretchFactor(self.before_after, 0)
        self.result_layout.addSpacing(2)

        # ================= REPORT BOX (SCROLLABLE) =================
        self.report_box = QFrame()
        self.report_box.setFixedHeight(160)
        self.report_box.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 85);
                border: 1.6px solid rgba(0, 229, 255, 160);
                border-radius: 12px;
            }
        """)

        self.report_label = QLabel("")

        self.report_label.setWordWrap(True)
        self.report_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.report_label.setFont(get_font("mono"))

        self.report_label.setStyleSheet("""
            QLabel {
                color: rgba(220,245,255,230);
                font-size: 12px;
                letter-spacing: 1px;
                line-height: 1.6;
                background: transparent;
            }
        """)

        self.report_scroll = QScrollArea()
        self.report_scroll.setWidgetResizable(True)
        self.report_scroll.setFrameShape(QFrame.NoFrame)
        self.report_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.report_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.report_scroll.setStyleSheet("""
            QScrollBar:vertical {
                background: rgba(0,0,0,60);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,229,255,180);
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.report_scroll.setWidget(self.report_label)

        report_layout = QVBoxLayout(self.report_box)
        report_layout.setContentsMargins(12, 10, 12, 10)
        report_layout.addWidget(self.report_scroll)

        self.result_layout.addWidget(self.report_box)


        # ================= DOWNLOAD BUTTON =================
        self.download_btn = QPushButton("DOWNLOAD")
        self.download_btn.setFixedSize(180, 42)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))

        self.download_btn.setStyleSheet("""
        QPushButton {
            color: #001014;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 2px;

            border: none;
            border-radius: 10px;

            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #00f6ff,
                stop:0.5 #00cfff,
                stop:1 #00ffd5
            );
        }

        QPushButton:hover {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #5cffff,
                stop:0.5 #33e1ff,
                stop:1 #6affea
            );
        }

        QPushButton:pressed {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #00b6be,
                stop:0.5 #009dcc,
                stop:1 #00c7a8
            );
        }
        """)

        # --- Glow ---
        dl_glow = QGraphicsDropShadowEffect()
        dl_glow.setBlurRadius(18)
        dl_glow.setOffset(0, 0)
        dl_glow.setColor(QColor(0, 229, 255, 160))
        self.download_btn.setGraphicsEffect(dl_glow)

        self.download_btn.clicked.connect(self.download_enhanced_image)

        btn_wrap = QHBoxLayout()
        btn_wrap.addStretch()
        btn_wrap.addWidget(self.download_btn)
        btn_wrap.addStretch()
        self.download_btn.setEnabled(False)


        self.result_layout.addLayout(btn_wrap)


        # ================= RIGHT HALF WRAPPER =================
        right_half = QVBoxLayout()
        right_half.addStretch(1)
        h_right = QHBoxLayout()
        h_right.addStretch(1)
        h_right.addWidget(result_card)
        h_right.addStretch(1)
        right_half.addLayout(h_right)
        right_half.addStretch(1)

        # ================= MAIN ASSEMBLY =================
        main_layout.addLayout(left_half, 1)
        main_layout.addLayout(right_half, 1)

        root_layout.addLayout(main_layout)
        # ================= POLICY TOGGLE =================
        policy_wrap = QHBoxLayout()
        policy_wrap.setContentsMargins(0, 0, 0, 0)

        self.policy_toggle = PolicyToggle(self)

        policy_wrap.addStretch()
        policy_wrap.addWidget(self.policy_toggle)
        policy_wrap.addStretch()

        root_layout.addLayout(policy_wrap)

        # ================= GLOBAL BOTTOM BACK BAR =================
        global_bottom_bar = QHBoxLayout()
        global_bottom_bar.setContentsMargins(0, 10, 0, 0)

        self.back_btn = QPushButton("BACK")
        self.back_btn.setFixedSize(170, 48)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setFont(get_font("exo_semibold"))

        self.back_btn.setStyleSheet("""
        QPushButton {
            color: white;
            background-color: rgba(255, 255, 255, 18);
            border: 1.5px solid rgba(255, 255, 255, 60);
            border-radius: 8px;
            letter-spacing: 3px;
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

        # Glow (same family as other system buttons)
        back_glow = QGraphicsDropShadowEffect()
        back_glow.setBlurRadius(22)
        back_glow.setOffset(0, 0)
        back_glow.setColor(QColor(0, 229, 255, 160))
        self.back_btn.setGraphicsEffect(back_glow)

        self.back_btn.clicked.connect(self.go_back)

        global_bottom_bar.addStretch()
        global_bottom_bar.addWidget(self.back_btn)
        global_bottom_bar.addStretch()

        root_layout.addLayout(global_bottom_bar)

        self.setLayout(root_layout)


    def reset_result_state(self):
        self.policy_toggle.setEnabled(True)


        self.before_after.set_images(None, None)
        self.report_label.setText("")
        self.result_border.stop()
        self.final_image_path = None
        self.download_btn.setEnabled(False)



    def upload_image(self):
        self.policy_toggle.setEnabled(False)

        self.reset_result_state()

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.jpg *.jpeg *.png)"
        )
        if not file_path:
            return

        temp_input_dir = get_temp_subpath("input")
        if not temp_input_dir:
            return

        try:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(temp_input_dir, filename)
            shutil.copy2(file_path, dest_path)
            self.image_path = dest_path

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
            LOG.info(f"[ERROR][IMPROVER] Copy failed: {e}")
            return

        # ✅ RUN AUTO IMPROVER
        self.run_auto_improver()

    def go_back(self):
        self.reset_result_state()
        self.stacked_widget.setCurrentWidget(self.main_menu)


    def update_enhancement_ui(self, before_path, after_path, report_text):
        self.before_after.set_images(before_path, after_path)
        self.report_label.setText(report_text)
        self.result_border.start()
        self.download_btn.setEnabled(True)

    def download_enhanced_image(self):
        if not hasattr(self, "final_image_path") or not self.final_image_path:
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Enhanced Image", "enhanced.png", "Images (*.png *.jpg *.jpeg)"
        )

        if save_path:
            shutil.copy2(self.final_image_path, save_path)

    def build_forensic_report(self, result: dict) -> str:

        qa_before = result.get("quality_before", {})
        qa_after  = result.get("quality_after", {})
        intel_rounds = result.get("intelligence", [])
        steps = result.get("steps", [])

        obj_b = qa_before.get("objective", {})
        faces_b = qa_before.get("faces", {})

        obj_a = qa_after.get("objective", {})
        faces_a = qa_after.get("faces", {})

        lines = []

        lines.append("FORENSIC AUTO ENHANCEMENT REPORT")
        lines.append("────────────────────────────────")
        lines.append("")

        # ====================================================
        # INITIAL QA
        # ====================================================
        lines.append("[ INITIAL IMAGE QUALITY ]")
        lines.append(f"• Blur variance   : {round(obj_b.get('blur_variance',0),2)}")
        lines.append(f"• Brightness mean : {round(obj_b.get('brightness',0),2)}")
        lines.append(f"• Contrast (std)  : {round(obj_b.get('contrast',0),2)}")
        lines.append(f"• Noise (PSNR)    : {round(obj_b.get('psnr',0),2)}")
        lines.append(f"• Resolution     : {obj_b.get('width',0)} × {obj_b.get('height',0)}")
        lines.append(f"• Faces detected : {faces_b.get('count',0)}")
        lines.append("")

        # ====================================================
        # INTELLIGENCE ROUNDS
        # ====================================================
        lines.append("[ INTELLIGENCE ANALYSIS ]")

        if not intel_rounds:
            lines.append("• No intelligence data available.")
        else:
            for intel in intel_rounds:
                r = intel.get("round", "?")
                decision = intel.get("decision", {})
                notes = decision.get("enhancement_notes", [])
                actions = decision.get("recommended_actions", [])

                lines.append(f"")
                lines.append(f"ROUND {r}")
                lines.append(f"• Mode        : {intel.get('mode','').upper()}")
                lines.append(f"• Target/Risk : {decision.get('target_quality', decision.get('risk_level','N/A'))}")
                lines.append(f"• Confidence  : {decision.get('confidence',0)}")

                lines.append("  Planned actions:")
                if actions:
                    for a in actions:
                        meta = " ".join([f"{k}={v}" for k,v in a.items() if k != "type"])
                        lines.append(f"   - {a.get('type','').upper()} {meta}")
                else:
                    lines.append("   - None")

                if notes:
                    lines.append("  Reasoning:")
                    for n in notes:
                        lines.append(f"   • {n}")

        lines.append("")

        # ====================================================
        # APPLIED PIPELINE TRACE
        # ====================================================
        lines.append("[ EXECUTED ENHANCEMENTS ]")

        if steps:
            for i, step in enumerate(steps, 1):
                r = step.get("round", "?")
                step_type = step.get("type", "unknown").upper()
                t = step.get("time", 0)
                lines.append(f"{i}. [R{r}] {step_type:<11} | {t}s")
        else:
            lines.append("• No enhancement required")

        lines.append("")

        # ====================================================
        # FINAL QA
        # ====================================================
        lines.append("[ FINAL IMAGE QUALITY ]")
        lines.append(f"• Blur variance   : {round(obj_a.get('blur_variance',0),2)}")
        lines.append(f"• Brightness mean : {round(obj_a.get('brightness',0),2)}")
        lines.append(f"• Contrast (std)  : {round(obj_a.get('contrast',0),2)}")
        lines.append(f"• Noise (PSNR)    : {round(obj_a.get('psnr',0),2)}")
        lines.append(f"• Resolution     : {obj_a.get('width',0)} × {obj_a.get('height',0)}")
        lines.append(f"• Faces detected : {faces_a.get('count',0)}")

        lines.append("")
        lines.append("[ FINAL STATUS ]")
        lines.append(f"• Total stages executed : {len(steps)}")
        lines.append(f"• Enhancement rounds    : {len(intel_rounds)}")

        return "\n".join(lines)


    def run_auto_improver(self):

        result = self.backend.run_pipeline(self.image_path)

        self.final_image_path = result["final_image"]

        forensic_text = self.build_forensic_report(result)

        self.update_enhancement_ui(
            before_path=result["before"],
            after_path=result["after"],
            report_text=forensic_text
        )

    def on_policy_changed(self, mode):
        LOG.info("[UI] Policy changed → %s", mode.upper())

        self.policy_mode = mode
        self.backend.set_mode(mode)
