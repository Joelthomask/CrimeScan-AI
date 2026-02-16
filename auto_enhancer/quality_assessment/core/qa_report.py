# auto_enhancer/quality_assessment/core/qa_report.py

from datetime import datetime


class QAReport:
    """
    Unified factual quality report (NO decisions, NO intelligence).

    Acts as the single contract between:
    QA → Intelligence → AutoEnhancer → UI → Reports
    """

    def __init__(self, image_path: str):
        self.image_path = image_path
        self.timestamp = datetime.now().isoformat()

        self.objective = {}
        self.faces = {}
        self.perceptual = {}

    # ----------------------------
    # Data setters
    # ----------------------------

    def set_objective(self, data: dict):
        self.objective = data or {}

    def set_faces(self, data: dict):
        self.faces = data or {}

    def set_perceptual(self, data: dict):
        self.perceptual = data or {}

    # ----------------------------
    # Serialization
    # ----------------------------

    def to_dict(self):
        return {
            "meta": {
                "image_path": self.image_path,
                "timestamp": self.timestamp
            },
            "objective": self.objective,
            "faces": self.faces,
            "perceptual": self.perceptual
        }

    # =========================================================
    # PROFESSIONAL FORENSIC CONSOLE REPORT
    # =========================================================

    def to_console_report(self, title="QA"):

        lines = []
        lines.append("")
        lines.append("============================================================")
        lines.append(f"                {title} QUALITY ASSESSMENT REPORT")
        lines.append("============================================================")

        # ================= OBJECTIVE =================
        obj = self.objective or {}

        blur = obj.get("blur", {})
        bright = obj.get("brightness", {})
        contrast = obj.get("contrast", {})
        noise = obj.get("noise", {})
        res = obj.get("resolution", {})

        lines.append("[OBJECTIVE FACTS]")
        lines.append(f"     • Blur variance     : {round(blur.get('variance', 0.0), 2)}")
        lines.append(f"     • Brightness mean   : {round(bright.get('mean', 0.0), 2)}")
        lines.append(f"     • Brightness std    : {round(bright.get('std', 0.0), 2)}")
        lines.append(f"     • Contrast std      : {round(contrast.get('std', 0.0), 2)}")
        lines.append(f"     • Contrast spread   : {round(contrast.get('spread', 0.0), 2)}")
        lines.append(f"     • Noise estimate    : {round(noise.get('noise', 0.0), 2)}")
        lines.append(f"     • Edge density      : {round(noise.get('edge_density', 0.0), 4)}")
        lines.append(f"     • Resolution        : {res.get('width',0)} x {res.get('height',0)}")
        lines.append("")

        # ================= FACES =================
        face = self.faces or {}
        lines.append("[FACE FACTS]")
        lines.append(f"     • Face detected     : {face.get('detected', False)}")
        lines.append(f"     • Face count        : {face.get('count', 0)}")

        largest = face.get("largest_face")
        if largest:
            lines.append(f"     • Largest face area : {largest.get('area_ratio', 0)}")
            lines.append(f"     • Face blur var     : {largest.get('blur_variance', 0)}")
            lines.append(f"     • Face brightness   : {largest.get('brightness', 0)}")
            lines.append(f"     • Masked            : {largest.get('masked', False)}")
        # ================= POSE =================
        pose = face.get("pose", {})
        if pose:
            lines.append("")
            lines.append("[POSE FACTS]")
            lines.append(f"     • Pose OK ratio     : {pose.get('pose_ok_ratio')}")

            if pose.get("worst_yaw") is not None:
                lines.append(f"     • Worst yaw        : {pose.get('worst_yaw')}°")
                lines.append(f"     • Worst pitch      : {pose.get('worst_pitch')}°")
                lines.append(f"     • Worst roll       : {pose.get('worst_roll')}°")

            for f in pose.get("faces", []):
                lines.append(
                    f"     • Face {f['face_id']} → "
                    f"yaw={f['yaw']}°, pitch={f['pitch']}°, roll={f['roll']}° | "
                    f"{'OK' if f['status'] else 'BAD'}"
                )

        lines.append("")

        # ================= PERCEPTUAL =================
        perc = self.perceptual or {}
        lines.append("[PERCEPTUAL FACTS]")
        for k, v in perc.items():
            try:
                lines.append(f"     • {k:<18}: {round(float(v), 4)}")
            except:
                lines.append(f"     • {k:<18}: {v}")

        lines.append("======================================================================")

        return "\n".join(lines)
