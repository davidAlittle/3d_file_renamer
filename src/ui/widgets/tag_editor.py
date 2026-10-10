# src/ui/widgets/tag_editor.py
import logging
from typing import Dict, Set, List, Optional
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QFrame,
    QScrollArea,
    QLineEdit,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal

@dataclass
class TagData:
    """Data structure for tag information"""
    text: str
    category: str
    removable: bool = True

class Tag(QFrame):
    """Individual tag widget"""
    # Signals
    removed = Signal(str)  # Emitted when tag is removed
    clicked = Signal(str)  # Emitted when tag is clicked
    
    # Styling
    STYLE_TEMPLATE = """
        QFrame {
            background: %s;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin: 1px;
        }
        QPushButton {
            border: none;
            border-radius: 2px;
            background: transparent;
            padding: 2px;
        }
        QPushButton:hover {
            background: rgba(0, 0, 0, 0.1);
        }
        QLabel {
            color: %s;
            padding: 2px 4px;
        }
    """
    
    # Color schemes for different categories
    COLORS = {
        'Content': ('#e3f2fd', '#1976d2'),    # Light blue
        'Technical': ('#f3e5f5', '#7b1fa2'),  # Light purple
        'Creator': ('#e8f5e9', '#388e3c'),    # Light green
        'Status': ('#fff3e0', '#f57c00'),     # Light orange
        'default': ('#f5f5f5', '#616161')     # Light gray
    }

    def __init__(self, text: str, category: str, removable: bool = True, parent=None):
        super().__init__(parent)
        self.text = text
        self.category = category
        self.removable = removable
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the tag UI"""
        try:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(4, 2, 4, 2)
            layout.setSpacing(4)
            
            # Tag text with category
            label = QLabel(f"{self.category}:{self.text}")
            layout.addWidget(label)
            
            # Remove button if tag is removable
            if self.removable:
                remove_btn = QPushButton("×")
                remove_btn.setFixedSize(16, 16)
                remove_btn.clicked.connect(lambda: self.removed.emit(self.text))
                layout.addWidget(remove_btn)
            
            # Apply style based on category
            bg_color, text_color = self.COLORS.get(
                self.category, 
                self.COLORS['default']
            )
            self.setStyleSheet(self.STYLE_TEMPLATE % (bg_color, text_color))
            
            # Make tag clickable
            self.setCursor(Qt.PointingHandCursor)
            
        except Exception as e:
            logging.error(f"Error setting up tag UI: {e}", exc_info=True)
            
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        try:
            if event.button() == Qt.LeftButton:
                self.clicked.emit(self.text)
            super().mousePressEvent(event)
        except Exception as e:
            logging.error(f"Error handling tag click: {e}", exc_info=True)
class TagEditor(QWidget):
    """Widget for managing tags with categories and suggestions"""
    
    # Signal emitted when tags are modified
    tagsChanged = Signal(list)
    
    # Default categories and their tags
    CATEGORIES = {
        'Content': ['NSFW', 'SFW', 'MULTI', 'ANIME', 'GAME'],
        'Technical': ['PiP', 'MULTI_FORMAT', 'NO_SUPPORT', 'STL', 'DOCUMENTED'],
        'Creator': ['HEX3D', 'TORRIDA', 'FLEXISTL'],
        'Status': ['DUPE', 'RENAMED', 'VERIFIED']
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tags: Dict[str, TagData] = {}
        
        # UI spacing constants
        self.SPACING = 6
        self.MARGIN = 8
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the tag editor UI"""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
            layout.setSpacing(self.SPACING)
            
            # Add tag section
            add_section = QHBoxLayout()
            add_section.setSpacing(self.SPACING)
            
            # Category selector
            self.category_combo = QComboBox()
            self.category_combo.addItems(self.CATEGORIES.keys())
            self.category_combo.currentTextChanged.connect(self.update_tag_suggestions)
            add_section.addWidget(self.category_combo)
            
            # Tag input/selector
            self.tag_input = QComboBox()
            self.tag_input.setEditable(True)
            self.tag_input.setInsertPolicy(QComboBox.InsertPolicy.InsertAlphabetically)
            self.update_tag_suggestions()
            add_section.addWidget(self.tag_input)
            
            # Add button
            add_btn = QPushButton("Add Tag")
            add_btn.clicked.connect(self.add_current_tag)
            add_section.addWidget(add_btn)
            
            layout.addLayout(add_section)
            
            # Tags display area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            self.tags_container = QWidget()
            self.tags_layout = QHBoxLayout(self.tags_container)
            self.tags_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.tags_layout.setSpacing(self.SPACING)
            self.tags_layout.addStretch()
            
            scroll.setWidget(self.tags_container)
            layout.addWidget(scroll)
            
        except Exception as e:
            logging.error(f"Error setting up tag editor: {e}", exc_info=True)
        
    def update_tag_suggestions(self):
        """Update tag suggestions based on selected category"""
        try:
            current_category = self.category_combo.currentText()
            self.tag_input.clear()
            self.tag_input.addItems(sorted(self.CATEGORIES[current_category]))
        except Exception as e:
            logging.error(f"Error updating tag suggestions: {e}", exc_info=True)
            
    def add_current_tag(self):
        """Add the currently selected/entered tag"""
        try:
            tag_text = self.tag_input.currentText().strip().upper()
            if tag_text and tag_text not in self.current_tags:
                category = self.category_combo.currentText()
                self.add_tag(tag_text, category)
        except Exception as e:
            logging.error(f"Error adding tag: {e}", exc_info=True)
            
    def add_tag(self, text: str, category: str, removable: bool = True):
        """Add a new tag to the editor"""
        try:
            if text not in self.current_tags:
                tag_data = TagData(text, category, removable)
                self.current_tags[text] = tag_data
                
                tag_widget = Tag(text, category, removable)
                tag_widget.removed.connect(self.remove_tag)
                tag_widget.clicked.connect(self._handle_tag_click)
                
                # Add before the stretch item
                self.tags_layout.insertWidget(
                    self.tags_layout.count() - 1, 
                    tag_widget
                )
                
                self.tagsChanged.emit(self.get_tags())
                
        except Exception as e:
            logging.error(f"Error adding tag {text}: {e}", exc_info=True)
            
    def remove_tag(self, text: str):
        """Remove a tag by its text"""
        try:
            if text in self.current_tags:
                del self.current_tags[text]
                
                # Find and remove the tag widget
                for i in range(self.tags_layout.count()):
                    widget = self.tags_layout.itemAt(i).widget()
                    if isinstance(widget, Tag) and widget.text == text:
                        widget.deleteLater()
                        break
                
                self.tagsChanged.emit(self.get_tags())
                
        except Exception as e:
            logging.error(f"Error removing tag {text}: {e}", exc_info=True)
            
    def get_tags(self) -> List[str]:
        """Get current tags in formatted string form"""
        try:
            return [f"[{text}]" for text in self.current_tags.keys()]
        except Exception as e:
            logging.error(f"Error getting tags: {e}", exc_info=True)
            return []
        
    def set_tags(self, tags: List[str]):
        """Set tags from a list of formatted strings"""
        try:
            # Clear existing tags
            self.clear_tags()
            
            # Add new tags
            for tag in tags:
                # Remove brackets if present
                tag = tag.strip('[]')
                if ':' in tag:
                    category, text = tag.split(':', 1)
                else:
                    category = self.guess_category(tag)
                    text = tag
                self.add_tag(text.strip(), category.strip())
                
        except Exception as e:
            logging.error(f"Error setting tags: {e}", exc_info=True)
            
    def guess_category(self, tag: str) -> str:
        """Try to guess the appropriate category for a tag"""
        try:
            for category, tags in self.CATEGORIES.items():
                if tag in tags:
                    return category
            return 'Content'  # Default category
        except Exception as e:
            logging.error(f"Error guessing category for {tag}: {e}", exc_info=True)
            return 'Content'
        
    def clear_tags(self):
        """Remove all tags"""
        try:
            self.current_tags.clear()
            # Remove all tag widgets while keeping the stretch item
            while self.tags_layout.count() > 1:  
                widget = self.tags_layout.itemAt(0).widget()
                if widget:
                    widget.deleteLater()
                self.tags_layout.takeAt(0)
            self.tagsChanged.emit([])
        except Exception as e:
            logging.error(f"Error clearing tags: {e}", exc_info=True)
            
    def _handle_tag_click(self, text: str):
        """Handle tag click events"""
        try:
            if text in self.current_tags:
                tag_data = self.current_tags[text]
                # Find and select the category
                self.category_combo.setCurrentText(tag_data.category)
                # Set the tag text in the input
                self.tag_input.setCurrentText(text)
        except Exception as e:
            logging.error(f"Error handling tag click: {e}", exc_info=True) 