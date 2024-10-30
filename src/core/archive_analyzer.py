# src/core/archive_analyzer.py
from pathlib import Path
import zipfile
import rarfile
import py7zr
from typing import Dict, List, Optional
import json
import hashlib
import logging
from .rules_manager import RulesManager


class ArchiveAnalyzer:
    def __init__(self):
        self.supported_formats = {
            '.zip': self._analyze_zip,
            '.rar': self._analyze_rar,
            '.7z': self._analyze_7z
        }
        self.rules_manager = RulesManager()

    def analyze_archive(self, filepath: Path) -> Dict:
        """Main analysis method"""
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
            'error': None
        }

        # Check if format is supported
        if result['extension'] not in self.supported_formats:
            result['error'] = f"Unsupported archive format: {result['extension']}"
            return result

        try:
            # Analyze archive contents
            archive_info = self.supported_formats[result['extension']](filepath)
            result.update(archive_info)

            # Analyze filename for patterns using rules
            name_analysis = self._analyze_filename(filepath.stem)
            result.update(name_analysis)

            # Generate suggestions based on rules
            self._generate_suggestions(result)

        except Exception as e:
            result['error'] = str(e)
            logging.error(f"Error analyzing archive {filepath}: {e}")

        return result

    # These methods remain unchanged as they handle archive operations
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

    def _analyze_filename(self, filename: str) -> Dict:
        """Analyze filename using rules"""
        result = {
            'detected_patterns': [],
            'potential_tags': []
        }
        
        # Use rules manager to analyze filename
        rule_matches = self.rules_manager.test_name(filename)
        
        # Add matching categories
        if rule_matches['categories']:
            result['detected_patterns'].extend(
                match['category'] for match in rule_matches['categories']
            )
        
        # Add NSFW status
        if rule_matches['nsfw_status']['is_nsfw']:
            result['potential_tags'].append('NSFW')
        
        # Add special pattern tags
        result['potential_tags'].extend(rule_matches['tags'])
        
        # Add creator tags
        for creator in rule_matches['creators']:
            if creator.get('always_tag'):
                result['potential_tags'].append(creator['name'])
                
        return result

    def _generate_suggestions(self, result: Dict):
        """Generate final category and tag suggestions using rules"""
        # Use detected patterns to set category
        if result['detected_patterns']:
            result['suggested_category'] = result['detected_patterns'][0]
        else:
            result['suggested_category'] = 'MISC'
            
        # Add potential tags from filename analysis
        if result.get('potential_tags'):
            result['suggested_tags'].extend(result['potential_tags'])
            
        # Add technical tags based on content
        if result['contains_stls']:
            result['suggested_tags'].append('STL')
        if result['contains_docs']:
            result['suggested_tags'].append('DOCUMENTED')