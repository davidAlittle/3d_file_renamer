# src/core/name_analyzer.py
from pathlib import Path
from typing import Dict, Any, List, Optional
from .rules_manager import RulesManager

class NameAnalyzer:
   def __init__(self, rules_manager: RulesManager):
       self.rules = rules_manager

   def analyze_name(self, filename: str, content_analysis: dict = None) -> dict:
       """Comprehensive name analysis using loaded rules"""
       result = {
           'original_name': filename,
           'base_name': self._clean_base_name(filename),
           'category': None,
           'franchise': None,
           'creator': None,
           'version': None,
           'tags': set(),
           'technical_specs': [],
           'is_nsfw': False,
           'has_sfw_version': False,
           'has_nsfw_version': False,
           'priority_override': False
       }

       # Use rules manager to find matches
       matches = self.rules.test_name(filename)
       
       # Apply NSFW status
       nsfw_status = matches['nsfw_status']
       result['is_nsfw'] = nsfw_status['is_nsfw']
       if nsfw_status['has_both_versions']:
           result['has_sfw_version'] = True
           result['has_nsfw_version'] = True

       # Check for special pattern overrides first
       for special in matches['special_patterns']:
           if special['override_category']:
               result['category'] = special['type']
               result['priority_override'] = True
               break

       # If no override, apply category based on priority
       if not result['priority_override'] and matches['categories']:
           result['category'] = matches['categories'][0]['category']

       # If still no category, use MISC
       if not result['category']:
           result['category'] = 'MISC'

       # Apply franchise if found
       if matches['franchises']:
           franchise = matches['franchises'][0]
           result['franchise'] = franchise['name']
           # Add related categories to tags if appropriate
           for cat in franchise.get('related_categories', []):
               if cat != result['category']:
                   result['tags'].add(cat)

       # Add creator tags
       for creator in matches['creators']:
           if creator.get('always_tag'):
               result['tags'].add(creator['name'])
               result['creator'] = creator['name']

       # Add version if found
       if matches['version']:
           result['version'] = matches['version']

       # Add technical specs
       result['technical_specs'] = matches['technical']

       # Add automatic tags
       result['tags'].update(matches['tags'])

       # Add content-based tags if content analysis is provided
       if content_analysis:
           self._add_content_tags(result, content_analysis)

       return result

   def _clean_base_name(self, filename: str) -> str:
       """Remove common patterns and clean up the base name"""
       name = Path(filename).stem

       # Remove known patterns using rules
       test_results = self.rules.test_name(name)
       
       # Remove version numbers if found
       if test_results['version']:
           name = name.replace(f"v{test_results['version']}", "")
           
       # Remove technical specs
       for spec in test_results['technical']:
           name = name.replace(spec, "")
           
       # Remove creator names
       for creator in test_results['creators']:
           for pattern in self.rules.rules['creators'][creator['name']]['patterns']:
               name = name.replace(pattern, "")
               
       # Clean up common artifacts
       name = name.replace('_', ' ')
       name = name.replace('-', ' ')
       name = ' '.join(name.split())  # Normalize whitespace
       name = name.strip()

       return name

   def _add_content_tags(self, result: dict, content_analysis: dict):
       """Add tags based on archive content analysis"""
       content_rules = self.rules.rules['tag_rules']['content_based_tags']
       
       for tag, rules in content_rules.items():
           file_patterns = rules.get('file_contains', [])
           if any(pattern in str(content_analysis).lower() for pattern in file_patterns):
               result['tags'].add(tag)

   def suggest_name(self, analysis: dict, settings: dict = None) -> str:
       """Generate suggested name based on analysis results"""
       parts = []
       
       # Add category prefix if not disabled
       if not settings or settings.get('add_category_prefix', True):
           parts.append(analysis['category'])
           
       # Add franchise if present
       if analysis['franchise']:
           parts.append(analysis['franchise'])
           
       # Add base name
       parts.append(analysis['base_name'])
       
       # Add version if present and preservation is enabled
       if analysis['version'] and (not settings or settings.get('preserve_version_numbers', True)):
           parts.append(f"v{analysis['version']}")
           
       # Add technical specs if any
       if analysis['technical_specs']:
           parts.extend(analysis['technical_specs'])
           
       # Build primary name
       new_name = ' '.join(parts)
       
       # Format and add tags
       if analysis['tags']:
           tag_style = settings.get('tag_style', 'brackets') if settings else 'brackets'
           tags = sorted(analysis['tags'])
           
           if tag_style == 'brackets':
               formatted_tags = [f"[{tag}]" for tag in tags]
           elif tag_style == 'parentheses':
               formatted_tags = [f"({tag})" for tag in tags]
           else:
               formatted_tags = tags
               
           new_name = f"{new_name} {' '.join(formatted_tags)}"
       
       return new_name

   def test_rules(self, test_filename: str) -> Dict[str, Any]:
       """Test current rules against a filename and return detailed analysis"""
       analysis = self.analyze_name(test_filename)
       suggested_name = self.suggest_name(analysis)
       
       return {
           'analysis': analysis,
           'suggested_name': suggested_name,
           'rule_matches': self.rules.test_name(test_filename)
       }