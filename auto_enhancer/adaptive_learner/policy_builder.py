"""
Adaptive Policy Builder
------------------------
Learns enhancement effectiveness and builds
tuned policy statistics.

Learns:
• Model effectiveness
• Strength effectiveness
• Ordering effects
• Harmful actions
• Recommended priorities
"""

from collections import defaultdict
from auto_enhancer.adaptive_learner.case_storage import CaseStorage


class PolicyBuilder:
    def __init__(self, case_root="learner_cases"):
        self.storage = CaseStorage(case_root)

    # =========================================================
    # Public entry
    # =========================================================
    def build(self):

        cases = self.storage.load_all_cases()

        if not cases:
            print("[LEARNER] No cases available")
            return {}

        action_stats = self._compute_action_stats(cases)
        strength_stats = self._compute_strength_stats(cases)
        order_stats = self._compute_order_stats(cases)

        priorities = self._recommend_priorities(action_stats)
        bad_actions = self._detect_bad_actions(action_stats)

        result = {
            "action_stats": action_stats,
            "strength_stats": strength_stats,
            "order_stats": order_stats,
            "recommended_priorities": priorities,
            "bad_actions": bad_actions,
        }

        print("[LEARNER] Policy statistics built")
        return result

    # =========================================================
    # Model effectiveness
    # =========================================================
    def _compute_action_stats(self, cases):

        stats = defaultdict(lambda: {
            "count": 0,
            "accepted": 0,
            "delta_similarity_sum": 0.0,
        })

        for case in cases:
            for step in case["steps"]:

                action = step["type"]
                delta = step.get("delta_similarity") or 0
                accepted = step.get("accepted", False)

                s = stats[action]
                s["count"] += 1
                s["delta_similarity_sum"] += delta

                if accepted:
                    s["accepted"] += 1

        for action, s in stats.items():
            s["avg_delta"] = (
                s["delta_similarity_sum"] / s["count"]
                if s["count"] else 0
            )
            s["accept_rate"] = (
                s["accepted"] / s["count"]
                if s["count"] else 0
            )

        return dict(stats)

    # =========================================================
    # Strength effectiveness
    # =========================================================
    def _compute_strength_stats(self, cases):

        stats = defaultdict(lambda: {
            "count": 0,
            "delta_sum": 0.0,
            "accepted": 0
        })

        for case in cases:
            for step in case["steps"]:

                action = step["type"]
                strength = step.get("strength", "default")

                key = f"{action}:{strength}"

                stats[key]["count"] += 1
                stats[key]["delta_sum"] += step.get("delta_similarity") or 0

                if step.get("accepted"):
                    stats[key]["accepted"] += 1

        result = {}

        for k, s in stats.items():
            result[k] = {
                "avg_delta": s["delta_sum"] / s["count"],
                "accept_rate": s["accepted"] / s["count"],
                "count": s["count"]
            }

        return result

    # =========================================================
    # Ordering learning
    # =========================================================
    def _compute_order_stats(self, cases):

        order_gain = defaultdict(float)
        order_count = defaultdict(int)

        for case in cases:

            steps = case["steps"]

            for i in range(len(steps) - 1):
                a = steps[i]["type"]
                b = steps[i + 1]["type"]

                pair = f"{a}->{b}"
                gain = steps[i + 1].get("delta_similarity") or 0

                order_gain[pair] += gain
                order_count[pair] += 1

        result = {}

        for pair in order_gain:
            result[pair] = {
                "avg_gain": order_gain[pair] / order_count[pair],
                "count": order_count[pair]
            }

        return result

    # =========================================================
    # Priority tuning
    # =========================================================
    def _recommend_priorities(self, stats):

        ordered = sorted(
            stats.items(),
            key=lambda x: x[1]["avg_delta"],
            reverse=True
        )

        priorities = {}
        p = 1

        for action, _ in ordered:
            priorities[action] = p
            p += 1

        return priorities

    # =========================================================
    # Detect harmful models
    # =========================================================
    def _detect_bad_actions(self, stats):

        bad = []

        for action, s in stats.items():
            if s["avg_delta"] < 0 and s["accept_rate"] < 0.4:
                bad.append(action)

        return bad
