# utils/logger.py

import logging
import sys
from pathlib import Path
from datetime import datetime
import warnings

_LOGGER = None


# ============================================================
# INITIALIZATION
# ============================================================

def init_logger(session_root: Path):
    """
    Initialize global CrimeScan logger.
    Call ONCE at app startup.
    """
    global _LOGGER

    if _LOGGER is not None:
        return _LOGGER

    # -------- Silence noisy libraries --------
    warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
    warnings.filterwarnings("ignore", message="No faces were detected.")

    logging.getLogger("torch").setLevel(logging.ERROR)
    logging.getLogger("torchvision").setLevel(logging.ERROR)
    logging.getLogger("PIL").setLevel(logging.ERROR)

    # -------- Log folder --------
    log_dir = session_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "session.log"
    from utils.temp_manager import _CURRENT_SESSION
    if _CURRENT_SESSION is not None:
        _CURRENT_SESSION["log_path"] = str(log_file)

    # -------- Logger --------
    logger = logging.getLogger("CrimeScanAI")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] %(message)s",
            datefmt="%H:%M:%S"
        )

        # Console
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # -------- Session header --------
    logger.info("=" * 64)
    logger.info("[SYSTEM] NEW FORENSIC SESSION STARTED")
    logger.info(f"[SYSTEM] Root : {session_root}")
    logger.info(f"[SYSTEM] Log  : {log_file}")
    logger.info(f"[SYSTEM] Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 64)
    logger.info("")

    # -------- Global crash capture --------
    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("[CRASH] Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = handle_exception

    _LOGGER = logger
    return logger


# ============================================================
# ACCESS
# ============================================================

def get_logger():
    if _LOGGER is None:
        raise RuntimeError("Logger not initialized. Call init_logger() first.")
    return _LOGGER


# ============================================================
# STRUCTURED EVENT API  🔥
# ============================================================

def log_event(layer: str, message: str, level: str = "INFO"):
    """
    Universal structured logger.

    layer examples:
    SYSTEM, QA, INTELLIGENCE, AUTO-ENHANCER, DEBLUR, DENOISE, UI, ENGINE

    level:
    INFO | WARNING | ERROR | CRITICAL
    """

    logger = get_logger()
    tag = f"[{layer.upper()}]"

    msg = f"{tag} {message}"

    level = level.upper()

    if level == "INFO":
        logger.info(msg)
    elif level == "WARNING":
        logger.warning(msg)
    elif level == "ERROR":
        logger.error(msg)
    elif level == "CRITICAL":
        logger.critical(msg)
    else:
        logger.info(msg)


# ============================================================
# OPTIONAL HELPERS (for later forensic reports)
# ============================================================

def log_stage(stage: str):
    log_event("ENGINE", f"{'-'*10} {stage} {'-'*10}")


def log_decision(policy: str, decision: dict):
    log_event("INTELLIGENCE", f"Policy → {policy}")
    for k, v in decision.items():
        log_event("INTELLIGENCE", f"{k} = {v}")
