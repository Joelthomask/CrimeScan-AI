import os
from PyQt5.QtWidgets import QMessageBox
from database.sqlite.criminals_db import DatabaseHandler

class DatabaseManagerBackend:
    def __init__(self):
        self.db = DatabaseHandler()


    def delete_criminal(self, parent, name: str):
        if not name.strip():
            return False
        success = self.db.delete_criminal(name.strip())
        if success:
            QMessageBox.information(parent, "Deleted", f"Criminal '{name}' deleted successfully.")
        else:
            QMessageBox.warning(parent, "Not Found", f"No criminal found with name '{name}'.")
        return success

    def clear_all_criminals(self, parent):
        confirm = QMessageBox.question(
            parent, "Clear Database",
            "Are you sure you want to delete ALL criminals?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.db.clear_all_criminals()
            QMessageBox.information(parent, "Cleared", "All criminals have been removed.")
            return True
        return False
    def load_criminals(self):
        criminals = self.db.fetch_all_criminals()

        if not criminals:
            return []

        return [c["name"] for c in criminals]
