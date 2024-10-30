# src/ui/dialogs/base_dialog.py
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt

class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        if parent:
            self.setWindowModality(Qt.WindowModal)
            # Center on parent
            self.move(parent.frameGeometry().center() - self.rect().center())