# src/ui/dialogs/base_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QGuiApplication

class BaseDialog(QDialog):
    """Base dialog class with standardized behaviors"""
    
    # Standard dimensions and margins
    DEFAULT_WIDTH = 600
    DEFAULT_HEIGHT = 400
    MARGIN = 8
    SPACING = 6
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        if parent:
            self.setWindowModality(Qt.WindowModal)
        
        # Set minimum size
        self.setMinimumSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        
        # Create main layout with standard margins
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        self.main_layout.setSpacing(self.SPACING)
        
        # Initialize standard content area
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(self.SPACING)
        self.main_layout.addWidget(self.content_widget)
        
        self.position_dialog()

    def position_dialog(self):
        """Position dialog relative to parent or screen center"""
        if self.parent():
            # Center on parent
            parent_geometry = self.parent().geometry()
            x = parent_geometry.center().x() - self.width() // 2
            y = parent_geometry.center().y() - self.height() // 2
            self.move(x, y)
        else:
            # Center on screen
            screen = QGuiApplication.primaryScreen()
            if screen is None:
                return
            geometry = screen.availableGeometry()
            x = geometry.center().x() - self.width() // 2
            y = geometry.center().y() - self.height() // 2
            self.move(x, y)

    def create_button_row(self, *buttons) -> QWidget:
        """Create a standardized button row"""
        button_widget = QWidget(self)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(self.SPACING)
        
        # Add stretch to push buttons right
        button_layout.addStretch()
        
        # Add buttons in order
        for button in buttons:
            button_layout.addWidget(button)
        
        return button_widget

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        # Re-center if parent exists
        if self.parent():
            self.position_dialog()

    def showEvent(self, event):
        """Handle show events"""
        super().showEvent(event)
        self.position_dialog()