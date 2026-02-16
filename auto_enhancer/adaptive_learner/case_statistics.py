"""
Case Statistics Generator
--------------------------
Builds per-case statistics for learner analysis.
"""

import os
import json


class CaseStatisticsGenerator:

    def generate(self, case_dir):

        metadata_path = os.path.join(case_dir, "metadata.json")
        steps_path = os.path.join(case_dir, "steps.json")

        if not os.path.exists(metadata_path) or not os.path.exists(steps_path):
            return

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        with open(steps_path, "r") as f:
            steps = json.load(f)

        baseline = metadata.get("baseline", {})
        summary = metadata.get("final_summary", {})

        base_sim = baseline.get("similarity", 0)
        final_sim = summary.get("final_similarity", base_sim)

        accepted = 0
        rejected = 0
        total_time = 0

        best_step = None
        worst_step = None

        best_gain = -999
        worst_gain = 999

        for s in steps:

            delta = s.get("delta_similarity") or 0
            proc_time = s.get("processing_time_ms") or 0

            total_time += proc_time

            if s.get("accepted"):
                accepted += 1
            else:
                rejected += 1

            if delta > best_gain:
                best_gain = delta
                best_step = s.get("type")

            if delta < worst_gain:
                worst_gain = delta
                worst_step = s.get("type")

        stats = {
            "baseline_similarity": base_sim,
            "final_similarity": final_sim,
            "total_improvement": final_sim - base_sim,

            "steps_total": len(steps),
            "steps_accepted": accepted,
            "steps_rejected": rejected,

            "best_step": best_step,
            "best_gain": best_gain,

            "worst_step": worst_step,
            "worst_gain": worst_gain,

            "total_processing_time_ms": total_time
        }

        output = os.path.join(case_dir, "statistics.json")

        with open(output, "w") as f:
            json.dump(stats, f, indent=2)
