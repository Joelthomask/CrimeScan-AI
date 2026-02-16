# utils/temp_manager.py

import os
import shutil
from datetime import datetime
from pathlib import Path

# ----------------- Base Template/Log Directory ----------------- #
TEMPLATE_LOG_DIR = Path(os.getcwd()) / "templog"
ACTIVE_SESSION_FILE = TEMPLATE_LOG_DIR / "active_session.txt"

# ----------------- GLOBAL SESSION CACHE ----------------- #
_CURRENT_SESSION = None   # prevents duplicate session creation

# ----------------- Session Folders ----------------- #
SESSION_SUBFOLDERS = {
    "temp": [
        "input",
        "livewebcam/detected_faces",
        "livewebcam/recognized",
        "autoenhancement/blur",
        "autoenhancement/noise",
        "autoenhancement/brightness",
        "autoenhancement/contrast",

        "autoenhancement/resolution",
        "autoenhancement/resolution/cropped_faces",
        "autoenhancement/resolution/restored_faces",
        "autoenhancement/resolution/cmp",
        "autoenhancement/resolution/restored_imgs",

        "autoenhancement/pose",
        "autoenhancement/mask",

        "datasets/test/RealBlur_J/input",
        "datasets/test/RealBlur_J/target",
    ],
    "outputs": ["recognized_faces", "reports", "final_images"],
    "config": [],
}


# =====================================================
#  SESSION CREATION (NO LOGGER HERE)
# =====================================================
def create_session():
    """Create a new session folder structure ONCE and return all paths."""
    global _CURRENT_SESSION

    if _CURRENT_SESSION is not None:
        return _CURRENT_SESSION

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_name = f"session_{timestamp}"
    session_path = TEMPLATE_LOG_DIR / session_name

    paths = {"root": session_path, "name": session_name}

    TEMPLATE_LOG_DIR.mkdir(parents=True, exist_ok=True)
    os.makedirs(session_path, exist_ok=True)

    for main_folder, nested in SESSION_SUBFOLDERS.items():
        main_path = session_path / main_folder
        os.makedirs(main_path, exist_ok=True)
        paths[main_folder] = main_path

        for sub in nested:
            sub_path = main_path / sub
            os.makedirs(sub_path, exist_ok=True)
            key_name = f"{main_folder}_{sub.replace('/', '_')}"
            paths[key_name] = sub_path

    with open(ACTIVE_SESSION_FILE, "w") as f:
        f.write(str(session_path))

    _CURRENT_SESSION = paths
    return paths


# =====================================================
#  SESSION ACCESS (NEVER CREATES)
# =====================================================
def get_session():
    global _CURRENT_SESSION

    if _CURRENT_SESSION is not None:
        return _CURRENT_SESSION

    if ACTIVE_SESSION_FILE.exists():
        session_path = Path(ACTIVE_SESSION_FILE.read_text().strip())
        _CURRENT_SESSION = {"root": session_path, "name": session_path.name}
        return _CURRENT_SESSION

    raise RuntimeError("No active session. Call create_session() in app.py first.")


def get_active_session():
    return get_session()["root"]


# =====================================================
#  TEMP PATH HELPER (SILENT)
# =====================================================
def get_temp_subpath(subfolder: str):
    session_root = get_active_session()
    temp_folder = session_root / "temp" / subfolder
    os.makedirs(temp_folder, exist_ok=True)
    return temp_folder


# =====================================================
#  MAINTENANCE
# =====================================================
def clear_all_sessions():
    global _CURRENT_SESSION

    if TEMPLATE_LOG_DIR.exists():
        shutil.rmtree(TEMPLATE_LOG_DIR)

    os.makedirs(TEMPLATE_LOG_DIR, exist_ok=True)
    _CURRENT_SESSION = None
    return True
