from utils.logger import get_logger
from auto_enhancer.auto_enhancer import AutoEnhancer


class AutoImageImproverBackend:
    """
    Backend controller for Auto Image Improver.
    Orchestrates AutoEnhancer execution.
    (NO low-level logs, NO prints)
    """

    def __init__(self, device="cuda", mode="forensic"):
        self.device = device
        self.mode = mode
        self.log = get_logger()
        self.engine = AutoEnhancer(device=device, mode=mode)

    # --------------------------------------------------
    # Mode switching
    # --------------------------------------------------

    def set_mode(self, mode: str):
        if mode == self.mode:
            return

        self.mode = mode
        self.engine = AutoEnhancer(device=self.device, mode=mode)

        self.log.info(f"[AUTO-IMPROVER] Mode switched → {mode.upper()}")

    # --------------------------------------------------
    # Main pipeline entry
    # --------------------------------------------------

    def run_pipeline(self, image_path: str):

        self.log.info("[AUTO-IMPROVER] Auto Image Improver pipeline requested")
        self.log.info(f"[AUTO-IMPROVER] Mode   → {self.mode.upper()}")
        self.log.info(f"[AUTO-IMPROVER] Input  → {image_path}")

        report = self.engine.enhance(image_path)

        return {
            "before": report["meta"]["input_image"],
            "after": report["final_image"],
            "final_image": report["final_image"],
            "analysis": report.get("quality_before", {}),
            "decisions": report.get("intelligence", {}),
            "steps": report.get("steps", []),
            "report_text": (
                "AUTO IMAGE ENHANCEMENT REPORT\n"
                "──────────────────────────────\n"
                f"MODE : {self.mode.upper()}\n\n"
                "Pipeline executed successfully.\n"
                "See console logs for full forensic trace."
            )
        }
