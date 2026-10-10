# src/ui/dialogs/archive_preview.py
import logging
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QWidget,
    QHeaderView
)
from PySide6.QtCore import Qt

from src.core.archive_analyzer import ArchiveAnalyzer
from .base_dialog import BaseDialog

class ArchivePreviewDialog(BaseDialog):
    """Dialog for previewing archive contents and analysis"""
    
    def __init__(self, filepath: Path, parent=None):
        super().__init__(parent)  # Call parent init first
        
        self.filepath = filepath
        self.analyzer = ArchiveAnalyzer()
        self.analysis_data: Optional[Dict] = None
        
        self.setWindowTitle(f"Archive Preview: {self.filepath.name}")
        self.resize(800, 600)
        
        # Setup UI before loading data
        self.setup_ui()
        
        # Load data after UI is ready using single-shot timer
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.load_data)

    def setup_ui(self):
        """Setup the dialog UI"""
        # Create tab widget in the base dialog's content area
        self.tab_widget = QTabWidget()
        self.content_layout.addWidget(self.tab_widget)
        
        # Contents tab
        contents_tab = QWidget()
        contents_layout = QVBoxLayout()
        contents_tab.setLayout(contents_layout)
        
        self.file_list = QTableWidget()
        self.file_list.setColumnCount(2)
        self.file_list.setHorizontalHeaderLabels(["Filename", "Size"])
        self.file_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        contents_layout.addWidget(self.file_list)
        
        # Analysis tab
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout()
        analysis_tab.setLayout(analysis_layout)
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        analysis_layout.addWidget(self.analysis_text)
        
        # Add tabs
        self.tab_widget.addTab(contents_tab, "Contents")
        self.tab_widget.addTab(analysis_tab, "Analysis")
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self.main_layout.addWidget(close_btn)

    def load_data(self):
        """Load and display archive data"""
        try:
            logging.debug(f"Loading preview data for: {self.filepath}")
            
            # Get analysis data from parent's cache if available
            parent = self.parent()
            if parent and hasattr(parent, 'file_analysis_cache'):
                logging.debug("Found parent cache")
                self.analysis_data = parent.file_analysis_cache.get(str(self.filepath))
                if self.analysis_data:
                    logging.debug("Using cached analysis data")
                else:
                    logging.debug("No cached data found")
            
            # If not in cache, analyze now
            if not self.analysis_data:
                logging.debug("Performing new analysis")
                self.analysis_data = self.analyzer.analyze_archive(self.filepath)
            
            logging.debug(f"Analysis data: {self.analysis_data}")
            
            self.display_contents()
            self.display_analysis()
            
        except Exception as e:
            logging.error(f"Error loading preview data: {e}", exc_info=True)
            self.analysis_text.setText(f"Error loading preview: {str(e)}")

    def display_contents(self):
        """Display archive contents in the file list"""
        if not self.analysis_data:
            logging.debug("No analysis data available for contents display")
            return
            
        file_list = self.analysis_data.get('file_list', [])
        logging.debug(f"Displaying {len(file_list)} files in list")
        self.file_list.setRowCount(len(file_list))
        
        for row, filename in enumerate(file_list):
            logging.debug(f"Adding file to row {row}: {filename}")
            self.file_list.setItem(row, 0, QTableWidgetItem(filename))
            # Add file size if available in the future
            self.file_list.setItem(row, 1, QTableWidgetItem(""))

    def display_analysis(self):
        """Display analysis results"""
        if not self.analysis_data:
            logging.debug("No analysis data available for analysis display")
            return
            
        logging.debug("Building analysis text")
        analysis_parts = []
        
        # Add suggested category
        if category := self.analysis_data.get('suggested_category'):
            logging.debug(f"Found category: {category}")
            analysis_parts.append(f"Suggested Category: {category}")
        
        # Add detected rules matches
        if franchises := self.analysis_data.get('franchises', []):
            logging.debug(f"Found franchises: {franchises}")
            analysis_parts.append("\nDetected Franchises:")
            analysis_parts.extend(f"- {franchise['name']}" for franchise in franchises)
        
        if creators := self.analysis_data.get('creators', []):
            logging.debug(f"Found creators: {creators}")
            analysis_parts.append("\nDetected Creators:")
            analysis_parts.extend(f"- {creator['name']}" for creator in creators)
        
        if version := self.analysis_data.get('version'):
            logging.debug(f"Found version: {version}")
            analysis_parts.append(f"\nVersion: {version}")
        
        if specs := self.analysis_data.get('technical', []):
            logging.debug(f"Found technical specs: {specs}")
            analysis_parts.append("\nTechnical Specs:")
            analysis_parts.extend(f"- {spec}" for spec in specs)
        
        # Add suggested tags
        if tags := self.analysis_data.get('suggested_tags', []):
            logging.debug(f"Found tags: {tags}")
            analysis_parts.append("\nSuggested Tags:")
            analysis_parts.extend(f"- {tag}" for tag in tags)
        
        # Add technical info
        logging.debug("Adding technical info")
        analysis_parts.append("\nTechnical Information:")
        analysis_parts.append(f"Contains STL files: {self.analysis_data.get('contains_stls', False)}")
        analysis_parts.append(f"Contains documentation: {self.analysis_data.get('contains_docs', False)}")
        
        # Add any errors
        if error := self.analysis_data.get('error'):
            logging.debug(f"Found error: {error}")
            analysis_parts.append(f"\nErrors: {error}")
        
        final_text = "\n".join(analysis_parts)
        logging.debug(f"Setting analysis text: {final_text}")
        self.analysis_text.setText(final_text)