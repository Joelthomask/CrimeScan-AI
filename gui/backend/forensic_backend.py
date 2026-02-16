from PyQt5.QtCore import QObject, pyqtSignal, QThread
import time
from utils.logger import get_logger

from auto_enhancer.auto_enhancer import AutoEnhancer


# ============================================================
# Worker Thread (runs heavy AI safely)
# ============================================================

class ForensicWorker(QThread):

    qc_ready = pyqtSignal(dict, dict, list)

    step_update = pyqtSignal(str, str)     # module_name, image_path
    finished = pyqtSignal(str)             # final_image_path
    status = pyqtSignal(str)
    error = pyqtSignal(str)

    # 🔥 NEW: rollback signal (dict = GuardDecision)
    rollback_detected = pyqtSignal(str, dict)

    def __init__(self, image_path: str, device="cuda", mode="forensic"):
        super().__init__()
        self.image_path = image_path
        self.device = device
        self.mode = mode

        self.engine = AutoEnhancer(device=device, mode=mode)

        self._allow_continue = False
        self._stopped = False

    # --------------------------------------------------------
    # Thread main
    # --------------------------------------------------------
    def is_stopped(self):
        return self._stopped

    def run(self):
        try:
            self._allow_continue = False
            self._stopped = False

            # ==============================
            # PHASE 1 — QC ONLY
            # ==============================
            self.status.emit("")

            qc_report, intelligence_preview = self.engine.run_qc_stage(self.image_path)

            # 🔥 DO NOT TOUCH INTELLIGENCE DICT
            decision = intelligence_preview.get("decision", {}) or {}
            plan = decision.get("recommended_actions", []) or []

            # UI-friendly list only (does not affect semantics)
            self.planned_steps = [
                p.get("type")
                for p in plan if isinstance(p, dict)
            ]

            # 🔥 PASS FULL INTELLIGENCE UNCHANGED
            self.qc_ready.emit(
                qc_report,
                intelligence_preview,
                self.planned_steps
            )


            # ==============================
            # WAIT FOR UI CONFIRMATION
            # ==============================
            self.status.emit("Waiting for User confirmation TO CONTINUE")

            while not self._allow_continue and not self._stopped:
                time.sleep(0.15)

            if self._stopped:
                return

            # ==============================
            # PHASE 2 — FULL PIPELINE
            # ==============================
            self.status.emit("Starting automatic forensic enhancement...")

            final_path = self.engine.run_full_pipeline(
                self.image_path,
                step_callback=self._emit_step
            )

            if not self._stopped:
                self.finished.emit(final_path)

        except Exception as e:
            self.error.emit(str(e))

    # --------------------------------------------------------
    # Controls
    # --------------------------------------------------------

    def allow_continue(self):
        self._allow_continue = True

    def stop(self):
        self._stopped = True
        self._allow_continue = False

    # --------------------------------------------------------
    # Enhancement callback bridge
    # --------------------------------------------------------

    def _emit_step(self, module_name, image_path):
        if self._stopped:
            return

        # UI update signal only
        self.step_update.emit(module_name, image_path)

        if hasattr(self.engine, "last_guard_result"):
            res = self.engine.last_guard_result
            if res and not res.get("accepted", True):
                self.rollback_detected.emit(module_name, res)




# ============================================================
# Public backend used by UI
# ============================================================

class ForensicBackend(QObject):

    qc_ready = pyqtSignal(dict, dict, list)

    step_update = pyqtSignal(str, str)
    finished = pyqtSignal(str)
    status = pyqtSignal(str)
    error = pyqtSignal(str)

    # 🔥 EXPOSED TO UI
    rollback_detected = pyqtSignal(str, dict)

    def __init__(self, device="cuda", mode="forensic"):
        super().__init__()
        self.device = device
        self.mode = mode
        self.worker = None
        self._pipeline_running = False

        self.LOGGER = get_logger()
        self.LOGGER.info("[BACKEND] Backend initialized")

        self.forensic_guard_enabled = True
        self.adaptive_learning_enabled = False

        # last guard decision (UI reads this)
        self.last_guard_result = None

    # --------------------------------------------------------
    # Mode toggles
    # --------------------------------------------------------

    def set_forensic_guard(self, enabled: bool):
        self.forensic_guard_enabled = enabled
        self.LOGGER.info(f"[BACKEND] Guard enabled → {enabled}")

        if not enabled:
            self.adaptive_learning_enabled = False
            self.LOGGER.info("[BACKEND] Adaptive learner forced OFF")

    def set_adaptive_learning(self, enabled: bool):
        if enabled and not self.forensic_guard_enabled:
            self.LOGGER.warning("[BACKEND] Adaptive blocked: guard is OFF")
            return

        self.adaptive_learning_enabled = enabled
        self.LOGGER.info(f"[BACKEND] Adaptive learner → {enabled}")

    # --------------------------------------------------------
    # Case lifecycle
    # --------------------------------------------------------

    def start_case(self, image_path: str):
        self._pipeline_running = False

        if self.worker and self.worker.isRunning():
            self.worker.stop()

        self.worker = ForensicWorker(
            image_path=image_path,
            device=self.device,
            mode=self.mode
        )

        # 🔒 PASS MODES INTO ENGINE
        self.worker.engine.forensic_guard_enabled = self.forensic_guard_enabled
        self.worker.engine.adaptive_learning_enabled = self.adaptive_learning_enabled

        # ---------- SIGNAL BRIDGE ----------
        self.worker.qc_ready.connect(self._forward_qc)

        self.worker.step_update.connect(self.step_update.emit)
        self.worker.finished.connect(self.finished.emit)
        self.worker.finished.connect(self._on_finished)

        self.worker.status.connect(self.status.emit)
        self.worker.error.connect(self.error.emit)

        # 🔥 ROLLBACK BRIDGE
        self.worker.rollback_detected.connect(self._on_rollback)

        self.worker.start()
    def _on_finished(self, _):
        self._pipeline_running = False

    # --------------------------------------------------------
    # Internal rollback handler
    # --------------------------------------------------------

    def _on_rollback(self, module, data):
        self.last_guard_result = data
        self.rollback_detected.emit(module, data)


    # --------------------------------------------------------
    # Continue after QC
    # --------------------------------------------------------

    def continue_pipeline(self):

        if self._pipeline_running:
            return

        self._pipeline_running = True

        if self.worker:
            self.worker.allow_continue()


    # --------------------------------------------------------
    # Emergency stop
    # --------------------------------------------------------

    def stop(self):

        if not self.worker:
            return

        self.LOGGER.info("[BACKEND] HARD STOP requested")

        try:
            # 🔥 tell worker to stop logic
            self.worker.stop()

            # 🔥 kill QThread event loop
            self.worker.quit()

            # 🔥 wait for actual termination
            self.worker.wait(2000)

        except Exception as e:
            self.LOGGER.warning(f"[BACKEND] Stop error: {e}")

        # 🔥 DISCONNECT signals to prevent ghost UI triggers
        try:
            self.worker.qc_ready.disconnect()
            self.worker.step_update.disconnect()
            self.worker.finished.disconnect()
            self.worker.status.disconnect()
            self.worker.error.disconnect()
            self.worker.rollback_detected.disconnect()
        except:
            pass

        self.worker = None
        self._pipeline_running = False

    def _forward_qc(self, qa, intel, steps):
        # 🔥 ensure full dict is forwarded untouched
        self.qc_ready.emit(qa, intel, steps)
