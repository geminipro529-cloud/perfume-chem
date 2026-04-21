"""Context builder for RAG-style prompt enhancement"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from app.services.data_loader import DataLoader
from app.services.chemistry_validator import ChemistryValidator

logger = logging.getLogger(__name__)

# Add project root for engine imports
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger(__name__)

# Formulations directory
FORMULATIONS_DIR = Path(__file__).parent.parent.parent.parent / "formulations"


class ContextBuilder:
    """Builds context for AI prompts from knowledge base"""
    
    def __init__(self):
        self.data_loader = DataLoader
        self.validator = ChemistryValidator()
    
    def build_context(
        self,
        query: str,
        ingredients: Optional[List[Dict]] = None,
        include_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Build full context for AI prompt.
        
        Args:
            query: User query or perfume name
            ingredients: Optional list of ingredient dicts
            include_validation: Whether to include validation context
            
        Returns:
            Dict with context strings for prompt injection
        """
        context = {
            "inventory": self._get_inventory_context(),
            "dosage_guidelines": self._get_dosage_guidelines(),
            "relevant_knowledge": self._search_relevant_knowledge(query),
            "similar_formulations": self._find_similar_formulations(query),
            "validation_context": None
        }
        
        if include_validation and ingredients:
            context["validation_context"] = self._get_validation_context(ingredients)
        
        return context
    
    def _get_inventory_context(self) -> str:
        """Format available chemicals as context string"""
        try:
            compounds = self.data_loader.load_compounds()
            compound_list = compounds.get("compounds", [])
            
            if not compound_list:
                return "No compounds database available."
            
            lines = ["## AVAILABLE CHEMICALS IN INVENTORY\n"]
            
            # Group by note type
            by_note = {"top": [], "heart": [], "base": [], "other": []}
            
            for compound in compound_list:
                name = compound.get("name", "Unknown")
                note = compound.get("note", "other")
                scent = ", ".join(compound.get("scent", []))
                ifra = compound.get("ifra_limit")
                
                entry = f"- **{name}**"
                if scent:
                    entry += f": {scent}"
                if ifra:
                    entry += f" (IFRA max: {ifra}%)"
                
                if note in by_note:
                    by_note[note].append(entry)
                else:
                    by_note["other"].append(entry)
            
            # Also add from potency database
            potency_chemicals = self.validator.potency_data.get("chemicals", {})
            for name, data in potency_chemicals.items():
                note = data.get("note", "other")
                if note not in by_note:
                    note = "other"
                
                entry = f"- **{name}**: {data.get('function', '')} ({data.get('min_percent', 0)}-{data.get('max_percent', 100)}%)"
                if entry not in by_note[note]:
                    by_note[note].append(entry)
            
            for note_type in ["top", "heart", "base", "other"]:
                if by_note[note_type]:
                    lines.append(f"\n### {note_type.upper()} NOTES")
                    lines.extend(sorted(set(by_note[note_type])))
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to build inventory context: {e}")
            return "Inventory context unavailable."
    
    def _get_dosage_guidelines(self) -> str:
        """Format dosage rules as context string"""
        try:
            return self.validator.format_dosage_for_prompt()
        except Exception as e:
            logger.error(f"Failed to build dosage guidelines: {e}")
            return "Dosage guidelines unavailable."
    
    def _search_relevant_knowledge(self, query: str) -> str:
        """Search knowledge base — semantic search with keyword fallback."""
        # Try semantic search first
        try:
            from engine.knowledge import KnowledgeIndex
            idx = KnowledgeIndex()
            idx.build()  # loads existing index
            results = idx.search(query, k=5)
            if results:
                lines = ["## RELEVANT KNOWLEDGE (semantic search)\n"]
                for r in results:
                    lines.append(f"### From {r['source']} (relevance: {r['score']:.2f})")
                    lines.append(r["text"][:3000])
                    lines.append("")
                return "\n".join(lines)
        except Exception as e:
            logger.debug(f"Semantic search unavailable, falling back to keyword: {e}")

        # Fallback: keyword search
        try:
            # Extract key terms from query
            terms = self._extract_search_terms(query)
            
            all_matches = []
            
            for term in terms:
                results = self.data_loader.search_knowledge(term)
                
                for file in results.get("files", []):
                    if file not in [m.get("file") for m in all_matches]:
                        content = self.data_loader.load_knowledge_file(file)
                        if content:
                            # Get relevant section
                            section = self._extract_relevant_section(content, term)
                            if section:
                                all_matches.append({
                                    "file": file,
                                    "term": term,
                                    "content": section
                                })
            
            if not all_matches:
                return "No specific knowledge found for this query."
            
            lines = ["## RELEVANT KNOWLEDGE\n"]
            
            for match in all_matches[:3]:  # Limit to top 3 most relevant
                lines.append(f"### From {match['file']} (matched: '{match['term']}')")
                lines.append(match['content'][:1500])  # Limit content length
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to search knowledge: {e}")
            return "Knowledge search unavailable."
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract meaningful search terms from query"""
        # Common perfume-related terms to look for
        perfume_keywords = [
            "aventus", "dior", "homme", "intense", "parfum", "bleu",
            "oud", "amber", "iris", "violet", "woody", "fresh",
            "leather", "musk", "vanilla", "sandalwood", "cedar",
            "citrus", "bergamot", "jasmine", "rose", "gourmand"
        ]
        
        terms = []
        query_lower = query.lower()
        
        # Add whole words that match keywords
        for keyword in perfume_keywords:
            if keyword in query_lower:
                terms.append(keyword)
        
        # Add any capitalized proper nouns (likely perfume names)
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 3:
                terms.append(word.lower())
        
        # Fallback to main words if no terms found
        if not terms:
            terms = [w.lower() for w in words if len(w) > 4][:3]
        
        return list(set(terms))[:5]  # Limit to 5 unique terms
    
    def _extract_relevant_section(self, content: str, term: str) -> Optional[str]:
        """Extract the most relevant section containing the search term"""
        lines = content.split('\n')
        term_lower = term.lower()
        
        # Find line with term
        matching_indices = []
        for i, line in enumerate(lines):
            if term_lower in line.lower():
                matching_indices.append(i)
        
        if not matching_indices:
            return None
        
        # Get context around first match
        idx = matching_indices[0]
        start = max(0, idx - 5)
        end = min(len(lines), idx + 15)
        
        return '\n'.join(lines[start:end])
    
    def _find_similar_formulations(self, query: str) -> str:
        """Find similar past formulations"""
        try:
            if not FORMULATIONS_DIR.exists():
                return "No formulations directory found."
            
            # Get search terms
            terms = self._extract_search_terms(query)
            
            matching_formulations = []
            
            for md_file in FORMULATIONS_DIR.glob("*.md"):
                filename = md_file.stem.lower()
                
                # Check if any term matches filename
                for term in terms:
                    if term in filename:
                        try:
                            with open(md_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Extract formula section if exists
                            formula_section = self._extract_formula_section(content)
                            
                            matching_formulations.append({
                                "name": md_file.stem,
                                "term": term,
                                "formula": formula_section or "Formula not extracted"
                            })
                            break
                        except Exception as e:
                            logger.warning(f"Could not read {md_file}: {e}")
            
            if not matching_formulations:
                return "No similar formulations found in history."
            
            lines = ["## SIMILAR PAST FORMULATIONS\n"]
            
            for form in matching_formulations[:3]:  # Limit to 3
                lines.append(f"### {form['name']}")
                lines.append(form['formula'][:1000])  # Limit length
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to find formulations: {e}")
            return "Formulation search unavailable."
    
    def _extract_formula_section(self, content: str) -> Optional[str]:
        """Extract the formula/ingredients section from a markdown file"""
        # Look for common section headers
        patterns = [
            r'#+\s*(Formula|Ingredients|Composition|Recipe).*?\n([\s\S]*?)(?=\n#+|\Z)',
            r'\|.*?Ingredient.*?\|.*?\n([\s\S]*?)(?=\n\n|\Z)',
            r'[-*]\s*\*\*.*?:\s*\d+.*?%'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(0)
        
        # Return first 500 chars if no pattern matched
        return content[:500] if len(content) > 500 else content
    
    def _get_validation_context(self, ingredients: List[Dict]) -> str:
        """Pre-validate and include any warnings"""
        try:
            issues = self.validator.validate_formula(ingredients)
            
            if not issues:
                return "✓ Formula passes all validation checks."
            
            lines = ["## PRE-VALIDATION RESULTS\n"]
            
            errors = [i for i in issues if i.severity.value == "error"]
            warnings = [i for i in issues if i.severity.value == "warning"]
            info = [i for i in issues if i.severity.value == "info"]
            
            if errors:
                lines.append("### ❌ ERRORS (Must Fix)")
                for issue in errors:
                    lines.append(f"- **{issue.chemical}**: {issue.message}")
                    if issue.suggested_fix:
                        lines.append(f"  - Fix: {issue.suggested_fix}")
                lines.append("")
            
            if warnings:
                lines.append("### ⚠️ WARNINGS (Should Fix)")
                for issue in warnings:
                    lines.append(f"- **{issue.chemical}**: {issue.message}")
                    if issue.suggested_fix:
                        lines.append(f"  - Suggestion: {issue.suggested_fix}")
                lines.append("")
            
            if info:
                lines.append("### ℹ️ INFO")
                for issue in info:
                    lines.append(f"- **{issue.chemical}**: {issue.message}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to build validation context: {e}")
            return "Validation unavailable."
    
    def build_system_context(self) -> str:
        """Build a system-level context with rules and constraints"""
        return """## SYSTEM RULES FOR PERFUME FORMULATION

1. **NEVER exceed IFRA limits** - These are safety regulations, not suggestions.
2. **Respect potency levels**:
   - EXTREME potency: Max 0.5%, use at trace levels
   - HIGH potency: Max 2%, use sparingly
   - MEDIUM potency: Max 10%, standard usage
   - LOW potency: Up to 50%, foundation materials
3. **Balance the pyramid**: Include top (10-30%), heart (30-50%), base (30-50%)
4. **Total must equal 100%** (or include solvent/carrier to complete)
5. **Only suggest chemicals from the available inventory**
6. **Flag any concerns** about safety, stability, or performance

When suggesting formulas:
- Start with foundation/base notes
- Build character with heart notes
- Add sparkle with top notes
- Use modifiers at trace levels for complexity
- Always include longevity and sillage estimates
"""
