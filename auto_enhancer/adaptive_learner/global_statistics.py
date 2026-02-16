"""
Global Statistics Generator
-----------------------------
Builds learner-wide statistics after policy rebuild.
"""

import os
import json
from collections import defaultdict


class GlobalStatisticsGenerator:

    def __init__(self, case_root="learner_cases"):
        self.case_root = case_root

    # ---------------------------------------------------------
    def generate(self):

        cases = self._load_cases()

        if not cases:
            return

        total_improvement = 0
        case_count = 0

        action_stats = defaultdict(lambda: {
            "count": 0,
            "accepted": 0,
            "delta_sum": 0.0
        })

        for case in cases:

            meta = case.get("metadata") or {}
            summary = meta.get("final_summary") or {}
            baseline = meta.get("baseline") or {}

            base_sim = baseline.get("similarity", 0)
            final_sim = summary.get("final_similarity", base_sim)

            total_improvement += (final_sim - base_sim)
            case_count += 1

            for step in case.get("steps", []):

                act = step.get("type")
                if not act:
                    continue

                action_stats[act]["count"] += 1
                action_stats[act]["delta_sum"] += (
                    step.get("delta_similarity") or 0
                )

                if step.get("accepted"):
                    action_stats[act]["accepted"] += 1

        actions_summary = {}

        for act, s in action_stats.items():
            actions_summary[act] = {
                "avg_gain":
                    s["delta_sum"] / s["count"]
                    if s["count"] else 0,
                "accept_rate":
                    s["accepted"] / s["count"]
                    if s["count"] else 0,
                "usage_count": s["count"]
            }

        stats = {
            "total_cases": case_count,
            "average_similarity_improvement":
                total_improvement / case_count
                if case_count else 0,
            "action_statistics": actions_summary
        }

        output = os.path.join(
            self.case_root,
            "global_statistics.json"
        )

        with open(output, "w") as f:
            json.dump(stats, f, indent=2)

        print("[LEARNER] Global statistics updated")

    # ---------------------------------------------------------
    def _load_cases(self):

        cases = []

        for case_id in os.listdir(self.case_root):

            case_dir = os.path.join(self.case_root, case_id)
            if not os.path.isdir(case_dir):
                continue

            meta_file = os.path.join(case_dir, "metadata.json")
            steps_file = os.path.join(case_dir, "steps.json")

            if not os.path.exists(meta_file):
                continue

            with open(meta_file) as f:
                metadata = json.load(f)

            steps = []
            if os.path.exists(steps_file):
                with open(steps_file) as f:
                    steps = json.load(f)

            cases.append({
                "metadata": metadata,
                "steps": steps
            })

        return cases
