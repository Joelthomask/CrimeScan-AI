"""
Learner Manager
----------------
Controls adaptive learner lifecycle.

Responsibilities:
• Enable/disable learner
• Accept completed case logs
• Parse and store cases
• Trigger automatic policy rebuild
"""
import json

import os
from utils.logger import get_logger

from auto_enhancer.adaptive_learner.log_parser import LogParser
from auto_enhancer.adaptive_learner.case_storage import CaseStorage
from auto_enhancer.adaptive_learner.policy_builder import PolicyBuilder
from auto_enhancer.adaptive_learner.global_statistics import GlobalStatisticsGenerator
from auto_enhancer.adaptive_learner.case_statistics import CaseStatisticsGenerator
class LearnerManager:
    """
    Central controller for adaptive learner.
    """

    def __init__(self):
        self.log = get_logger()
        self.enabled = False

        self.parser = LogParser()
        self.storage = CaseStorage()
        self.builder = PolicyBuilder()
        self.state = self._load_state()

        # rebuild policy every N cases
        self.rebuild_interval = 20

        self.log.info("[LEARNER] Manager initialized (disabled)")

    # =========================================================
    # Toggle control
    # =========================================================
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        state = "ENABLED" if enabled else "DISABLED"
        self.log.info(f"[LEARNER] Adaptive learner → {state}")

    # =========================================================
    # Case processing entry point
    # =========================================================
    def process_case(self, log_path: str):
        """
        Called when forensic pipeline finishes.
        """
        print("[DEBUG] LearnerManager.process_case called")
        print("[DEBUG] Learner enabled:", self.enabled)
        print("[DEBUG] Log path:", log_path)

        if not self.enabled:
            self.log.info("[LEARNER] Skipping case (disabled)")
            return

        if not log_path or not os.path.exists(log_path):
            self.log.warning("[LEARNER] Log file missing")
            return

        self.log.info("[LEARNER] Parsing completed case")

        parsed = self.parser.parse(log_path)
        print("[DEBUG] Parsed case:", parsed.get("case_id"))
        print("[DEBUG] Steps count:", len(parsed.get("steps", [])))

        if not parsed:
            self.log.warning("[LEARNER] Parser returned empty result")
            return

        case_id = parsed.get("case_id", "UNKNOWN_CASE")

        # ---- store metadata ----
        self.storage.save_metadata(case_id, {
            "baseline": parsed.get("baseline"),
            "quality_scores": parsed.get("quality_scores"),
            "intelligence": parsed.get("intelligence"),
            "final_summary": parsed.get("final_summary"),
        })

        # ---- store step results ----
        self.storage.save_steps(case_id, parsed.get("steps", []))

        self.log.info(f"[LEARNER] Case stored → {case_id}")
        self.state["processed_cases"] += 1
        self._save_state()


        CaseStatisticsGenerator().generate(
            self.storage.get_case_dir(case_id)
        )

        # ---- auto policy rebuild ----
        self._maybe_rebuild_policy()

    # =========================================================
    # Policy rebuild trigger
    # =========================================================
    def _maybe_rebuild_policy(self):

        total_cases = self.state["processed_cases"]

        if total_cases == 0:
            return

        if total_cases % self.rebuild_interval != 0:
            return

        self.log.info(
            f"[LEARNER] {total_cases} cases reached → rebuilding policy"
        )

        self.build_policy()


    # =========================================================
    # Policy builder trigger
    # =========================================================
    def build_policy(self):

        if not self.enabled:
            return

        result = self.builder.build()

        GlobalStatisticsGenerator().generate()

        self.log.info("[LEARNER] Policy statistics updated")

        return result


    # =========================================================
    # Reset hook
    # =========================================================
    def reset(self):
        self.log.info("[LEARNER] Reset requested (not implemented)")
    def _load_state(self):
        path = os.path.join(self.storage.root_dir, "learner_state.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {"processed_cases": 0}
    def _save_state(self):
        path = os.path.join(self.storage.root_dir, "learner_state.json")
        with open(path, "w") as f:
            json.dump(self.state, f, indent=2)
