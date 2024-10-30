# src/core/rules_manager.py
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

class RulesManager:
    def __init__(self, rules_file: str = None):
        self.rules_file = rules_file or Path(__file__).parent.parent / "rules" / "default_rules.json"
        self.rules = self.load_rules()
        
    def load_rules(self) -> Dict[str, Any]:
        """Load rules from JSON file"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Rules file not found: {self.rules_file}")

    def save_rules(self, rules: Dict[str, Any] = None):
        """Save current or provided rules to file"""
        rules = rules or self.rules
        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=4)

    def get_category_patterns(self) -> Dict[str, list]:
        """Get category patterns in simple format"""
        return {
            cat: data["patterns"] 
            for cat, data in self.rules["categories"].items()
        }

    def test_name(self, name: str) -> Dict[str, Any]:
        """Test how a name would be processed with current rules"""
        return {
            'categories': self._find_matching_categories(name),
            'franchises': self._find_matching_franchises(name),
            'creators': self._find_matching_creators(name),
            'special_patterns': self._find_special_patterns(name),
            'tags': self._find_matching_tags(name),
            'technical': self._extract_technical_specs(name),
            'version': self._extract_version(name),
            'nsfw_status': self._check_nsfw_status(name)
        }

    def _find_matching_categories(self, name: str) -> List[Dict[str, Any]]:
        """Find all matching categories for a name"""
        lower_name = name.lower()
        matches = []
        
        for category, data in self.rules["categories"].items():
            if any(pattern in lower_name for pattern in data["patterns"]):
                matches.append({
                    "category": category,
                    "priority": data["priority"],
                    "description": data["description"]
                })
        
        return sorted(matches, key=lambda x: x["priority"], reverse=True)

    def _find_matching_franchises(self, name: str) -> List[Dict[str, Any]]:
        """Find all matching franchises"""
        lower_name = name.lower()
        matches = []
        
        for franchise, data in self.rules["franchises"].items():
            if any(pattern in lower_name for pattern in data["patterns"]):
                matches.append({
                    "name": franchise,
                    "aliases": data.get("aliases", []),
                    "related_categories": data.get("related_categories", [])
                })
        
        return matches

    def _find_matching_creators(self, name: str) -> List[Dict[str, Any]]:
        """Find all matching creators"""
        lower_name = name.lower()
        matches = []
        
        for creator, data in self.rules["creators"].items():
            if any(pattern in lower_name for pattern in data["patterns"]):
                matches.append({
                    "name": creator,
                    "always_tag": data.get("always_tag", False),
                    "trusted": data.get("trusted", False)
                })
        
        return matches

    def _find_special_patterns(self, name: str) -> List[Dict[str, Any]]:
        """Find special patterns that might override category"""
        lower_name = name.lower()
        matches = []
        
        for pattern_type, data in self.rules["special_patterns"].items():
            if any(pattern in lower_name for pattern in data["patterns"]):
                matches.append({
                    "type": pattern_type,
                    "override_category": data.get("override_category", False)
                })
        
        return matches

    def _find_matching_tags(self, name: str) -> List[str]:
        """Find all automatic tags that should be applied"""
        lower_name = name.lower()
        tags = set()
        
        # Check auto tags
        for tag, patterns in self.rules["tag_rules"]["auto_tags"].items():
            if any(pattern in lower_name for pattern in patterns):
                tags.add(tag)
        
        return list(tags)

    def _extract_technical_specs(self, name: str) -> List[str]:
        """Extract technical specifications based on patterns"""
        pattern = self.rules["naming_patterns"]["technical_specs"]["regex"]
        return re.findall(pattern, name)

    def _extract_version(self, name: str) -> Optional[str]:
        """Extract version number if present"""
        pattern = self.rules["naming_patterns"]["version"]["regex"]
        match = re.search(pattern, name)
        return match.group(1) if match else None

    def _check_nsfw_status(self, name: str) -> Dict[str, bool]:
        """Check NSFW status and whether both versions exist"""
        lower_name = name.lower()
        has_nsfw = False
        has_both = False
        
        # Check for NSFW indicators
        nsfw_pattern = self.rules["naming_patterns"]["nsfw_indicators"]["regex"]
        if re.search(nsfw_pattern, lower_name):
            has_both = True
            has_nsfw = True
        elif "nsfw" in lower_name:
            has_nsfw = True
            
        return {
            "is_nsfw": has_nsfw,
            "has_both_versions": has_both
        }

    def validate_rules(self) -> bool:
        """Validate the structure and content of rules"""
        required_sections = [
            "categories", "franchises", "creators", "special_patterns",
            "tag_rules", "naming_patterns"
        ]
        
        try:
            # Check for required sections
            for section in required_sections:
                if section not in self.rules:
                    raise ValueError(f"Missing required section: {section}")
                
            # Validate category structure
            for category, data in self.rules["categories"].items():
                if not isinstance(data.get("patterns"), list):
                    raise ValueError(f"Invalid patterns for category: {category}")
                if not isinstance(data.get("priority"), int):
                    raise ValueError(f"Invalid priority for category: {category}")
                    
            # Add more specific validation as needed
            
            return True
            
        except Exception as e:
            raise ValueError(f"Rules validation failed: {str(e)}")