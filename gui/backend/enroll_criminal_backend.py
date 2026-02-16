# gui/backend/enroll_backend.py
import os
import shutil
from PyQt5.QtWidgets import QMessageBox
from database.sqlite.criminals_db import DatabaseHandler
from enrollment.enrollment import EnrollmentPipeline
from utils.logger import get_logger
LOG = get_logger()

class EnrollCriminalBackend:
    def __init__(self, log_box=None):
        self.db = DatabaseHandler()
        self.pipeline = EnrollmentPipeline()
        self.log_box = log_box


    def enroll_criminal(self, parent, name, age, gender, height, address,
                        crime, location, dob, other_info):
        """Handles DB insertion and folder preparation."""

        if not name:
            QMessageBox.warning(parent, "Validation Error", "Name is required.")
            return False

        safe = name.replace(" ", "_")
        folder = os.path.join("criminal_gallery", "custom", safe)

        # --- Duplicate check FIRST ---
        if self.db.get_criminal_by_name(name):
            QMessageBox.warning(
                parent,
                "Duplicate Entry",
                f"A criminal with the name \"{name}\" already exists.\n\n"
                "Please enter a different name."
            )
            return False

        # --- Create folder (single source of truth) ---
        os.makedirs(folder, exist_ok=True)

        # --- Insert into DB (store ONLY gallery path) ---
        criminal_id = self.db.insert_criminal(
            name=name,
            age=int(age) if age.isdigit() else None,
            gender=gender or None,
            height=height or None,
            address=address or None,
            crime=crime or None,
            location=location or None,
            dob=dob or None,
            other_info=other_info or None,
            image_folder=folder
        )

        LOG.info(f"[INFO] Inserted new criminal '{name}' with ID={criminal_id}")
        return folder


    def copy_images(self, parent, folder, image_paths):
        """Copy selected images to the criminal folder."""
        if not image_paths:
            QMessageBox.warning(parent, "No Images", "No images selected for enrollment.")
            return []

        copied = []
        for src in image_paths:
            dst = os.path.join(folder, os.path.basename(src))
            try:
                shutil.copy2(src, dst)
                copied.append(dst)
            except Exception as e:
                LOG.info(f"[WARN] Could not copy {src}: {e}")
        return copied

    def generate_embeddings(self, name, age, crime, height, gender, address, location, dob, other_info, copied_images):
        """Call enrollment pipeline to generate embeddings."""
        if copied_images:
            self.pipeline.enroll_multiple_images(
                image_paths=copied_images,
                name=name,
                age=int(age) if age.isdigit() else None,
                crime=crime,
                height=height,
                otherinfo=f"Gender:{gender}; Addr:{address}; Loc:{location}; DOB:{dob}; Info:{other_info}"
            )
