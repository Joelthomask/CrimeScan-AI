# gui/splash_screen.py
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QFrame, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor
import random
from PyQt5.QtCore import QTimer

from .loading_bar import LoadingBar


# -----------------------------
# Glitch Decoration Widget
# -----------------------------
class GlitchOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(120)   # refresh speed

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # middle glitch fragments only
        for _ in range(16):
            center_x = w // 2
            spread_left = int(w * 0.32)
            spread_right = int(w * 0.26)

            x = random.randint(center_x - spread_left,
                            center_x + spread_right)



            y = random.randint(int(h * 0.56), int(h * 0.76))


            length = random.randint(20, 55)

            painter.fillRect(
                x, y,
                length,
                2,
                QColor(0, 220, 255, random.randint(60, 140))
            )


# -----------------------------
# Splash Screen
# -----------------------------
class SplashScreen(QWidget):
    def __init__(self, fonts):
        super().__init__()
        self.fonts = fonts
        self._drag_pos = None


        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("")

        self.setFixedSize(720, 420)

        self.init_ui()
        self.center_on_screen()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        ASSETS = PROJECT_ROOT / "assets"


        # Outer cyan rectangle
        outer = QFrame()
        outer.setStyleSheet("""
            QFrame {
                border-radius: 0px;
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:1,
                    stop:0 #123e57,
                    stop:0.4 #16698a,
                    stop:0.75 #1ca3d6,
                    stop:1 #49e1ff
                );
            }
        """)






        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(4, 4, 4, 4)


        # Inner dark rectangle
        inner = QFrame()
        inner.setStyleSheet("""
            QFrame {
                background-color: #121417;
                border-radius: 0px;
            }
        """)


        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(30, 26, 30, 26)
        inner_layout.setSpacing(14)
        inner_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # glitch decoration
        glitch = GlitchOverlay(inner)
        glitch.resize(inner.size())
        glitch.lower()

        def resize_event(e):
            glitch.resize(inner.size())

        inner.resizeEvent = resize_event
        inner_layout.addSpacing(20)
        # -----------------
        # Logo (top center)
        # -----------------
        logo = QLabel()
        pix = QPixmap(str(ASSETS / "logo.png"))

        logo.setPixmap(
            pix.scaled(
                72, 72,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )
        logo.setAlignment(Qt.AlignCenter)
        inner_layout.addWidget(logo)
        inner_layout.addSpacing(5)
        # -----------------
        # Title
        # -----------------
        title = QLabel("CrimeScan AI")
        title.setFont(self.fonts["exo_semibold"])



        title.setStyleSheet("color: #e0e0e0; font-size: 28px;")

        title.setAlignment(Qt.AlignCenter)
        inner_layout.addWidget(title)
        inner_layout.addSpacing(45)   # adjust value if needed


        # -----------------
        # Loading bar
        # -----------------
        texture = ASSETS / "bar_texture.png"

        self.loader = LoadingBar(texture_path=str(texture))


        self.loader.setFixedHeight(70)
        inner_layout.addWidget(self.loader)
        inner_layout.addSpacing(3)

        # -----------------
        # Step text
        # -----------------
        self.log_label = QLabel("")
        self.log_label.setAlignment(Qt.AlignCenter)

        self.log_label.setFont(QFont("Roboto Mono", 10))

        self.log_label.setStyleSheet("color: #9aa4ad;")
        self.log_label.setWordWrap(True)
        self.log_label.setFixedHeight(40)

        inner_layout.addWidget(self.log_label)


        outer_layout.addWidget(inner)
        root_layout.addWidget(outer)

    def center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    def update_step(self, text):
        # remove timestamps
        if "] " in text:
            text = text.split("] ", 1)[-1]

        text = text.strip()

        if not text:
            return

        self.log_label.setText(text)

    def _animate_progress(self):
        current = self.loader.progress
        target = getattr(self, "target_progress", current)

        if current < target:
            self.loader.progress += min(0.8, target - current)
            self.loader.update()

        elif current > target:
            self.loader.progress = target

        # trigger burst only when bar visually reaches end
        if (
            self.loader.progress >= 100
            and not self.loader.finished
        ):
            self.loader.finish()



    def update_progress(self, value):
        mapped = int((value / 120) * 100)
        mapped = max(0, min(100, mapped))

        # target progress
        self.target_progress = mapped

        if not hasattr(self, "_smooth_timer"):
            self._smooth_timer = QTimer(self)
            self._smooth_timer.timeout.connect(self._animate_progress)
            self._smooth_timer.start(16)


        self.loader.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
