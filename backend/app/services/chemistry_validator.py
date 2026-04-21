"""Chemistry validation service for perfume formulations"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)

# Reference paths
BACKEND_DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"      # Must fix - dangerous or impossible
    WARNING = "warning"  # Should fix - suboptimal
    INFO = "info"        # FYI - minor suggestion


@dataclass
class ValidationIssue:
    """Represents a single validation issue"""
    severity: ValidationSeverity
    chemical: str
    message: str
    suggested_fix: Optional[str] = None
    current_value: Optional[float] = None
    recommended_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "severity": self.severity.value,
            "chemical": self.chemical,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value
        }


class ChemistryValidator:
    """Validates perfume formulations against chemistry rules and safety limits"""
    
    def __init__(self):
        self.potency_data: Dict[str, Any] = {}
        self.compounds_data: Dict[str, Any] = {}
        self._load_potency_data()
        self._load_compounds_data()
    
    def _load_potency_data(self) -> None:
        """Load chemicals potency database"""
        potency_file = BACKEND_DATA_DIR / "reference" / "chemicals_potency.json"
        try:
            if potency_file.exists():
                with open(potency_file, 'r', encoding='utf-8') as f:
                    self.potency_data = json.load(f)
                logger.info(f"Loaded potency data for {len(self.potency_data.get('chemicals', {}))} chemicals")
            else:
                logger.warning(f"Potency data file not found: {potency_file}")
                self.potency_data = {"chemicals": {}, "potency_categories": {}}
        except Exception as e:
            logger.error(f"Failed to load potency data: {e}")
            self.potency_data = {"chemicals": {}, "potency_categories": {}}
    
    def _load_compounds_data(self) -> None:
        """Load compounds database for IFRA limits"""
        compounds_file = DATA_DIR / "compounds.json"
        try:
            if compounds_file.exists():
                with open(compounds_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Index by name for faster lookup
                    self.compounds_data = {
                        compound["name"].lower(): compound
                        for compound in data.get("compounds", [])
                    }
                logger.info(f"Loaded IFRA data for {len(self.compounds_data)} compounds")
            else:
                logger.warning(f"Compounds data file not found: {compounds_file}")
                self.compounds_data = {}
        except Exception as e:
            logger.error(f"Failed to load compounds data: {e}")
            self.compounds_data = {}
    
    def _normalize_chemical_name(self, name: str) -> str:
        """Normalize chemical name for matching"""
        # Handle common variations
        normalized = name.strip()
        # Try direct match first
        if normalized in self.potency_data.get("chemicals", {}):
            return normalized
        
        # Try lowercase match
        chemicals = self.potency_data.get("chemicals", {})
        for chem_name in chemicals:
            if chem_name.lower() == normalized.lower():
                return chem_name
        
        # Try removing percentage suffixes (e.g., "Galaxolide 50%" -> "Galaxolide")
        base_name = re.sub(r'\s*\d+%?\s*$', '', normalized)
        for chem_name in chemicals:
            if chem_name.lower() == base_name.lower():
                return chem_name
        
        return normalized
    
    def _get_chemical_data(self, name: str) -> Optional[Dict[str, Any]]:
        """Get chemical data from potency database"""
        normalized = self._normalize_chemical_name(name)
        return self.potency_data.get("chemicals", {}).get(normalized)
    
    def _get_ifra_limit(self, name: str) -> Optional[float]:
        """Get IFRA limit for a chemical from compounds database"""
        normalized = name.lower().strip()
        compound = self.compounds_data.get(normalized)
        if compound:
            return compound.get("ifra_limit")
        
        # Try partial matching
        for key, compound in self.compounds_data.items():
            if key in normalized or normalized in key:
                return compound.get("ifra_limit")
        
        return None
    
    def validate_formula(self, ingredients: List[Dict]) -> List[ValidationIssue]:
        """
        Full validation of a formula.
        
        Args:
            ingredients: List of dicts with 'name' and 'percentage' keys
            
        Returns:
            List of ValidationIssue objects
        """
        issues = []
        issues.extend(self._check_total_percentage(ingredients))
        issues.extend(self._check_potency_limits(ingredients))
        issues.extend(self._check_ifra_limits(ingredients))
        issues.extend(self._check_note_pyramid(ingredients))
        return issues
    
    def _check_total_percentage(self, ingredients: List[Dict]) -> List[ValidationIssue]:
        """Ensure ingredients sum to approximately 100%"""
        issues = []
        
        total = sum(ing.get("percentage", 0) for ing in ingredients)
        
        if total < 95.0:
            diff = 100.0 - total
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                chemical="FORMULA_TOTAL",
                message=f"Formula only sums to {total:.1f}%. Missing {diff:.1f}% to reach 100%.",
                suggested_fix=f"Add {diff:.1f}% more ingredients or adjust existing percentages",
                current_value=total,
                recommended_value=100.0
            ))
        elif total > 105.0:
            diff = total - 100.0
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                chemical="FORMULA_TOTAL",
                message=f"Formula sums to {total:.1f}%, which exceeds 100% by {diff:.1f}%.",
                suggested_fix=f"Reduce ingredient percentages by {diff:.1f}% total",
                current_value=total,
                recommended_value=100.0
            ))
        elif total < 99.0 or total > 101.0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                chemical="FORMULA_TOTAL",
                message=f"Formula sums to {total:.1f}%. Consider adjusting to exactly 100%.",
                current_value=total,
                recommended_value=100.0
            ))
        
        return issues
    
    def _check_potency_limits(self, ingredients: List[Dict]) -> List[ValidationIssue]:
        """Check each chemical against potency database limits"""
        issues = []
        potency_categories = self.potency_data.get("potency_categories", {})
        
        for ing in ingredients:
            name = ing.get("name", "Unknown")
            percentage = ing.get("percentage", 0)
            
            chem_data = self._get_chemical_data(name)
            if not chem_data:
                # Unknown chemical - info only
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    chemical=name,
                    message=f"Chemical '{name}' not in potency database. Cannot validate dosage.",
                    current_value=percentage
                ))
                continue
            
            max_percent = chem_data.get("max_percent", 100)
            min_percent = chem_data.get("min_percent", 0)
            typical_percent = chem_data.get("typical_percent", max_percent / 2)
            potency = chem_data.get("potency", "medium")
            
            # Get potency category thresholds
            potency_cat = potency_categories.get(potency, {})
            max_allowed = potency_cat.get("max_allowed", max_percent)
            warning_threshold = potency_cat.get("warning_threshold", max_percent * 0.8)
            
            # Check if over maximum
            if percentage > max_percent:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    chemical=name,
                    message=f"'{name}' at {percentage:.1f}% exceeds maximum safe limit of {max_percent:.1f}%. Potency: {potency}.",
                    suggested_fix=f"Reduce to {max_percent:.1f}% or less. Typical usage: {typical_percent:.1f}%.",
                    current_value=percentage,
                    recommended_value=typical_percent
                ))
            elif percentage > max_allowed:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    chemical=name,
                    message=f"'{name}' at {percentage:.1f}% exceeds potency category limit of {max_allowed:.1f}%. Potency: {potency}.",
                    suggested_fix=f"Reduce to {max_percent:.1f}% or less for this {potency} potency material.",
                    current_value=percentage,
                    recommended_value=typical_percent
                ))
            # Check if above warning threshold
            elif percentage > warning_threshold or percentage > (max_percent * 0.8):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    chemical=name,
                    message=f"'{name}' at {percentage:.1f}% is approaching maximum of {max_percent:.1f}%. Potency: {potency}.",
                    suggested_fix=f"Consider reducing to typical usage of {typical_percent:.1f}%.",
                    current_value=percentage,
                    recommended_value=typical_percent
                ))
            # Check if below minimum
            elif percentage < min_percent and percentage > 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    chemical=name,
                    message=f"'{name}' at {percentage:.1f}% is below recommended minimum of {min_percent:.1f}%.",
                    suggested_fix=f"Consider increasing to at least {min_percent:.1f}% for noticeable effect.",
                    current_value=percentage,
                    recommended_value=min_percent
                ))
        
        return issues
    
    def _check_ifra_limits(self, ingredients: List[Dict]) -> List[ValidationIssue]:
        """Check IFRA safety limits from compounds database"""
        issues = []
        
        for ing in ingredients:
            name = ing.get("name", "Unknown")
            percentage = ing.get("percentage", 0)
            
            ifra_limit = self._get_ifra_limit(name)
            if ifra_limit is None:
                continue
            
            if percentage > ifra_limit:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    chemical=name,
                    message=f"IFRA VIOLATION: '{name}' at {percentage:.1f}% exceeds IFRA limit of {ifra_limit:.1f}%.",
                    suggested_fix=f"MUST reduce to {ifra_limit:.1f}% or below for safety compliance.",
                    current_value=percentage,
                    recommended_value=ifra_limit * 0.8  # Suggest 80% of limit for safety margin
                ))
            elif percentage > (ifra_limit * 0.9):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    chemical=name,
                    message=f"IFRA WARNING: '{name}' at {percentage:.1f}% is very close to IFRA limit of {ifra_limit:.1f}%.",
                    suggested_fix=f"Consider reducing to {ifra_limit * 0.8:.1f}% for safety margin.",
                    current_value=percentage,
                    recommended_value=ifra_limit * 0.8
                ))
        
        return issues
    
    def _check_note_pyramid(self, ingredients: List[Dict]) -> List[ValidationIssue]:
        """Ensure proper top/heart/base distribution in the formula"""
        issues = []
        
        # Calculate distribution by note
        note_totals = {"top": 0.0, "heart": 0.0, "base": 0.0, "unknown": 0.0}
        
        for ing in ingredients:
            name = ing.get("name", "Unknown")
            percentage = ing.get("percentage", 0)
            
            chem_data = self._get_chemical_data(name)
            if chem_data:
                note = chem_data.get("note", "unknown")
                if note in note_totals:
                    note_totals[note] += percentage
                else:
                    note_totals["unknown"] += percentage
            else:
                note_totals["unknown"] += percentage
        
        total_known = note_totals["top"] + note_totals["heart"] + note_totals["base"]
        
        if total_known == 0:
            # Can't analyze if no known chemicals
            return issues
        
        # Get guidelines
        guidelines = self.potency_data.get("note_distribution_guidelines", {})
        
        # Check each layer
        for note_type in ["top", "heart", "base"]:
            note_percent = note_totals[note_type]
            guide = guidelines.get(note_type, {})
            
            min_pct = guide.get("min_percent", 10.0)
            max_pct = guide.get("max_percent", 50.0)
            ideal_pct = guide.get("ideal_percent", 30.0)
            
            # Calculate as percentage of known total
            if total_known > 0:
                relative_percent = (note_percent / total_known) * 100
            else:
                relative_percent = 0
            
            if note_percent == 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    chemical=f"NOTE_PYRAMID_{note_type.upper()}",
                    message=f"No {note_type} notes detected in formula. A balanced perfume needs all three layers.",
                    suggested_fix=f"Add {note_type} note ingredients. Recommended: {min_pct:.0f}-{max_pct:.0f}% of formula."
                ))
            elif relative_percent < min_pct:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    chemical=f"NOTE_PYRAMID_{note_type.upper()}",
                    message=f"{note_type.capitalize()} notes at {relative_percent:.1f}% of formula (ideal: {ideal_pct:.0f}%).",
                    suggested_fix=f"Consider adding more {note_type} notes for better balance.",
                    current_value=relative_percent,
                    recommended_value=ideal_pct
                ))
        
        return issues
    
    def auto_correct_formula(self, ingredients: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        Attempt to fix issues and return corrected formula with change log.
        
        Args:
            ingredients: List of ingredient dicts
            
        Returns:
            Tuple of (corrected ingredients, list of change descriptions)
        """
        corrected = []
        changes = []
        total_reduction = 0.0
        
        for ing in ingredients:
            name = ing.get("name", "Unknown")
            percentage = ing.get("percentage", 0)
            new_percentage = percentage
            
            # Check potency limits
            chem_data = self._get_chemical_data(name)
            if chem_data:
                max_percent = chem_data.get("max_percent", 100)
                typical_percent = chem_data.get("typical_percent", max_percent / 2)
                
                if percentage > max_percent:
                    new_percentage = max_percent
                    changes.append(
                        f"Reduced '{name}' from {percentage:.1f}% to {max_percent:.1f}% "
                        f"(exceeded maximum safe limit)"
                    )
                    total_reduction += (percentage - max_percent)
            
            # Check IFRA limits
            ifra_limit = self._get_ifra_limit(name)
            if ifra_limit and new_percentage > ifra_limit:
                old_pct = new_percentage
                new_percentage = ifra_limit * 0.9  # Set to 90% of IFRA limit
                changes.append(
                    f"Reduced '{name}' from {old_pct:.1f}% to {new_percentage:.1f}% "
                    f"(IFRA compliance: max {ifra_limit:.1f}%)"
                )
                total_reduction += (old_pct - new_percentage)
            
            corrected.append({
                **ing,
                "percentage": round(new_percentage, 2)
            })
        
        # If we reduced percentages, note the total reduction
        if total_reduction > 0:
            changes.append(
                f"Total reduction: {total_reduction:.1f}%. "
                f"Consider redistributing to other ingredients or adding solvent."
            )
        
        # Check if totals now need adjustment
        new_total = sum(ing.get("percentage", 0) for ing in corrected)
        if new_total < 95.0:
            changes.append(
                f"Formula now sums to {new_total:.1f}%. "
                f"Add {100.0 - new_total:.1f}% more ingredients to complete."
            )
        
        return corrected, changes
    
    def get_dosage_guidelines(self, chemical_name: str) -> Optional[Dict[str, Any]]:
        """
        Get recommended dosage for a chemical.
        
        Args:
            chemical_name: Name of the chemical
            
        Returns:
            Dict with dosage info or None if not found
        """
        chem_data = self._get_chemical_data(chemical_name)
        if not chem_data:
            return None
        
        potency = chem_data.get("potency", "medium")
        potency_cat = self.potency_data.get("potency_categories", {}).get(potency, {})
        
        return {
            "chemical": chemical_name,
            "min_percent": chem_data.get("min_percent"),
            "max_percent": chem_data.get("max_percent"),
            "typical_percent": chem_data.get("typical_percent"),
            "potency": potency,
            "potency_description": potency_cat.get("description", ""),
            "category": chem_data.get("category"),
            "note": chem_data.get("note"),
            "function": chem_data.get("function"),
            "notes": chem_data.get("notes"),
            "ifra_limit": self._get_ifra_limit(chemical_name)
        }
    
    def get_all_dosage_guidelines(self) -> Dict[str, Dict[str, Any]]:
        """Get dosage guidelines for all known chemicals"""
        guidelines = {}
        for name in self.potency_data.get("chemicals", {}):
            guidelines[name] = self.get_dosage_guidelines(name)
        return guidelines
    
    def format_dosage_for_prompt(self) -> str:
        """Format dosage rules as a string for AI prompts"""
        lines = ["## DOSAGE GUIDELINES BY POTENCY\n"]
        
        # Group by potency
        by_potency = {"extreme": [], "high": [], "medium": [], "low": []}
        
        for name, data in self.potency_data.get("chemicals", {}).items():
            potency = data.get("potency", "medium")
            if potency in by_potency:
                by_potency[potency].append((name, data))
        
        potency_categories = self.potency_data.get("potency_categories", {})
        
        for potency in ["extreme", "high", "medium", "low"]:
            cat = potency_categories.get(potency, {})
            chemicals = by_potency.get(potency, [])
            
            if chemicals:
                lines.append(f"\n### {potency.upper()} POTENCY ({cat.get('description', '')})")
                lines.append(f"Max allowed: {cat.get('max_allowed', 'N/A')}%, Warning at: {cat.get('warning_threshold', 'N/A')}%\n")
                
                for name, data in sorted(chemicals):
                    lines.append(
                        f"- **{name}**: {data.get('min_percent', 0)}-{data.get('max_percent', 100)}% "
                        f"(typical: {data.get('typical_percent', 'N/A')}%) - {data.get('notes', '')}"
                    )
        
        return "\n".join(lines)
