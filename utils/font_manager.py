# utils/font_manager.py
from PyQt5.QtGui import QFont

FONTS = {}

def set_fonts(font_dict: dict):
    """Called ONCE from app.py after QApplication"""
    global FONTS
    FONTS = font_dict

def get_font(name: str) -> QFont:
    return FONTS.get(name, QFont())
