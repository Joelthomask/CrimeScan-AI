import shutil
from pathlib import Path
from .temp_manager import TEMPLATE_LOG_DIR, get_active_session

def delete_logs():
    """Delete all logs in all sessions."""
    deleted = False

    if TEMPLATE_LOG_DIR.exists():
        for session in TEMPLATE_LOG_DIR.iterdir():
            if session.is_dir():
                logs_dir = session / "logs"
                if logs_dir.exists():
                    shutil.rmtree(logs_dir)
                    deleted = True
    return deleted


def delete_temp_sessions():
    """Delete all temp subfolders in all sessions."""
    if TEMPLATE_LOG_DIR.exists():
        for session in TEMPLATE_LOG_DIR.iterdir():
            if session.is_dir():
                temp_dir = session / "temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    temp_dir.mkdir(parents=True, exist_ok=True)
        return True
    return False


def full_cleanup():
    """Completely wipe all temporary and log data for all sessions."""
    delete_logs()
    delete_temp_sessions()
    return True
