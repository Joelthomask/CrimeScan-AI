# gui/frontend/enroll_criminal_page.py
import os
import sys
import shutil
import vlc
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QTextEdit, QLabel, QPushButton, QFileDialog, QMessageBox
)
from ..backend.enroll_criminal_backend import EnrollCriminalBackend
from utils.logger import get_logger
LOG = get_logger()

from utils.temp_manager import get_temp_subpath  # temp folder manager


class EnrollCriminalPage(QWidget):
    MIN_W = 180
    MIN_H = 40
    ADDR_H = MIN_H * 4

    def __init__(self, stacked, main_menu, log_box=None):
        super().__init__()
        self.stacked = stacked
        self.main_menu = main_menu
        self.log_box = log_box

        # --- Backend (DB path is centralized, not passed) ---
                # --- Backend (lazy) ---
        self.backend = None


        self.init_ui()
        self.apply_styles()




    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left panel: VLC-powered looping video ---
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(0, 0, 0, 0)
        left_panel.setSpacing(0)
        self.video_frame = QWidget()
        self.video_frame.setMinimumSize(640, 360)
        self.video_frame.setMaximumSize(1200, 1200)
        from PyQt5.QtWidgets import QSizePolicy
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_frame.setStyleSheet("background-color: black;")

        # VLC setup
        base_dir = os.path.dirname(os.path.abspath(__file__))
        PROJECT_ROOT = os.path.abspath(os.path.join(base_dir, "..", ".."))
        vlc_dir = os.path.join(PROJECT_ROOT, "vlc")
        os.environ["PATH"] = vlc_dir + os.pathsep + os.environ["PATH"]

        self.vlc_instance = vlc.Instance(["--no-xlib", "--no-video-title-show"])
        self.vlc_player = self.vlc_instance.media_player_new()

        if sys.platform.startswith("linux"):
            self.vlc_player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.vlc_player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.vlc_player.set_nsobject(int(self.video_frame.winId()))

        video_path = os.path.join(PROJECT_ROOT, "assets", "side_video.mp4")
        if not os.path.exists(video_path):
            LOG.info(f"[WARN] Video not found at {video_path}")
        else:
            media = self.vlc_instance.media_new(video_path)
            media.add_option("input-repeat=65535")
            self.vlc_player.set_media(media)
            self.vlc_player.play()

        left_panel.addWidget(self.video_frame, stretch=1)

        # --- Right panel: form layout ---
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(60, 0, 40, 0)
        right_panel.setSpacing(25)
        right_panel.addStretch(1)

        title = QLabel("""
<div style='line-height:75%; font-size:60px; font-weight:bold; font-family:Poppins;'>
    ENROLL<br><span style='color:#00ffff;'>NEW CRIMINAL</span>
</div>
""")
        title.setObjectName("titleCombo")
        title.setAlignment(Qt.AlignLeft)
        title.setTextFormat(Qt.RichText)
        title.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
        right_panel.addWidget(title)

        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Name"); self.name_edit.setFixedHeight(self.MIN_H)
        self.age_edit = QLineEdit(); self.age_edit.setPlaceholderText("Age"); self.age_edit.setFixedHeight(self.MIN_H)
        row1 = QHBoxLayout(); row1.setSpacing(10); row1.addWidget(self.name_edit, 1); row1.addWidget(self.age_edit, 1)
        right_panel.addLayout(row1)

        self.gender_edit = QLineEdit(); self.gender_edit.setPlaceholderText("Gender"); self.gender_edit.setFixedHeight(self.MIN_H)
        self.height_edit = QLineEdit(); self.height_edit.setPlaceholderText("Height"); self.height_edit.setFixedHeight(self.MIN_H)
        row2 = QHBoxLayout(); row2.setSpacing(10); row2.addWidget(self.gender_edit, 1); row2.addWidget(self.height_edit, 1)
        right_panel.addLayout(row2)

        self.address_edit = QLineEdit(); self.address_edit.setPlaceholderText("Address"); self.address_edit.setFixedHeight(self.ADDR_H)
        right_panel.addWidget(self.address_edit)

        self.crime_edit = QLineEdit(); self.crime_edit.setPlaceholderText("Crime"); self.crime_edit.setFixedHeight(self.MIN_H)
        self.location_edit = QLineEdit(); self.location_edit.setPlaceholderText("Location"); self.location_edit.setFixedHeight(self.MIN_H)
        row4 = QHBoxLayout(); row4.setSpacing(10); row4.addWidget(self.crime_edit, 1); row4.addWidget(self.location_edit, 1)
        right_panel.addLayout(row4)

        self.dob_edit = QLineEdit(); self.dob_edit.setPlaceholderText("DOB"); self.dob_edit.setFixedHeight(self.MIN_H)
        self.other_info_edit = QTextEdit(); self.other_info_edit.setPlaceholderText("Other Info"); self.other_info_edit.setFixedHeight(self.MIN_H)
        row5 = QHBoxLayout(); row5.setSpacing(10); row5.addWidget(self.dob_edit, 1); row5.addWidget(self.other_info_edit, 1)
        right_panel.addLayout(row5)

        brow = QHBoxLayout(); brow.setSpacing(20); brow.addStretch(1)
        ebtn = QPushButton("ENROLL"); ebtn.setObjectName("primaryAction"); ebtn.clicked.connect(self.enroll_and_copy)
        bbtn = QPushButton("BACK"); bbtn.setObjectName("secondaryAction"); bbtn.clicked.connect(lambda: self.stacked.setCurrentWidget(self.main_menu))
        brow.addWidget(ebtn); brow.addWidget(bbtn); brow.addStretch(1)
        right_panel.addLayout(brow)
        right_panel.addStretch(1)

        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 1)

    def showEvent(self, event):
        super().showEvent(event)
        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player.play()

    def apply_styles(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #1e1e2f;
                color: #e0e0e0;
                font-family: 'Poppins', sans-serif;
            }}
            QLineEdit, QTextEdit {{
                background-color: rgba(255,255,255,0.05);
                border: 1px solid #00ffff;
                border-radius: 8px;
                padding: 0 10px;
                color: #ffffff;
                font-size: 14px;
            }}
            QLineEdit::placeholder, QTextEdit::placeholder {{
                color: #bbbbbb;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid #00ffff;
            }}
            QPushButton#primaryAction {{
                background-color: #00ffff;
                color: #1e1e2f;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton#primaryAction:hover {{
                background-color: #33ffff;
            }}
            QPushButton#secondaryAction {{
                background-color: transparent;
                color: #00ffff;
                padding: 12px 24px;
                border: 2px solid #00ffff;
                border-radius: 8px;
                font-size: 16px;
            }}
            QPushButton#secondaryAction:hover {{
                background-color: rgba(0,255,255,0.1);
            }}
        """)

    def enroll_and_copy(self):

        if self.backend is None:
            LOG.info("[ENROLL-UI] Creating Enrollment Backend (lazy init)")
            self.backend = EnrollCriminalBackend(log_box=self.log_box)

        # Get form values
        name, age = self.name_edit.text().strip(), self.age_edit.text().strip()


        gender, height = self.gender_edit.text().strip(), self.height_edit.text().strip()
        address = self.address_edit.text().strip()
        crime, location = self.crime_edit.text().strip(), self.location_edit.text().strip()
        dob, other = self.dob_edit.text().strip(), self.other_info_edit.toPlainText().strip()

        LOG.info(f"[ENROLL] Enroll attempt: {name}")


        # Step1: Insert into DB
        folder = self.backend.enroll_criminal(self, name, age, gender, height, address, crime, location, dob, other)
        if not folder:
            LOG.info("[ERROR] Enrollment failed at DB insertion.")

            return

        # Step2: Select images
        imgs, _ = QFileDialog.getOpenFileNames(self, "Select Image(s)")
        if not imgs:
            LOG.info("[WARN] No images selected.")

            return

        # Copy images to structured temp folder
        temp_dir = get_temp_subpath("enroll_input")
        temp_paths = []
        for img in imgs:
            try:
                dest = os.path.join(temp_dir, os.path.basename(img))
                shutil.copy2(img, dest)
                temp_paths.append(dest)
            except Exception as e:
                LOG.info(f"[ERROR] Failed to copy {img}: {str(e)}")

        LOG.info(f"[ENROLL] {len(temp_paths)} images copied to temp folder.")


        # Step3: Backend copy & generate embeddings
        self.backend.copy_images(self, folder, temp_paths)
        self.backend.generate_embeddings(name, age, crime, height, gender, address, location, dob, other, temp_paths)
        LOG.info(f"[ENROLL] Embeddings generated for {name}")


        # Step4: Notify user & reset form
        QMessageBox.information(self, "Success",
            f"Enrolled “{name}” with {len(temp_paths)} new image(s) and stored embeddings."
        )

        for w in (self.name_edit, self.age_edit, self.gender_edit,
                  self.height_edit, self.address_edit, self.crime_edit,
                  self.location_edit, self.dob_edit, self.other_info_edit):
            w.clear()

        self.stacked.setCurrentWidget(self.main_menu)

