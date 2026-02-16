import os
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy,
    QStackedWidget, QPushButton, QInputDialog,
    QLineEdit, QListWidget, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtGui import QTransform
from PyQt5.QtGui import QImageReader
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

from PyQt5.QtGui import QPixmap, QFontDatabase, QFont, QPainter, QColor

from gui.frontend.image_crime_scan import AnimatedBorder, GlassOverlay
from gui.frontend.enroll_criminal_page import EnrollCriminalPage
from gui.backend.db_manager_backend import DatabaseManagerBackend
from utils.logger import get_logger
import sys
import vlc
from PyQt5.QtGui import QImageReader

LOG = get_logger()

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


class DatabaseManagerPage(QWidget):
    def __init__(self, stacked: QStackedWidget, main_menu: QWidget):
        super().__init__()

        self.stacked = stacked
        self.main_menu = main_menu
        self.backend = DatabaseManagerBackend()

        self._load_fonts()

        bg_file = os.path.join(project_root, "assets", "app_background.jpg")
        self.bg_pixmap = QPixmap(bg_file) if os.path.exists(bg_file) else QPixmap()

        self.enroll_page = EnrollCriminalPage(
            stacked=self.stacked,
            main_menu=self
        )
        self.stacked.addWidget(self.enroll_page)

        self.init_ui()
        self.load_criminals()

    # ---------- Fonts ----------
    def _load_fonts(self):
        fid = QFontDatabase.addApplicationFont("gui/Poppins-SemiBold.ttf")
        family = QFontDatabase.applicationFontFamilies(fid)
        self.font_family = family[0] if family else "Sans Serif"

        self.font_btn = QFont(self.font_family, 12, QFont.Medium)

    # ---------- UI ----------
    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(30, 20, 30, 30)
        root_layout.setSpacing(12)
        # ===== PAGE TITLE =====
        page_title = QLabel("DATABASE MANAGER")
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

        root_layout.addSpacing(10)
        root_layout.addWidget(page_title)

        root_layout.addSpacing(6)
        root_layout.addWidget(page_divider)

        root_layout.addSpacing(14)

        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)

        # ===== LEFT PANEL CARD =====
        left_box = QFrame()
        left_box.setFixedSize(750, 600)

        left_box.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 120);
                border: 2px solid #329FCB;
                border-radius: 14px;
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setOffset(0, 0)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(50, 159, 203, 90))
        left_box.setGraphicsEffect(shadow)
        self.left_glass = GlassOverlay(left_box)
        self.left_glass.lower()


        self.left_border = AnimatedBorder(left_box, radius=14)
        self.left_border.raise_()

        box_layout = QVBoxLayout(left_box)
        box_layout.setContentsMargins(20, 20, 20, 20)
        box_layout.setSpacing(20)

        # ---------- TOP ROW ----------
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # ===== SEARCH + LIST =====
        self.search_box = QFrame()
        self.search_box.setStyleSheet("""
            QFrame {
                background-color: rgba(25,25,25,150);
                border-radius: 16px;
                border: 2px solid #444;
            }
        """)

        search_layout = QVBoxLayout(self.search_box)
        search_layout.setContentsMargins(16, 16, 16, 16)
        search_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search criminal...")
        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255,255,255,20);
                border: 1px solid #00ffff;
                border-radius: 18px;
                padding-left: 12px;
                color: white;
                font-size: 14px;
            }
        """)

        search_layout.addWidget(self.search_input)
        self.search_input.textChanged.connect(self.filter_list)

        self.overlay_list = QListWidget()
        self.overlay_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(10,10,10,200);
                border: 2px solid #00ffff;
                border-radius: 10px;
                color: white;
                font-size: 18px;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: rgba(0,255,255,80);
            }
        """)

        self.overlay_list.setMinimumHeight(300)

        search_layout.addWidget(self.overlay_list)

        self.overlay_list.itemClicked.connect(self.show_criminal_details)

        # ===== DETAILS =====
        self.details_box = QFrame()
        self.details_box.setStyleSheet("""
            QFrame {
                background-color: rgba(25,25,25,150);
                border-radius: 16px;
                border: 2px solid #444;
            }
        """)

        details_layout = QVBoxLayout(self.details_box)
        details_layout.setContentsMargins(16, 16, 16, 16)

        self.details_label = QLabel("")
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("""
            color: #66d9ff;
            font-size: 14px;
            line-height: 18px;
        """)


        details_layout.addWidget(self.details_label)

        top_row.addWidget(self.search_box, 1)
        top_row.addWidget(self.details_box, 1)

        box_layout.addLayout(top_row, 4)

        # ===== PREVIEW BOX =====
        self.preview_box = QFrame()
        self.preview_box.setStyleSheet("""
            QFrame {
                background-color: rgba(25,25,25,150);
                border-radius: 16px;
                border: 2px solid #444;
            }
        """)

        preview_layout = QVBoxLayout(self.preview_box)
        preview_layout.setContentsMargins(10, 10, 10, 10)

        self.preview_container = QHBoxLayout()
        preview_layout.addLayout(self.preview_container)

        self.preview_label = QLabel("Preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color:white;")

        preview_layout.addWidget(self.preview_label)

        box_layout.addWidget(self.preview_box, 2)

        preview_layout.setContentsMargins(10, 10, 10, 10)

        self.preview_container = QHBoxLayout()
        preview_layout.addLayout(self.preview_container)

        self.preview_label = QLabel("Preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color:white;")

        preview_layout.addWidget(self.preview_label)


        left_wrapper = QHBoxLayout()
        left_wrapper.addStretch()

        left_box.setMaximumWidth(820)
        left_wrapper.addWidget(left_box)

        left_wrapper.addStretch()

        main_layout.addLayout(left_wrapper, 1)
        main_layout.addStretch(2)

        # ---------- RIGHT SIDE (VIDEO) ----------
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 90, 40, 0)
        right_layout.setSpacing(12)


        self.video_frame = QFrame()
        self.video_frame.setFixedSize(620, 420)
        self.video_frame.setStyleSheet("background: transparent;")

        right_layout.addWidget(self.video_frame, alignment=Qt.AlignLeft)

        right_layout.addSpacing(15)

        # ---------- TITLE ----------
        self.db_title = QLabel("")

        self.db_title.setFont(QFont(self.font_family, 44, QFont.Bold))
        self.db_title.setStyleSheet("""
            color: white;
            font-size: 44px;
            font-weight: 600;
        """)

        self.db_title.setAlignment(Qt.AlignLeft)
        self.db_title.setContentsMargins(0, 10, 0, 10)
        self.db_title.adjustSize()




        right_layout.addWidget(self.db_title)

        # ---------- PARAGRAPH ----------
        self.db_para = QLabel("")
        self.db_para.setWordWrap(True)
        self.db_para.setStyleSheet("color: cyan; font-size: 20px;")
        self.db_para.setAlignment(Qt.AlignLeft)
        self.db_para.setMaximumWidth(1100)

        right_layout.addWidget(self.db_para)

        right_layout.addStretch()

        main_layout.addLayout(right_layout,2)
        # -------- VLC SETUP --------
        self.vlc_instance = vlc.Instance(["--no-video-title-show"])
        self.vlc_player = self.vlc_instance.media_player_new()

        if sys.platform.startswith("linux"):
            self.vlc_player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.vlc_player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.vlc_player.set_nsobject(int(self.video_frame.winId()))

        video_path = os.path.join(project_root, "assets", "side_video2.mp4")
        media = self.vlc_instance.media_new(video_path)
        media.add_option("input-repeat=65535")  # loop forever
        self.vlc_player.set_media(media)
        self.vlc_player.play()

        # ---------- BUTTON BAR ----------
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(20)

        self.back_btn = self._styled_button("BACK")
        self.enroll_btn = self._styled_button("ENROLL")
        self.delete_btn = self._styled_button("DELETE")
        self.clear_btn = self._styled_button("CLEAR")

        bottom_bar.addStretch()
        bottom_bar.addWidget(self.back_btn)
        bottom_bar.addWidget(self.enroll_btn)
        bottom_bar.addWidget(self.delete_btn)
        bottom_bar.addWidget(self.clear_btn)
        bottom_bar.addStretch()

        # connections
        self.back_btn.clicked.connect(
            lambda: self.stacked.setCurrentWidget(self.main_menu)
        )
        self.enroll_btn.clicked.connect(
            lambda: self.stacked.setCurrentWidget(self.enroll_page)
        )
        self.delete_btn.clicked.connect(self.delete_person)
        self.clear_btn.clicked.connect(self.clear_all)

        root_layout.addLayout(main_layout, 1)
        root_layout.addLayout(bottom_bar)
    def filter_list(self, text):
        text = text.lower()

        for i in range(self.overlay_list.count()):
            item = self.overlay_list.item(i)
            item.setHidden(text not in item.text().lower())

    # ---------- Button Style ----------
    def _styled_button(self, text):
        btn = QPushButton(text)
        btn.setFont(self.font_btn)
        btn.setMinimumHeight(45)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: rgba(255,255,255,18);
                border: 1px solid rgba(255,255,255,60);
                border-radius: 8px;
                padding: 10px 18px;
            }
            QPushButton:hover {
                color: #00E5FF;
                background-color: rgba(0,229,255,25);
                border-color: #00E5FF;
            }
            QPushButton:pressed {
                color: #00E5FF;
                background-color: rgba(0,229,255,45);
            }
        """)
        return btn
    def show_criminal_details(self, item):
        name = item.text()

        row = self.backend.db.get_criminal_by_name(name)
        if not row:
            return

        criminal = self.backend.db.fetch_criminal_by_id(row[0])
        if not criminal:
            return

        self.detail_lines = [
            f"Name: {criminal['name']}",
            f"Age: {criminal['age']}",
            f"Gender: {criminal['gender']}",
            f"Address: {criminal['address']}",
            f"Height: {criminal['height']}",
            f"Location: {criminal['location']}",
            f"Crime: {criminal['crime']}",
            f"Other Info: {criminal['other_info']}",
        ]

        self.current_line = 0
        self.details_label.setText("")

        if not hasattr(self, "detail_timer"):
            self.detail_timer = QTimer(self)
            self.detail_timer.timeout.connect(self._type_next_line)

        self.detail_timer.start(25)

        self.pending_image_folder = criminal["image_folder"]

    def _type_next_line(self):
        if self.current_line >= len(self.detail_lines):
            self.detail_timer.stop()
            self.show_preview_images(self.pending_image_folder)
            return

        line = self.detail_lines[self.current_line]

        if not hasattr(self, "char_index"):
            self.char_index = 0

        if self.char_index < len(line):
            existing = self.details_label.text()
            self.details_label.setText(existing + line[self.char_index])
            self.char_index += 1
        else:
            self.details_label.setText(
                self.details_label.text() + "\n"
            )
            self.current_line += 1
            self.char_index = 0

    def show_preview_images(self, folder_path):
        # clear old previews
        while self.preview_container.count():
            item = self.preview_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not os.path.exists(folder_path):
            return

        images = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ][:3]

        for img_path in images:
            # Correct EXIF orientation automatically
            reader = QImageReader(img_path)
            reader.setAutoTransform(True)

            img = reader.read()
            if img.isNull():
                continue

            # Apply grayscale filter (visual only)
            img = img.convertToFormat(QImage.Format_Grayscale8)

            pixmap = QPixmap.fromImage(img).scaled(
                130, 130,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            lbl = QLabel()
            lbl.setPixmap(pixmap)
            lbl.setAlignment(Qt.AlignCenter)

            # open in Windows viewer
            def open_image(ev, path=img_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))

            lbl.mousePressEvent = open_image

            self.preview_container.addWidget(lbl)


    def showEvent(self, event):
        super().showEvent(event)
        self.load_criminals()
        self.start_title_animation()


    def start_title_animation(self):
        self.title_text = "DATABASE"
        self.title_index = 0
        self.db_title.setText("")

        if not hasattr(self, "title_timer"):
            self.title_timer = QTimer(self)
            self.title_timer.timeout.connect(self._type_title)

        self.title_timer.start(90)



    def _type_title(self):
        if self.title_index >= len(self.title_text):
            self.title_timer.stop()
            self.start_para_animation()
            return

        self.db_title.setText(self.title_text[:self.title_index + 1])
        self.title_index += 1


    def start_para_animation(self):
        raw_text = (
            "This database securely stores and manages detailed criminal records. "
            "It supports enrollment, fast searching, and real time recognition "
            "for forensic investigations. The system allows efficient profile "
            "management, quick updates, and scalable data expansion for growing "
            "law enforcement needs.."
        )


        words = raw_text.split()
        lines = [" ".join(words[i:i+7]) for i in range(0, len(words), 7)]
        self.para_text = "\n".join(lines)


        self.para_index = 0
        self.db_para.setText("")

        if not hasattr(self, "para_timer"):
            self.para_timer = QTimer(self)
            self.para_timer.timeout.connect(self._type_para)

        self.para_timer.start(40)

    def hideEvent(self, event):
        if hasattr(self, "title_timer"):
            self.title_timer.stop()
        if hasattr(self, "para_timer"):
            self.para_timer.stop()

        super().hideEvent(event)

    def _type_para(self):
        if self.para_index >= len(self.para_text):
            self.para_timer.stop()
            QTimer.singleShot(1500, self.start_para_animation)  # loop
            return

        self.db_para.setText(self.para_text[:self.para_index + 1])
        self.para_index += 1

    # ---------- DB ----------
    def delete_person(self):
        name, ok = QInputDialog.getText(self, "Delete Criminal", "Enter name:")
        if ok and name.strip():
            self.backend.delete_criminal(self, name.strip())
            self.load_criminals()

    def clear_all(self):
        if self.backend.clear_all_criminals(self):
            self.load_criminals()

    def load_criminals(self):
        criminals = self.backend.load_criminals() or []
        LOG.info(f"[DB PAGE] Loaded criminals: {criminals}")

        self.overlay_list.clear()

        for name in criminals:
            self.overlay_list.addItem(name)

        LOG.info(
            f"[DB PAGE] List items count: {self.overlay_list.count()}"
        )


    # ---------- Background ----------
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.bg_pixmap.isNull():
            cover = self.bg_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            painter.drawPixmap(0, 0, cover)
