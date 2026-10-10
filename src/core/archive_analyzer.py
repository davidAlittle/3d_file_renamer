# src/core/archive_analyzer.py
from pathlib import Path
import zipfile
import rarfile
import py7zr
from typing import Dict, List, Optional
import json
import hashlib
import logging
import re
from datetime import datetime
from .rules_manager import RulesManager

class ArchiveAnalyzer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ArchiveAnalyzer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.supported_formats = {
            '.zip': self._analyze_zip,
            '.rar': self._analyze_rar,
            '.7z': self._analyze_7z
        }
        self.rules_manager = RulesManager()
        self._initialized = True

    def analyze_archive(self, filepath: Path) -> Dict:
        """Main analysis method"""
        logging.debug(f"Starting archive analysis for: {filepath}")
        result = {
            'filepath': str(filepath),
            'filename': filepath.name,
            'extension': filepath.suffix.lower(),
            'size': filepath.stat().st_size,
            'suggested_category': None,
            'suggested_tags': [],
            'contains_stls': False,
            'contains_docs': False,
            'file_list': [],
            'error': None,
            'analysis_date': datetime.now().isoformat()
        }
        
        try:
            if result['extension'] not in self.supported_formats:
                msg = f"Unsupported archive format: {result['extension']}"
                logging.debug(msg)
                result['error'] = msg
                return result

            # Analyze archive contents
            logging.debug("Analyzing archive contents...")
            archive_info = self.supported_formats[result['extension']](filepath)
            logging.debug(f"Archive info: {archive_info}")
            result.update(archive_info)

            # Analyze filename using rules
            logging.debug("Analyzing filename...")
            name_analysis = self._analyze_filename(filepath.stem)
            logging.debug(f"Name analysis: {name_analysis}")
            result.update(name_analysis)

            # Build a cleaned base name for the suggested rename
            result['base_name'] = self._clean_base_name(filepath.stem, result)

            # Generate suggestions based on rules and content
            logging.debug("Generating suggestions...")
            self._generate_suggestions(result)
            logging.debug(f"Final analysis result: {result}")

        except Exception as e:
            error_msg = f"Error analyzing archive: {str(e)}"
            logging.error(error_msg, exc_info=True)
            result['error'] = error_msg

        return result

    def _analyze_filename(self, filename: str) -> Dict:
        """Analyze filename using rules"""
        return self.rules_manager.analyze_name(filename)

    def _clean_base_name(self, name: str, matches: Dict) -> str:
        """Strip matched rule patterns from an already extension-free name"""
        if version := matches.get('version'):
            name = re.sub(rf"[vV]{re.escape(version)}", "", name)

        for spec in matches.get('technical', []):
            name = name.replace(spec, "")

        for creator in matches.get('creators', []):
            patterns = self.rules_manager.rules['creators'][creator['name']]['patterns']
            for pattern in patterns:
                name = re.sub(re.escape(pattern), "", name, flags=re.IGNORECASE)

        # NSFW/SFW markers are represented by tags instead
        name = re.sub(
            r"(?<![A-Za-z0-9])(nsfw|sfw)(?![A-Za-z0-9])", "", name, flags=re.IGNORECASE
        )

        # Normalize separators and whitespace
        name = name.replace('_', ' ').replace('-', ' ')
        return ' '.join(name.split())

    def _generate_suggestions(self, result: Dict):
        """Generate suggestions using rules and content analysis"""
        # Special pattern overrides win, otherwise use the highest priority match
        category = None
        for special in result.get('special_patterns', []):
            if special.get('override_category'):
                category = special['type']
                break

        if not category and result.get('categories'):
            category = result['categories'][0]['category']

        if not category:
            category = self.rules_manager.get_default_category()

        result['suggested_category'] = category

        # Combine all potential tags
        tags = set(result.get('tags', []))
        
        # Add technical tags based on content
        if result['contains_stls']:
            tags.add('STL')
        if result['contains_docs']:
            tags.add('DOCUMENTED')

        # Add categories related to any matched franchise
        for franchise in result.get('franchises', []):
            for related in franchise.get('related_categories', []):
                if related != category:
                    tags.add(related)

        # Add any creator tags
        for creator in result.get('creators', []):
            if creator.get('always_tag'):
                tags.add(creator['name'])

        result['suggested_tags'] = sorted(tags)

    def _analyze_zip(self, filepath: Path) -> Dict:
        """Analyze ZIP archive contents"""
        info = {'file_list': [], 'contains_stls': False, 'contains_docs': False}
        
        try:
            with zipfile.ZipFile(filepath) as zf:
                info['file_list'] = zf.namelist()
                
                for filename in info['file_list']:
                    lower_name = filename.lower()
                    if lower_name.endswith('.stl'):
                        info['contains_stls'] = True
                    if lower_name.endswith(('.txt', '.pdf', '.md')):
                        info['contains_docs'] = True
                        
                if zf.comment:
                    info['archive_comment'] = zf.comment.decode('utf-8', 'ignore')
        except Exception as e:
            info['error'] = f"ZIP analysis error: {str(e)}"
            logging.error(f"Error analyzing ZIP {filepath}: {e}")
            
        return info

    def _analyze_rar(self, filepath: Path) -> Dict:
        """Analyze RAR archive contents"""
        info = {'file_list': [], 'contains_stls': False, 'contains_docs': False}
        
        try:
            with rarfile.RarFile(filepath) as rf:
                info['file_list'] = rf.namelist()
                
                for filename in info['file_list']:
                    lower_name = filename.lower()
                    if lower_name.endswith('.stl'):
                        info['contains_stls'] = True
                    if lower_name.endswith(('.txt', '.pdf', '.md')):
                        info['contains_docs'] = True
                        
                if rf.comment:
                    info['archive_comment'] = rf.comment
        except Exception as e:
            info['error'] = f"RAR analysis error: {str(e)}"
            logging.error(f"Error analyzing RAR {filepath}: {e}")
            
        return info

    def _analyze_7z(self, filepath: Path) -> Dict:
        """Analyze 7Z archive contents"""
        info = {'file_list': [], 'contains_stls': False, 'contains_docs': False}
        
        try:
            with py7zr.SevenZipFile(filepath) as sz:
                info['file_list'] = sz.getnames()
                
                for filename in info['file_list']:
                    lower_name = filename.lower()
                    if lower_name.endswith('.stl'):
                        info['contains_stls'] = True
                    if lower_name.endswith(('.txt', '.pdf', '.md')):
                        info['contains_docs'] = True
        except Exception as e:
            info['error'] = f"7Z analysis error: {str(e)}"
            logging.error(f"Error analyzing 7Z {filepath}: {e}")
            
        return info