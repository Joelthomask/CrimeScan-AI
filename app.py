# =============================================================
# APP BOOTSTRAP  (MUST BE FIRST LINES OF FILE)
# =============================================================
# =============================================================
# FORCE LOCAL BASICSR (HI-DIFF) BEFORE ANY OTHER IMPORT
# =============================================================
import sys
from pathlib import Path
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add model repo paths
sys.path.insert(0, os.path.join(
    BASE_DIR,
    "auto_enhancer",
    "enhancement",
    "resolution",
    "GFPGAN"
))

sys.path.insert(0, os.path.join(
    BASE_DIR,
    "auto_enhancer",
    "enhancement",
    "deblurring",
    "HI_Diff"
))

PROJECT_ROOT = Path(__file__).resolve().parent
HI_DIFF_ROOT = PROJECT_ROOT / "auto_enhancer" / "enhancement" / "deblurring" / "HI_Diff"

if HI_DIFF_ROOT.exists():
    sys.path.insert(0, str(HI_DIFF_ROOT))



PROJECT_ROOT = Path(__file__).resolve().parent

# ---- Hard set project root as import base ----
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

print("[BOOT] Project root locked:", PROJECT_ROOT)


# =============================================================
# SESSION CREATION
# =============================================================
from utils.temp_manager import create_session, get_temp_subpath, get_session

SESSION = create_session()



# =============================================================
# LOGGER INIT (MUST BE BEFORE AI ENGINE)
# =============================================================
from utils.logger import init_logger, get_logger

BASE_LOGGER = init_logger(SESSION["root"])
SYS_LOG = get_logger()



SYS_LOG.info("Application boot started")
SYS_LOG.info(f"Session name → {SESSION['name']}")
SYS_LOG.info(f"Session root → {SESSION['root']}")


# =============================================================
# AI ENGINE INIT (loads all AI models ONCE)
# =============================================================




# =============================================================
# GUI IMPORTS (safe after engine + session + logging)
# =============================================================
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from gui.frontend.splash_screen import SplashScreen

from gui.frontend.auto_image_improver_page import AutoImageImproverPage
from gui.frontend.live_webcam_page import LiveWebcamPage
from gui.frontend.db_manager_page import DatabaseManagerPage
from gui.frontend.enroll_criminal_page import EnrollCriminalPage
from gui.frontend.image_crime_scan import ImageCrimeScanPage

from PyQt5.QtGui import QIcon, QPixmap, QPalette, QFont, QBrush, QColor, QRegion, QFontDatabase
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel,
    QStackedWidget, QMessageBox, QHBoxLayout, QFrame,
    QGraphicsDropShadowEffect, QToolButton, QGraphicsOpacityEffect,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect

from utils.font_manager import set_fonts



# =============================================================
# PROJECT PATHS / RESOURCES
# =============================================================
BASE_DIR = PROJECT_ROOT
BG_IMAGE = BASE_DIR / "assets/bg.jpg"
FONT_FILE = BASE_DIR / "Poppins-SemiBold.ttf"


def load_fonts():
    fonts_path = BASE_DIR / "assets/fonts"

    exo_regular = QFontDatabase.addApplicationFont(str(fonts_path / "Exo2-Regular.ttf"))
    exo_bold = QFontDatabase.addApplicationFont(str(fonts_path / "Exo2-Bold.ttf"))
    exo_semibold = QFontDatabase.addApplicationFont(str(fonts_path / "Exo2-SemiBold.ttf"))

    mono_regular = QFontDatabase.addApplicationFont(str(fonts_path / "RobotoMono-Regular.ttf"))
    mono_bold = QFontDatabase.addApplicationFont(str(fonts_path / "RobotoMono-Bold.ttf"))

    print("[FONTS] Loaded:", exo_regular, exo_bold, exo_semibold, mono_regular, mono_bold)

    return {
        "exo": QFont("Exo 2"),
        "exo_bold": QFont("Exo 2", weight=QFont.Bold),
        "exo_semibold": QFont("Exo 2", weight=QFont.DemiBold),
        "mono": QFont("Roboto Mono"),
        "mono_bold": QFont("Roboto Mono", weight=QFont.Bold)
    }

from PyQt5.QtGui import QPainter, QPainterPath

def rounded_pixmap(pixmap, radius):
    if pixmap.isNull():
        return pixmap

    result = QPixmap(pixmap.size())
    result.fill(Qt.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)

    path = QPainterPath()
    path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return result


class CriminalFaceRecognitionApp(QWidget):
    def __init__(self):
        super().__init__()

        self.timer = QTimer()
        ICON_PATH = BASE_DIR / "assets/logo.ico"   # or .png

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))


        # --- STACKED WIDGET FOR MULTIPLE PAGES --- #
        self.stacked_widget = QStackedWidget()

        # --- Lazy pages (professional pattern) ---
        self.webcam_page = None
        self.db_page = None
        self.crime_scan_page = None
        self.enroll_page = None
        self.auto_improver_page = None



        # ======================================================
        #  TOP LEFT LOGO + APP NAME BAR (Premium Header)
        # ======================================================

        self.header_bar = QFrame(self)
        self.header_bar.setFixedHeight(90)
        self.header_bar.setStyleSheet("""
        QFrame {
            background: rgba(0,0,0,100);

            border: none;
        }
        """)



        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(36, 22, 28, 14)


        header_layout.setSpacing(12)
        header_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # --- Logo ---
        self.logo_label = QLabel()
        logo_path = BASE_DIR / "assets/logo.png"
        if logo_path.exists():
            logo_pix = QPixmap(str(logo_path)).scaled(
                52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.logo_label.setPixmap(logo_pix)

        # --- App name ---
        self.app_name = QLabel("CrimeScan AI")
        self.app_name.setStyleSheet("""
            QLabel {
                color: rgb(0,220,255);
                font-size: 22px;
                font-weight: 600;
                letter-spacing: 1px;
            }
        """)
        self.app_name.setFont(FONTS["exo_semibold"])

        self.settings_btn = QToolButton(self.header_bar)
        self.settings_btn.setText("⚙")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setFixedSize(38, 38)
        self.settings_btn.setStyleSheet("""
        QToolButton {
            font-size: 20px;
            border-radius: 19px;
            color: #001014;

            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(0,220,255,200),
                stop:0.5 rgba(0,220,255,220),
                stop:1 rgba(0,220,255,200)

            );
        }

        QToolButton:hover {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #5cffff,
                stop:0.5 #33e1ff,
                stop:1 #6affea
            );
        }
        """)


        header_layout.addWidget(self.logo_label)
        header_layout.addWidget(self.app_name)

        header_layout.addStretch()
        header_layout.addWidget(self.settings_btn)


        # --- Soft glow shadow ---
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(35)
        shadow.setOffset(0, 0)   # 👈 IMPORTANT (no line effect)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.header_bar.setGraphicsEffect(shadow)



        # Page 0: Main menu
        self.page_main = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.header_bar)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignTop)

        # ======================================================
        #  HERO SECTION (Main Screen Identity)
        # ======================================================

        hero_container = QFrame()
        hero_layout = QVBoxLayout(hero_container)
        hero_layout.setContentsMargins(0, 20, 0, 5)

        hero_layout.setSpacing(14)
        hero_layout.setAlignment(Qt.AlignCenter)

        self.hero_title = QLabel("AI-POWERED CRIMINAL\nFACE RECOGNITION")
        self.hero_title.setAlignment(Qt.AlignCenter)
        self.hero_title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 54px;
                font-weight: 700;
                letter-spacing: 3px;
            }
        """)



        self.hero_subtitle = QLabel("Real-Time Detection • Forensic Enhancement • Identity Matching")
        self.hero_subtitle.setAlignment(Qt.AlignCenter)
        self.hero_subtitle.setStyleSheet("""
            QLabel {
                color: rgba(200,230,255,200);
                font-size: 16px;
                letter-spacing: 2px;
            }
        """)



        hero_layout.addWidget(self.hero_title)
        hero_layout.addWidget(self.hero_subtitle)
        main_layout.addWidget(hero_container)
        main_layout.addSpacing(36)





        # ======================================================
        #  STATUS ROW (Text-only forensic stats)
        # ======================================================

        stats_container = QFrame()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(60, 10, 60, 20)
        stats_layout.setSpacing(90)
        stats_layout.setAlignment(Qt.AlignCenter)

        def create_stat_text(title, value):
            wrapper = QFrame()
            v = QVBoxLayout(wrapper)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(6)
            v.setAlignment(Qt.AlignCenter)

            val = QLabel("0")






            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet("""
                QLabel {
                    background: transparent;
                    border: none;
                    font-size: 34px;
                    font-weight: 700;
                    color: white;
                    letter-spacing: 2px;
                }
            """)

            lab = QLabel(title)

            lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet("""
                QLabel {
                    background: transparent;
                    border: none;
                    font-size: 11px;
                    color: rgba(0,220,255,200);


                    letter-spacing: 3px;
                }
            """)

            wrapper.value_label = val
            wrapper.target_value = int(value)

            v.addWidget(val)
            v.addWidget(lab)
            return wrapper



        self.stat_widgets = []

        w = create_stat_text("ENROLLED FACES", "248")
        self.stat_widgets.append(w)
        stats_layout.addWidget(w)

        w = create_stat_text("CRIMINAL RECORDS", "51")
        self.stat_widgets.append(w)
        stats_layout.addWidget(w)

        w = create_stat_text("MATCHES FOUND", "37")
        self.stat_widgets.append(w)
        stats_layout.addWidget(w)

        w = create_stat_text("ACTIVE CAMERAS", "1")
        self.stat_widgets.append(w)
        stats_layout.addWidget(w)

        # --- now add stats to main layout ---
        stats_container.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(stats_container)
        main_layout.addSpacing(40)




        # ======================================================
        #  MAIN FORENSIC CARDS (Carousel Style)
        # ======================================================

        cards_data = [
            ("Live Recognition", BASE_DIR / "assets/liverecognition.jpg", self.open_webcam_page),
            ("Crime Scan", BASE_DIR / "assets/crimescan.jpg", self.open_crime_scan),
            ("Database", BASE_DIR / "assets/database.jpg", self.open_database_page),

            ("Enrollment", BASE_DIR / "assets/enroll.jpeg", self.open_enroll_page),
            ("Image Improver", BASE_DIR / "assets/enhancement.jpeg", self.open_auto_improver),

            ("Analytics", BASE_DIR / "assets/analytics.jpg", None),
        ]


        def create_main_card(title, image_path):
            card = QFrame()
            card.setCursor(Qt.PointingHandCursor)
            card.setFixedSize(220, 310)

            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(0,0,0,140);
                    border-radius: 18px;
                }
            """)

            # ---- Shadow (card only) ----
            card.shadow = QGraphicsDropShadowEffect(card)
            card.shadow.setBlurRadius(18)
            card.shadow.setOffset(0, 8)
            card.shadow.setColor(QColor(0,220,255))

            card.setGraphicsEffect(card.shadow)

            # ---- Layout ----
            v = QVBoxLayout(card)
            v.setContentsMargins(12, 12, 12, 12)
            v.setSpacing(8)


            # ---- Image (FIXED, never pops) ----
            img_label = QLabel(card)
            img_label.setFixedSize(196, 236)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet("background: transparent;")
            card.raw_pixmap = QPixmap(196, 236)
            card.raw_pixmap.fill(Qt.black)   # fallback so app never crashes


            if image_path.exists():
                raw = QPixmap(str(image_path)).scaled(
                    196, 236, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )

                card.raw_pixmap = raw   # ✅ store original clean pixmap
                rounded = rounded_pixmap(raw, 14)
                img_label.setPixmap(rounded)


                # ✅ HARD CLIP THE LABEL ITSELF (this removes sharp widget corners)
                mask = QRegion(QRect(0, 0, 196, 236), QRegion.Rectangle)
                rounded_path = QPainterPath()
                rounded_path.addRoundedRect(0, 0, 196, 236, 14, 14)
                mask = QRegion(rounded_path.toFillPolygon().toPolygon())
                img_label.setMask(mask)

            card.img_label = img_label


            # ====================================================
            #  IMAGE OVERLAY BORDER (thin rounded square, above image)
            # ====================================================
            img_overlay = QFrame(img_label)   # 👈 parent = img_label (important)
            img_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
            img_overlay.setStyleSheet("""
                QFrame {
                    border: 2.2px solid rgba(0, 246, 255, 150);
                    border-radius: 12px;
                    background: transparent;
                }
            """)

            img_overlay.setGeometry(0, 0, img_label.width(), img_label.height())
            img_overlay.raise_()

            def img_resize_event(e):
                img_overlay.setGeometry(0, 0, img_label.width(), img_label.height())

            img_label.resizeEvent = img_resize_event

            # store reference if needed later
            card.img_overlay = img_overlay
            img_overlay.shadow = QGraphicsDropShadowEffect(img_overlay)
            img_overlay.shadow.setBlurRadius(12)
            img_overlay.shadow.setOffset(0, 0)
            img_overlay.shadow.setColor(Qt.transparent)
            img_overlay.setGraphicsEffect(img_overlay.shadow)



            # ---- Gradient title button (replaces label + open) ----
            action_btn = QPushButton(title.upper(), card)
            action_btn.setFont(FONTS["mono_bold"])

            action_btn.setCursor(Qt.PointingHandCursor)

            # ✅ FIXED PREMIUM SIZE
            action_btn.setFixedSize(170, 36)   # width, height

            action_btn.setCursor(Qt.PointingHandCursor)
            action_btn.setFixedHeight(34)

            action_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 19px;
                color: #001014;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 2px;

                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0,220,255,200),
                    stop:0.5 rgba(0,220,255,220),
                    stop:1 rgba(0,220,255,200)

                );
            }

            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0,220,255,230),
                    stop:0.5 rgba(0,220,255,255),
                    stop:1 rgba(0,220,255,230)

                );
            }

            QPushButton:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0,220,255,150),
                    stop:0.5 rgba(0,220,255,170),
                    stop:1 rgba(0,220,255,150)

                );
            }
            """)

            action_btn.hide()   # only visible when center


            v.addWidget(img_label, 1, Qt.AlignCenter)
            v.addSpacing(10)
            v.addWidget(action_btn, 0, Qt.AlignCenter)


            # ---- Overlay border (ABOVE image) ----
            overlay = QFrame(card)
            overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
            overlay.setStyleSheet("""
                QFrame {
                    border: 1.5px solid rgba(0, 246, 255, 90);
                    border-radius: 18px;
                    background: transparent;
                }
            """)
            overlay.setGeometry(card.rect())
            overlay.raise_()

            def resizeEvent(e):
                overlay.setGeometry(card.rect())

            card.resizeEvent = resizeEvent

            # ---- Hover (glow ONLY) ----
            # ---- Hover (glow ONLY) ----
            def enterEvent(e):
                if not getattr(card, "is_center", False):
                    card.shadow.setBlurRadius(35)

                card.img_overlay.shadow.setColor(Qt.cyan)
                card.img_overlay.shadow.setBlurRadius(22)

            def leaveEvent(e):
                if not getattr(card, "is_center", False):
                    card.shadow.setBlurRadius(18)
                    card.img_overlay.shadow.setColor(Qt.transparent)
                    card.img_overlay.shadow.setBlurRadius(10)
                else:
                    # restore center glow
                    card.shadow.setBlurRadius(55)
                    card.img_overlay.shadow.setColor(Qt.cyan)
                    card.img_overlay.shadow.setBlurRadius(35)


            # ✅ THIS WAS MISSING
            card.enterEvent = enterEvent
            card.leaveEvent = leaveEvent
            card.action_btn = action_btn   # ✅ VERY IMPORTANT

            return card






        cards_container = QFrame()
        cards_layout = QHBoxLayout(cards_container)
        cards_layout.setContentsMargins(120, 10, 120, 0)

        cards_layout.setSpacing(40)
        cards_layout.setAlignment(Qt.AlignCenter)


        self.cards_data = cards_data
        self.card_index = 1   # center focus

        self.cards_container = cards_container
        self.cards_layout = cards_layout

        self.card_widgets = []
        for title, img, _ in self.cards_data:
            self.card_widgets.append(create_main_card(title, img))

        self.bind_card_clicks()


        self.left_card = self.card_widgets[self.card_index - 1]
        self.center_card = self.card_widgets[self.card_index]
        self.right_card = self.card_widgets[self.card_index + 1]

        self.cards_layout.addWidget(self.left_card)
        self.cards_layout.addWidget(self.center_card)
        self.cards_layout.addWidget(self.right_card)




        main_layout.addWidget(cards_container)

        # ================= SECTION INDICATOR (Carousel Dots) =================
        self.indicator_bar = QFrame()
        indicator_layout = QHBoxLayout(self.indicator_bar)
        indicator_layout.setContentsMargins(0, 6, 0, 0)
        indicator_layout.setSpacing(12)
        indicator_layout.setAlignment(Qt.AlignCenter)

        self.indicators = []

        for i in range(len(self.cards_data)):
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet("""
                QLabel {
                    border-radius: 5px;
                    background: rgba(0, 255, 255, 70);
                }
            """)
            self.indicators.append(dot)
            indicator_layout.addWidget(dot)

        main_layout.addSpacing(22)          # gap below cards
        main_layout.addWidget(self.indicator_bar)
        main_layout.addStretch(1)


        self.apply_focus_style()
        self.update_indicators()
        # ✅ VERY IMPORTANT — attach layout to home page
        self.page_main.setLayout(main_layout)



        # ================= FLOATING SIDE ARROWS =================

        self.left_arrow = QToolButton(self.page_main)
        self.left_arrow.setText("❮")
        self.left_arrow.setCursor(Qt.PointingHandCursor)
        self.left_arrow.setFixedSize(56, 56)
        self.left_arrow.setStyleSheet("""
            QToolButton {
                font-size: 48px;
                color: rgba(0, 255, 255, 220);
                background: transparent;
                border: none;
            }
            QToolButton:hover {
                color: rgba(0, 255, 255, 255);
            }
        """)


        self.right_arrow = QToolButton(self.page_main)
        self.right_arrow.setText("❯")
        self.right_arrow.setCursor(Qt.PointingHandCursor)
        self.right_arrow.setFixedSize(56, 56)
        self.right_arrow.setStyleSheet(self.left_arrow.styleSheet())

        self.left_arrow.clicked.connect(self.manual_left)
        self.right_arrow.clicked.connect(self.manual_right)

        self.left_arrow.raise_()
        self.right_arrow.raise_()


        # ======================================================
        #  AUTO SLIDE TIMER (every 5 seconds)
        # ======================================================

        self.carousel_timer = QTimer(self)
        self.carousel_timer.timeout.connect(self.auto_slide)
        self.carousel_timer.start(8000)  # 5 seconds

        # --- Main menu buttons --- #

# --- Register ONLY home page at boot ---
        self.stacked_widget.addWidget(self.page_main)
        self.stacked_widget.setCurrentWidget(self.page_main)


        # --- Set background --- #
        self.update_background()

        # --- Styles --- #
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(0,200,255,40);
                color: rgb(0,220,255);
                border: 1px solid rgba(0,220,255,100);


                font-size: 16px;
                padding: 10px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #d6d6d6;
            }
            QLabel {
                background: transparent;
                border: none;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }

        """)

        # --- Default page --- #
        self.stacked_widget.setCurrentWidget(self.page_main)

        # --- Main layout --- #
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

    # 👈 header on top
        root_layout.addWidget(self.stacked_widget)    # 👈 your full system UI

        self.setLayout(root_layout)


        self.setWindowTitle("CrimeScan AI")

        self.position_arrows()
        self.start_stats_animation()

        self.showMaximized()  # fullscreen windowed mode
    def position_arrows(self):
        side_margin = 110    # ⬅⬅ increased spacing from edges
        y = int(self.height() * 0.62)

        self.left_arrow.move(side_margin, y)
        self.right_arrow.move(self.width() - self.right_arrow.width() - side_margin, y)

        self.left_arrow.raise_()
        self.right_arrow.raise_()

    def open_database_page(self):
        if self.db_page is None:
            print("[UI] Creating DatabaseManagerPage...")
            self.db_page = DatabaseManagerPage(
                stacked=self.stacked_widget,
                main_menu=self.page_main
            )
            self.stacked_widget.addWidget(self.db_page)

        self.stacked_widget.setCurrentWidget(self.db_page)

    def auto_slide(self):
        self.card_index = (self.card_index + 1) % len(self.card_widgets)
        self.refresh_cards()

    def apply_focus_style(self):
        self.update_indicators()


        # ================= SIDE / NORMAL CARDS =================
        for card in self.card_widgets:
            card.is_center = False
            card.setFixedSize(220, 310)

            # ---- Side card glow ----
            card.shadow.setBlurRadius(34)
            card.shadow.setColor(QColor(0,220,255,140))



            # ---- Image ----
            card.img_label.setFixedSize(196, 236)
            self.set_card_image(card, 196, 236, 14)

            # ---- Image overlay (bright neon, not faded) ----
            card.img_overlay.setGeometry(0, 0, 196, 236)
            card.img_overlay.setStyleSheet("""
                QFrame {
                    border: 2px solid rgba(0,220,255,120);


                    border-radius: 14px;
                    background: transparent;
                }
            """)
            card.img_overlay.shadow.setColor(QColor(0, 255, 255, 150))
            card.img_overlay.shadow.setBlurRadius(18)

            # ---- Side card button (SMALL) ----
            if hasattr(card, "action_btn"):
                card.action_btn.show()
                self.style_card_button(card.action_btn, 140, 30)

                card.action_btn.setStyleSheet(card.action_btn.styleSheet() + """
                    QPushButton {
                        font-size: 10px;
                        letter-spacing: 1.4px;
                        opacity: 0.8;
                    }
                """)

            # ---- Card base ----
            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(0,0,0,155);
                    border-radius: 18px;
                    border: 1.4px solid rgba(0,255,255,120);
                }
            """)

        # ================= CENTER CARD =================
        c = self.center_card
        c.is_center = True
        c.setFixedSize(300, 400)

        # ---- Strong center glow ----
        c.shadow.setBlurRadius(55)
        card.shadow.setColor(QColor(0,220,255,230))


        big_w, big_h = 250, 300
        self.set_card_image(c, big_w, big_h, 18)

        c.img_label.setFixedSize(big_w, big_h)
        c.img_overlay.setGeometry(0, 0, big_w, big_h)

        c.img_overlay.setStyleSheet("""
            QFrame {
                border: 3px solid rgba(0,220,255,240);

                border-radius: 18px;
                background: transparent;
            }
        """)
        c.img_overlay.shadow.setColor(QColor(0, 255, 255, 220))
        c.img_overlay.shadow.setBlurRadius(35)

        c.setStyleSheet("""
            QFrame {
                background-color: rgba(0,0,0,190);
                border-radius: 22px;
                border: 1.5px solid rgba(0,255,255,140);
            }
        """)

        # ---- Center card button (BIG & PREMIUM) ----
        if hasattr(c, "action_btn"):
            c.action_btn.show()
            self.style_card_button(c.action_btn, 190, 40)

            c.action_btn.setStyleSheet(c.action_btn.styleSheet() + """
                QPushButton {
                    font-size: 13px;
                    letter-spacing: 2px;
                    opacity: 1;
                }
            """)


    def manual_left(self):
        self.carousel_timer.stop()
        self.slide_left()
        self.carousel_timer.start(5000)

    def manual_right(self):
        self.carousel_timer.stop()
        self.slide_right()
        self.carousel_timer.start(5000)




    # ----------------------------------------------------------
    #  UI Setup
    # ----------------------------------------------------------
    def add_main_menu_buttons(self, layout):
        buttons = [
            ("Live Webcam Recognition", self.open_webcam_page),
            ("Image Crime Scan", self.open_crime_scan),
            ("Enroll New Criminal", self.open_enroll_page),
            ("Manage Database", lambda: self.stacked_widget.setCurrentWidget(self.db_page)),
            ("Exit Application", self.close_application)
        ]
        for text, callback in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

    def resizeEvent(self, event):
        self.update_background()
        self.position_arrows()
        super().resizeEvent(event)

    def update_background(self):
        if BG_IMAGE.exists():
            pixmap = QPixmap(str(BG_IMAGE))
            palette = QPalette()
            palette.setBrush(QPalette.Window, QBrush(pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )))
            self.setPalette(palette)

    # ----------------------------------------------------------
    #  Page Navigation + Actions
    # ----------------------------------------------------------
    def open_webcam_page(self):
        if self.webcam_page is None:
            print("[UI] Creating LiveWebcamPage...")
            self.webcam_page = LiveWebcamPage(
                stacked_widget=self.stacked_widget,
                main_menu=self.page_main
            )
            self.stacked_widget.addWidget(self.webcam_page)

        self.stacked_widget.setCurrentWidget(self.webcam_page)
        self.webcam_page.start_camera()


    def open_crime_scan(self):
        if self.crime_scan_page is None:
            print("[UI] ImageCrimeScan Initilaized")
            self.crime_scan_page = ImageCrimeScanPage(
                stacked_widget=self.stacked_widget,
                main_menu=self.page_main,
                device="cuda"
            )
            self.stacked_widget.addWidget(self.crime_scan_page)

        self.stacked_widget.setCurrentWidget(self.crime_scan_page)


    def open_enroll_page(self):
        if self.enroll_page is None:
            print("[UI] EnrollCriminalPage Initilaized")
            self.enroll_page = EnrollCriminalPage(
                stacked=self.stacked_widget,
                main_menu=self.page_main
            )
            self.stacked_widget.addWidget(self.enroll_page)

        self.stacked_widget.setCurrentWidget(self.enroll_page)


    def close_application(self):
        self.timer.stop()
        self.close()
    def slide_left(self):
        self.card_index = (self.card_index - 1) % len(self.card_widgets)
        self.refresh_cards()


    def slide_right(self):
        self.card_index = (self.card_index + 1) % len(self.card_widgets)
        self.refresh_cards()


    def refresh_cards(self):

        # clear old widgets
        for i in reversed(range(self.cards_layout.count())):
            self.cards_layout.itemAt(i).widget().setParent(None)

        total = len(self.card_widgets)

        left_index = (self.card_index - 1) % total
        right_index = (self.card_index + 1) % total

        self.left_card = self.card_widgets[left_index]
        self.center_card = self.card_widgets[self.card_index]
        self.right_card = self.card_widgets[right_index]

        # ✅ ADD THEM BACK
        self.cards_layout.addWidget(self.left_card)
        self.cards_layout.addWidget(self.center_card)
        self.cards_layout.addWidget(self.right_card)

        self.apply_focus_style()
        self.bind_card_clicks()

        # reconnect action button safely
        action = self.cards_data[self.card_index][2]

        try:
            self.center_card.action_btn.clicked.disconnect()
        except:
            pass

        if action:
            self.center_card.action_btn.clicked.connect(action)
        self.update_indicators()





    def bind_card_clicks(self):
        for i, card in enumerate(self.card_widgets):
            def handler(event, idx=i):
                if idx != self.card_index:
                    self.card_index = idx
                    self.refresh_cards()
            card.mousePressEvent = handler

    def set_card_image(self, card, w, h, radius):

        if not hasattr(card, "raw_pixmap") or card.raw_pixmap.isNull():
            return

        scaled = card.raw_pixmap.scaled(
            w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )

        rounded = rounded_pixmap(scaled, radius)
        card.img_label.setPixmap(rounded)

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, radius, radius)
        mask = QRegion(path.toFillPolygon().toPolygon())
        card.img_label.setMask(mask)


    def style_card_button(self, btn, w, h):
        btn.setFixedSize(w, h)
        btn.setAttribute(Qt.WA_StyledBackground, True)

        radius = h // 2
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, radius, radius)
        mask = QRegion(path.toFillPolygon().toPolygon())
        btn.setMask(mask)

    def start_stats_animation(self):
        self.stat_index = 0
        self.stat_timer = QTimer(self)
        self.stat_timer.timeout.connect(self.update_stats)
        self.stat_timer.start(20)

    def update_stats(self):
        done = True

        for w in self.stat_widgets:
            current = int(w.value_label.text())
            target = w.target_value

            if current < target:
                step = max(1, target // 60)
                w.value_label.setText(str(min(target, current + step)))
                done = False

        if done:
            self.stat_timer.stop()
            QTimer.singleShot(7000, self.reset_stats)




    def reset_stats(self):
        for w in self.stat_widgets:
            w.value_label.setText("0")
        self.start_stats_animation()




    def update_indicators(self):
        if not hasattr(self, "indicators"):
            return

        for i, dot in enumerate(self.indicators):
            if i == self.card_index:
                dot.setFixedSize(14, 14)
                dot.setStyleSheet("""
                    QLabel {
                        border-radius: 7px;
                        background: qradialgradient(
                            cx:0.5, cy:0.5, radius:0.5,
                            stop:0 rgba(0,220,255,255),
                            stop:1 rgba(0,220,255,180)

                        );
                    }
                """)
            else:
                dot.setFixedSize(10, 10)
                dot.setStyleSheet("""
                    QLabel {
                        border-radius: 5px;
                        background: rgba(0,220,255,60);


                    }
                """)

    def open_auto_improver(self):
        if self.auto_improver_page is None:
            print("[UI] Entering AutoImageImprover")
            self.auto_improver_page = AutoImageImproverPage(
                stacked_widget=self.stacked_widget,
                main_menu=self.page_main,
                device="cuda"
            )
            self.stacked_widget.addWidget(self.auto_improver_page)

        self.stacked_widget.setCurrentWidget(self.auto_improver_page)

class AppLoader(QObject):
    progress = pyqtSignal(int, str)
    log = pyqtSignal(str)
    finished = pyqtSignal()


    def run(self):
        # ---- Session ----
        self.progress.emit(10, "Creating session...")
        from utils.temp_manager import create_session
        global SESSION
        SESSION = create_session()

        # ---- Logger ----
        self.progress.emit(25, "Initializing logger...")
        from utils.logger import init_logger, get_logger
        global BASE_LOGGER, SYS_LOG
        BASE_LOGGER = init_logger(SESSION["root"])
        SYS_LOG = get_logger()
        import logging

        class QtLogHandler(logging.Handler):
            def emit(inner_self, record):
                msg = inner_self.format(record)
                self.log.emit(msg)

        logger = logging.getLogger()
        handler = QtLogHandler()
        logger.addHandler(handler)
        loader.log.connect(splash.update_step)

        # ---- AI Engine ----
        # ---- AI Engine ----
        self.progress.emit(50, "Loading AI engine...")

        # Engine already loaded earlier in app.py,
        # so we just hold at 50% while warmups/logging finish

        import time
        # ---- AI Engine ----
        self.progress.emit(50, "Loading AI engine...")

        from core.ai_engine import get_ai_engine
        engine = get_ai_engine()

        # optional FAN stabilization
        import cv2
        test_img = cv2.imread("tuning/test.jpg")
        if test_img is not None:
            engine.pose_checker.analyze(test_img)

        self.progress.emit(100, "Models ready")
        # tiny pause for visual smoothness

        # Smooth finish after engine ready
        for p in range(50, 101, 5):
            self.progress.emit(p, "Finalizing models...")
            time.sleep(0.04)

        self.progress.emit(100, "Models ready")

        self.progress.emit(110, "Preparing interface...")


        self.progress.emit(120, "Starting interface...")
        self.finished.emit()


# --------------------------------------------------------------
#  Entry Point
# --------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    FONTS = load_fonts()
    set_fonts(FONTS)

        # --- Splash ---
    splash = SplashScreen(FONTS)
    splash.show()
    app.processEvents()

    # ---- Load engine now ----
    import cv2


    # --- Loader thread ---
    loader = AppLoader()
    thread = QThread()
    loader.moveToThread(thread)

    # Progress updates
    loader.progress.connect(
        lambda p, t: (
            splash.update_progress(p),
            splash.update_step(t)
        )
    )

    # After loading complete
    def on_loaded():
        from PyQt5.QtCore import QTimer

        def start_main():
            window = CriminalFaceRecognitionApp()
            window.show()
            splash.close()
            thread.quit()

        # pause at 100%
        # stop particles + burst
        # splash.loader.finish()

        # wait 2 seconds
        QTimer.singleShot(1500, start_main)


    loader.finished.connect(on_loaded)

    thread.started.connect(loader.run)
    thread.start()

    sys.exit(app.exec_())

    app = QApplication(sys.argv)

    FONTS = load_fonts()
    set_fonts(FONTS)   # ✅ share fonts globally

    window = CriminalFaceRecognitionApp()
    sys.exit(app.exec_())