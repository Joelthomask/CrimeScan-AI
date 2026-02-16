"""
Production Log Parser
----------------------
Extracts structured forensic session data for adaptive learner.

Extracted:
• Case metadata
• Baseline recognition
• Quality scores
• Intelligence decisions
• Enhancement steps
• Final summary

Robust against:
• Partial logs
• Errors in between
• Missing sections
"""

import os
import re
from utils.logger import get_logger


class LogParser:
    def __init__(self):
        self.log = get_logger()

    # =========================================================
    # Public API
    # =========================================================
    def parse(self, log_path: str) -> dict:

        if not os.path.exists(log_path):
            self.log.warning("[LEARNER] LogParser → log not found")
            return {}

        self.log.info(f"[LEARNER] Parsing log → {log_path}")

        lines = self._load_lines(log_path)

        case_id = self._extract_case_id(lines)

        data = {
            "case_id": case_id,
            "raw_log_path": log_path,

            "baseline": {},
            "quality_scores": {},
            "intelligence": {},
            "steps": [],
            "final_summary": {},
        }

        data["baseline"] = self._extract_baseline(lines)
        data["quality_scores"] = self._extract_quality_scores(lines)
        data["intelligence"] = self._extract_intelligence(lines)
        data["steps"] = self._extract_steps(lines)
        data["final_summary"] = self._extract_final_summary(lines)

        self.log.info("[LEARNER] LogParser completed")

        return data

    # =========================================================
    # File loading
    # =========================================================
    def _load_lines(self, log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.readlines()
        except Exception as e:
            self.log.warning(f"[LEARNER] Failed reading log: {e}")
            return []

    # =========================================================
    # Case ID
    # =========================================================
    def _extract_case_id(self, lines):
        for line in lines:
            if "[CASE] Started" in line:
                tokens = line.strip().split()
                for t in tokens:
                    if t.startswith("CASE_"):
                        return t
        return "UNKNOWN_CASE"

    # =========================================================
    # Baseline recognition
    # =========================================================
    def _extract_baseline(self, lines):
        result = {}

        for line in lines:

            if self._contains(line, "Baseline similarity"):
                val = self._extract_float(line)
                if val is not None:
                    result["similarity"] = val

            elif self._contains(line, "Baseline score"):
                val = self._extract_float(line)
                if val is not None:
                    result["score"] = val

        return result

    # =========================================================
    # Quality scores
    # =========================================================
    def _extract_quality_scores(self, lines):

        scores = {}
        capture = False

        for line in lines:
            if "---- QUALITY SCORES ----" in line:
                capture = True
                continue

            if capture:
                if "---- FACE FACTS ----" in line:
                    break

                parsed = self._parse_score_line(line)
                if parsed:
                    k, v = parsed
                    scores[k] = v

        return scores

    def _parse_score_line(self, line):
        try:
            if ":" not in line:
                return None

            key = line.split("]")[-1].split(":")[0].strip()

            value = self._extract_float(line)
            if value is None:
                return None

            key = key.lower().replace(" ", "_")
            return key, value

        except:
            return None


    # =========================================================
    # Intelligence decisions
    # =========================================================
    def _extract_intelligence(self, lines):

        intel = {"actions": []}

        for i, line in enumerate(lines):

            if "Risk level" in line:
                m = re.search(r"Risk level\s*:\s*([A-Z_]+)", line, re.IGNORECASE)
                if m:
                    intel["risk_level"] = m.group(1).upper()



            elif "Confidence" in line:
                intel["confidence"] = self._extract_float(line)

            elif "[INTELLIGENCE]" in line and "Type" in line:
                action = {
                    "type": line.split(":")[-1].strip()
                }

                # Look ahead for priority/strength
                for j in range(i + 1, min(i + 5, len(lines))):
                    if "Strength" in lines[j]:
                        val = lines[j].split(":")[-1].strip()
                        val = re.sub(r"[^a-z]", "", val.lower())
                        action["strength"] = val

                    if "Priority" in lines[j]:
                        action["priority"] = self._extract_int(lines[j])

                intel["actions"].append(action)

        return intel

    # =========================================================
    # Enhancement step extraction
    # =========================================================
    def _extract_steps(self, lines):

        steps = []
        current = None
        last_strength = None

        for line in lines:

            # --------------------------------------------------
            # Detect strength from engine logs
            # --------------------------------------------------
            if "strength=" in line.lower():
                try:
                    val = line.lower().split("strength=")[-1]
                    val = val.split()[0]
                    val = re.sub(r"[^a-z]", "", val)
                    last_strength = val
                except:
                    pass

            # --------------------------------------------------
            # Step report begins
            # --------------------------------------------------
            if "ENHANCEMENT STEP REPORT" in line:

                if current:
                    steps.append(current)

                step_name = line.split(":")[-1].strip()

                current = {
                    "type": step_name,
                    "model": None,
                    "strength": last_strength,
                    "before_similarity": None,
                    "after_similarity": None,
                    "delta_similarity": None,
                    "before_score": None,
                    "after_score": None,
                    "accepted": None,
                    "processing_time_ms": None
                }

                # reset after assignment
                last_strength = None
                continue

            if not current:
                continue

            # --------------------------------------------------
            # Model info
            # --------------------------------------------------
            if "Model used" in line:
                current["model"] = line.split(":")[-1].strip()

            elif "Before similarity" in line:
                current["before_similarity"] = self._extract_float(line)

            elif "After similarity" in line:
                current["after_similarity"] = self._extract_float(line)

            elif "Similarity change" in line:
                current["delta_similarity"] = self._extract_float(line)

            elif "Before score" in line:
                current["before_score"] = self._extract_float(line)

            elif "After score" in line:
                current["after_score"] = self._extract_float(line)

            elif "Processing time" in line:
                current["processing_time_ms"] = self._extract_float(line)

            elif "Final decision" in line:
                decision = line.split(":")[-1].strip()
                current["accepted"] = decision == "ACCEPTED"

            elif "STEP EVALUATION COMPLETE" in line:
                steps.append(current)
                current = None

        if current:
            steps.append(current)

        return steps


    # =========================================================
    # Final case summary
    # =========================================================
    def _extract_final_summary(self, lines):

        result = {}

        for line in lines:
            if "Final similarity" in line:
                result["final_similarity"] = self._extract_float(line)

            elif "Best score reached" in line:
                result["best_score"] = self._extract_float(line)

            elif "Final score" in line:
                result["final_score"] = self._extract_float(line)

            elif "Accepted actions" in line:
                result["accepted_actions"] = self._extract_int(line)

            elif "Rejected actions" in line:
                result["rejected_actions"] = self._extract_int(line)
        # fallback if summary missing
        if "final_similarity" not in result:
            for line in reversed(lines):
                if self._contains(line, "After similarity"):
                    val = self._extract_float(line)
                    if val is not None:
                        result["final_similarity"] = val
                        break

        return result

    # =========================================================
    # Utility parsing
    # =========================================================


    def _extract_float(self, line):
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", line)
        if not nums:
            return None
        return float(nums[-1])  # take LAST number
    def _extract_int(self, line):
        nums = re.findall(r"\d+", line)
        return int(nums[-1]) if nums else None
    def _contains(self, line, key):
        return key.lower() in line.lower()
