# src/ui/widgets/tag_editor.py
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QFrame,
    QScrollArea,
    QLineEdit
)
from PySide6.QtCore import Qt, Signal

class Tag(QFrame):
    removed = Signal(str)
    
    def __init__(self, text: str, category: str, parent=None):
        super().__init__(parent)
        self.text = text
        self.category = category
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # Tag text
        label = QLabel(f"{self.category}:{self.text}")
        layout.addWidget(label)
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.text))
        layout.addWidget(remove_btn)
        
        # Styling
        self.setStyleSheet("""
            QFrame {
                background: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton {
                border: none;
                border-radius: 2px;
                background: transparent;
            }
            QPushButton:hover {
                background: #ddd;
            }
        """)

class TagEditor(QWidget):
    tagsChanged = Signal(list)  # Emitted when tags are modified
    
    CATEGORIES = {
        'Content': ['NSFW', 'SFW', 'MULTI', 'ANIME', 'GAME'],
        'Technical': ['PiP', 'MULTI_FORMAT', 'NO_SUPPORT'],
        'Creator': ['HEX3D', 'TORRIDA', 'FLEXISTL'],
        'Status': ['DUPE', 'RENAMED', 'VERIFIED']
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tags = {}  # {text: category}
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add tag section
        add_section = QHBoxLayout()
        
        # Category selector
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.CATEGORIES.keys())
        self.category_combo.currentTextChanged.connect(self.update_tag_suggestions)
        add_section.addWidget(self.category_combo)
        
        # Tag input/selector
        self.tag_input = QComboBox()
        self.tag_input.setEditable(True)
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
        
        self.tags_container = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setAlignment(Qt.AlignLeft)
        self.tags_layout.addStretch()
        
        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll)
        
    def update_tag_suggestions(self):
        current_category = self.category_combo.currentText()
        self.tag_input.clear()
        self.tag_input.addItems(self.CATEGORIES[current_category])
        
    def add_current_tag(self):
        tag_text = self.tag_input.currentText().strip().upper()
        if tag_text and tag_text not in self.current_tags:
            category = self.category_combo.currentText()
            self.add_tag(tag_text, category)
            
    def add_tag(self, text: str, category: str):
        if text not in self.current_tags:
            self.current_tags[text] = category
            tag_widget = Tag(text, category)
            tag_widget.removed.connect(self.remove_tag)
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, tag_widget)
            self.tagsChanged.emit(self.get_tags())
            
    def remove_tag(self, text: str):
        if text in self.current_tags:
            del self.current_tags[text]
            # Find and remove the tag widget
            for i in range(self.tags_layout.count()):
                widget = self.tags_layout.itemAt(i).widget()
                if isinstance(widget, Tag) and widget.text == text:
                    widget.deleteLater()
                    break
            self.tagsChanged.emit(self.get_tags())
            
    def get_tags(self) -> list[str]:
        return [f"[{text}]" for text in self.current_tags.keys()]
        
    def set_tags(self, tags: list[str]):
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
            self.add_tag(text, category)
            
    def guess_category(self, tag: str) -> str:
        """Try to guess the appropriate category for a tag"""
        for category, tags in self.CATEGORIES.items():
            if tag in tags:
                return category
        return 'Content'  # Default category
        
    def clear_tags(self):
        """Remove all tags"""
        self.current_tags.clear()
        # Remove all tag widgets
        while self.tags_layout.count() > 1:  # Keep the stretch item
            widget = self.tags_layout.itemAt(0).widget()
            if widget:
                widget.deleteLater()