# utils/paths.py
import os
from pathlib import Path

# Root of the project (2 levels up from this file)
ROOT_DIR = Path(__file__).resolve().parents[1]

# Central weights directory
WEIGHTS_DIR = ROOT_DIR / "weights"

def get_weight_path(model_name: str, filename: str) -> Path:
    """
    Returns the path to a given model's weights file.
    :param model_name: subfolder inside weights/ (e.g. 'retinaface', 'arcface')
    :param filename: name of the weight file (e.g. 'retinaface.h5')
    """
    path = WEIGHTS_DIR / model_name / filename
    if not path.exists():
        raise FileNotFoundError(f"Weight file not found: {path}")
    return path
