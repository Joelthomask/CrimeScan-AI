"""
Policy Updater
---------------
Builds and stores learned policy parameters.

Does NOT rewrite policy code.
Instead writes learned tuning to JSON file.
"""

import json
import os
from auto_enhancer.adaptive_learner.policy_builder import PolicyBuilder


class PolicyUpdater:
    def __init__(self,
                 case_root="learner_cases",
                 output_path="learner_cases/learned_policy.json"):
        self.builder = PolicyBuilder(case_root)
        self.output_path = output_path

    # ---------------------------------------------------------
    def update_policy(self):

        stats = self.builder.build()

        if not stats:
            print("[LEARNER] No policy stats generated")
            return None

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        with open(self.output_path, "w") as f:
            json.dump(stats, f, indent=2)

        print("[LEARNER] Learned policy saved")

        return stats
