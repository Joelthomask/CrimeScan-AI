# learner/case_storage.py

import os
import json
from datetime import datetime


class CaseStorage:
    """
    Stores learner-ready case data.

    Responsibilities:
    - Create case storage folders
    - Save structured case metadata
    - Save per-step enhancement data
    - Load stored cases for learner training
    """

    def __init__(self, root_dir="learner_cases"):
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    # --------------------------------------------------
    # Case folder management
    # --------------------------------------------------
    def create_case_folder(self, case_id: str) -> str:
        """
        Create folder for a case.

        learner_cases/
            CASE_0001/
                metadata.json
                steps.json
        """
        case_path = os.path.join(self.root_dir, case_id)
        os.makedirs(case_path, exist_ok=True)
        return case_path

    # --------------------------------------------------
    # Metadata storage
    # --------------------------------------------------
    def save_metadata(self, case_id: str, metadata: dict):
        """
        Store case-level metadata.
        """
        case_path = self.create_case_folder(case_id)
        meta_file = os.path.join(case_path, "metadata.json")

        metadata["saved_at"] = datetime.now().isoformat()
        print("[DEBUG] Saving metadata for", case_id)

        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)

    # --------------------------------------------------
    # Step data storage
    # --------------------------------------------------
    def save_steps(self, case_id: str, steps: list):
        """
        Store enhancement steps data.
        """
        case_path = self.create_case_folder(case_id)
        steps_file = os.path.join(case_path, "steps.json")
        print("[DEBUG] Saving steps for", case_id)

        with open(steps_file, "w") as f:
            json.dump(steps, f, indent=2)

    # --------------------------------------------------
    # Case loading
    # --------------------------------------------------
    def load_case(self, case_id: str):
        case_path = os.path.join(self.root_dir, case_id)

        meta_file = os.path.join(case_path, "metadata.json")
        steps_file = os.path.join(case_path, "steps.json")

        metadata = None
        steps = []

        if os.path.exists(meta_file):
            with open(meta_file, "r") as f:
                metadata = json.load(f)

        if os.path.exists(steps_file):
            with open(steps_file, "r") as f:
                steps = json.load(f)

        return {
            "metadata": metadata,
            "steps": steps,
        }

    # --------------------------------------------------
    # Bulk loading for learner training
    # --------------------------------------------------
    def load_all_cases(self):
        """
        Load all stored cases.
        """
        cases = []

        for case_id in os.listdir(self.root_dir):
            case_path = os.path.join(self.root_dir, case_id)
            if os.path.isdir(case_path):
                cases.append(self.load_case(case_id))

        return cases
    def get_case_dir(self, case_id: str) -> str:
        return os.path.join(self.root_dir, case_id)
