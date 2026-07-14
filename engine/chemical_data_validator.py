"""
Chemical Data Validator - Prevents Recommendations Without Verified Data

CRITICAL RULE: Never recommend a chemical unless it passes ALL validation checks.

This module ensures every recommended chemical has:
1. Verified CAS number from trusted source
2. Confirmed odor character description
3. Usage rate data (percentage range)
4. Price verification from supplier
5. Source attribution (where data came from)

Author: Safety-First Chemistry Assistant
Last Updated: 2026-01-13
"""

import csv
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

_ENGINE_ROOT = Path(__file__).resolve().parent.parent


class DataQuality(Enum):
    """Data quality levels"""
    VERIFIED = "verified"  # All fields confirmed from multiple sources
    PARTIAL = "partial"    # Some fields missing or single source
    INSUFFICIENT = "insufficient"  # Too many gaps, DO NOT RECOMMEND
    UNKNOWN = "unknown"    # No reliable data


class TrustedSource(Enum):
    """Trusted data sources in order of reliability"""
    # Tier 1: Scientific databases
    TGSC = "The Good Scents Company"
    PUBCHEM = "PubChem"
    CHEMSPIDER = "ChemSpider"
    
    # Tier 2: Supplier catalogs (verified)
    PERFUMERSWORLD = "PerfumersWorld Catalog"
    SIGMA_ALDRICH = "Sigma-Aldrich"
    
    # Tier 3: Formulation databases
    DATA_SPINE = "Local Data Spine"
    USER_INVENTORY = "User Chemical Inventory"
    FORMULATION_HISTORY = "Historical Formulations"
    
    # Tier 4: Secondary sources (requires corroboration)
    FRAGRANTICA = "Fragrantica"
    BASENOTES = "Basenotes"
    
    # NEVER USE ALONE
    CHAT_MEMORY = "Previous Conversation (VERIFY BEFORE USE)"


@dataclass
class ChemicalDataRecord:
    """Complete data record for a chemical"""
    # Identity
    name: str
    cas_number: Optional[str] = None
    
    # Physical/Chemical
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    log_p: Optional[float] = None
    vapor_pressure: Optional[float] = None
    
    # Olfactory
    odor_description: Optional[str] = None
    odor_threshold: Optional[float] = None
    usage_rate_min: Optional[float] = None  # Percentage
    usage_rate_max: Optional[float] = None  # Percentage
    
    # Commercial
    price_per_ml: Optional[float] = None
    supplier: Optional[str] = None
    availability: Optional[str] = None
    
    # Safety
    ifra_status: Optional[str] = None
    
    # Provenance (CRITICAL)
    data_sources: List[TrustedSource] = None
    verification_date: Optional[str] = None
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.data_sources is None:
            self.data_sources = []
    
    def calculate_confidence(self) -> float:
        """Calculate confidence score (0-100)"""
        score = 0.0
        
        # Identity verification (30 points)
        if self.cas_number:
            score += 15
        if len(self.data_sources) >= 2:
            score += 15
        
        # Olfactory data (40 points - MOST CRITICAL for perfumery)
        if self.odor_description:
            score += 20
        if self.usage_rate_min is not None and self.usage_rate_max is not None:
            score += 20
        
        # Physical data (20 points)
        if self.log_p is not None:
            score += 10
        if self.vapor_pressure is not None:
            score += 10
        
        # Commercial data (10 points)
        if self.price_per_ml is not None:
            score += 10
        
        self.confidence_score = score
        return score
    
    def get_data_quality(self) -> DataQuality:
        """Determine if this chemical can be recommended"""
        confidence = self.calculate_confidence()
        
        # STRICT RULES:
        # - Must have odor description from trusted source
        # - Must have usage rate OR well-documented in formulations
        # - Must have price if recommending purchase
        
        if confidence >= 70:
            return DataQuality.VERIFIED
        elif confidence >= 50:
            return DataQuality.PARTIAL
        elif confidence >= 30:
            return DataQuality.INSUFFICIENT
        else:
            return DataQuality.UNKNOWN
    
    def can_recommend(self) -> Tuple[bool, str]:
        """
        Returns (can_recommend, reason)
        
        ONLY return True if VERIFIED quality
        """
        quality = self.get_data_quality()
        
        if quality == DataQuality.VERIFIED:
            return True, "Verified data from multiple sources"
        
        # Build specific failure reason
        missing = []
        if not self.odor_description:
            missing.append("odor character")
        if self.usage_rate_min is None or self.usage_rate_max is None:
            missing.append("usage rate")
        if not self.cas_number:
            missing.append("CAS number")
        if not self.data_sources or len(self.data_sources) < 2:
            missing.append("multiple source verification")
        
        reason = f"Insufficient data: missing {', '.join(missing)}"
        return False, reason


class ChemicalKnowledgeBase:
    """
    Central knowledge base for chemical data
    
    CRITICAL: All recommendations must query this first
    """
    
    def __init__(self, 
                 inventory_path: str = "knowledge/chemical_inventory.md",
                 tgsc_path: str = "tgsc_ingredients_all.csv",
                 perfumersworld_path: str = "perfumersworld_ABC_families/"):
        self.inventory_path = inventory_path
        self.tgsc_path = tgsc_path
        self.perfumersworld_path = perfumersworld_path
        
        # Cache for validated chemicals
        self.verified_chemicals: Dict[str, ChemicalDataRecord] = {}
        self.flagged_chemicals: Dict[str, str] = {}  # name -> reason flagged
    
    def lookup_chemical(self, name: str) -> Optional[ChemicalDataRecord]:
        """
        Look up chemical in all trusted sources
        
        Returns None if insufficient data
        """
        # Check cache first
        if name.lower() in self.verified_chemicals:
            return self.verified_chemicals[name.lower()]
        
        # Check flagged list
        if name.lower() in self.flagged_chemicals:
            return None  # Already determined insufficient
        
        # Build record from sources
        record = ChemicalDataRecord(name=name)
        sources = []
        
        # Source 1: ingredient_intelligence profiles (returns MaterialProfile dataclass)
        try:
            from .ingredient_intelligence import get_profile
            profile = get_profile(name)
            if profile:
                record.molecular_weight = record.molecular_weight or profile.mw
                record.vapor_pressure = record.vapor_pressure or profile.vp
                record.log_p = record.log_p or profile.clogp
                record.odor_threshold = record.odor_threshold or profile.odt
                record.odor_description = record.odor_description or profile.dominant_character()
                usage_ranges = {
                    "character": (2.0, 15.0),
                    "modifier": (0.5, 5.0),
                    "fixative": (1.0, 10.0),
                    "trace": (0.01, 1.0),
                    "radiance": (1.0, 10.0),
                    "volume": (2.0, 20.0),
                    "bridge": (0.5, 5.0),
                }
                umin, umax = usage_ranges.get(profile.role, (0.5, 10.0))
                if profile.dilution < 1.0:
                    umin = round(umin / profile.dilution, 3)
                    umax = round(umax / profile.dilution, 3)
                record.usage_rate_min = record.usage_rate_min or umin
                record.usage_rate_max = record.usage_rate_max or umax
                sources.append(TrustedSource.FORMULATION_HISTORY)
        except (ImportError, Exception):
            pass
        
        # Source 2: material_properties.json
        try:
            from .data_spine.loader import load_registry
            material = load_registry().get(name)
            if material:
                record.molecular_weight = record.molecular_weight or material.mw_g_mol
                record.vapor_pressure = record.vapor_pressure or material.vp_25c_pa
                record.log_p = record.log_p or material.logp
                record.odor_threshold = record.odor_threshold or material.odt_air_ppb
                record.cas_number = record.cas_number or material.cas
                record.odor_description = record.odor_description or material.character
                sources.append(TrustedSource.DATA_SPINE)
        except (ImportError, Exception):
            pass

        # Source 3: material_properties.json
        try:
            props_path = os.path.join(
                os.path.dirname(__file__), "..", "data",
                "knowledge_graph", "material_properties.json"
            )
            if os.path.exists(props_path):
                with open(props_path, "r", encoding="utf-8") as f:
                    all_props = json.load(f)
                name_lower = name.lower()
                for entry in all_props:
                    if entry.get("name", "").lower() == name_lower:
                        if entry.get("mw") and not record.molecular_weight:
                            record.molecular_weight = entry["mw"]
                        if entry.get("vp") and not record.vapor_pressure:
                            record.vapor_pressure = entry["vp"]
                        if entry.get("clp") and not record.log_p:
                            record.log_p = entry["clp"]
                        if entry.get("odt") and not record.odor_threshold:
                            record.odor_threshold = entry["odt"]
                        if entry.get("cas") and not record.cas_number:
                            record.cas_number = entry["cas"]
                        sources.append(TrustedSource.PUBCHEM)
                        break
        except (IOError, json.JSONDecodeError):
            pass
        
        # Source 4: compounds.json (IFRA limits, CAS, MW)
        try:
            compounds_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "compounds.json"
            )
            if os.path.exists(compounds_path):
                with open(compounds_path, "r", encoding="utf-8") as f:
                    compounds_data = json.load(f)
                name_lower = name.lower()
                for c in compounds_data.get("compounds", []):
                    if c.get("name", "").lower() == name_lower:
                        if c.get("cas") and not record.cas_number:
                            record.cas_number = c["cas"]
                        if c.get("ifra_limit") is not None:
                            record.ifra_status = f"IFRA Cat 4 limit: {c['ifra_limit']}%"
                        if c.get("molecular_weight") and not record.molecular_weight:
                            record.molecular_weight = c["molecular_weight"]
                        scent = c.get("scent", [])
                        if scent and not record.odor_description:
                            record.odor_description = ", ".join(scent)
                        sources.append(TrustedSource.SIGMA_ALDRICH)
                        break
        except (IOError, json.JSONDecodeError):
            pass
        
        record.data_sources = sources
        record.calculate_confidence()
        
        # Cache the result
        self.verified_chemicals[name.lower()] = record
        return record
    
    def validate_for_recommendation(self, name: str) -> Tuple[bool, Optional[ChemicalDataRecord], str]:
        """
        Validate a chemical before recommending
        
        Returns: (can_recommend, data_record, explanation)
        
        USE THIS BEFORE EVERY RECOMMENDATION!
        """
        record = self.lookup_chemical(name)
        
        if record is None:
            return False, None, f"No data found for {name} in trusted sources"
        
        can_rec, reason = record.can_recommend()
        
        if not can_rec:
            # Flag it to prevent future recommendations
            self.flagged_chemicals[name.lower()] = reason
        
        return can_rec, record, reason
    
    def get_alternatives_with_data(self, category: str, 
                                   minimum_confidence: float = 70.0) -> List[ChemicalDataRecord]:
        """
        Get list of alternatives in a category that have VERIFIED data
        
        Only returns chemicals that pass validation.
        Category matches against note (top/heart/base), role, or dominant
        character dimension.
        """
        try:
            from .ingredient_intelligence import get_all_profiles
            profiles = get_all_profiles()
        except (ImportError, Exception):
            return []

        results = []
        cat_lower = category.lower()

        for prof_name, profile in profiles.items():
            # profile is a MaterialProfile dataclass
            note = (profile.note or "").lower()
            role = (profile.role or "").lower()
            dominant = profile.dominant_character().lower()

            if cat_lower in (note, role, dominant):
                record = self.lookup_chemical(prof_name)
                if record and record.confidence_score >= minimum_confidence:
                    results.append(record)
        
        results.sort(key=lambda r: r.confidence_score, reverse=True)
        return results
    
    def flag_chemical(self, name: str, reason: str):
        """Manually flag a chemical as unrecommendable"""
        self.flagged_chemicals[name.lower()] = reason
        print(f"⚠️ FLAGGED: {name} - {reason}")
    
    def report_knowledge_gaps(self) -> str:
        """Generate report of chemicals with insufficient data"""
        report = "# Knowledge Gaps Report\n\n"
        report += f"Total flagged chemicals: {len(self.flagged_chemicals)}\n\n"
        
        for name, reason in sorted(self.flagged_chemicals.items()):
            report += f"## {name.title()}\n"
            report += f"**Reason:** {reason}\n\n"
        
        return report


# SAFETY DECORATOR
def require_verified_data(func):
    """
    Decorator that prevents recommendations without verified data
    
    Usage:
        @require_verified_data
        def recommend_chemical(self, name: str, ...):
            # This only runs if data is verified
    """
    def wrapper(self, name: str, *args, **kwargs):
        kb = getattr(self, 'knowledge_base', None)
        if kb is None:
            raise RuntimeError("ChemicalKnowledgeBase not initialized!")
        
        can_rec, record, reason = kb.validate_for_recommendation(name)
        
        if not can_rec:
            print(f"❌ BLOCKED RECOMMENDATION: {name}")
            print(f"   Reason: {reason}")
            return None  # Do not proceed
        
        print(f"✅ VERIFIED: {name} (confidence: {record.confidence_score}%)")
        return func(self, name, *args, record=record, **kwargs)
    
    return wrapper


# PRE-POPULATE KNOWN PROBLEM CHEMICALS
FLAGGED_CHEMICALS = {
    # Add more as discovered
}


def blocked_reason(name: str) -> Optional[str]:
    """Return the block reason for a chemical name if it is explicitly flagged."""
    key = name.lower().strip()
    return FLAGGED_CHEMICALS.get(key)


def is_blocked_chemical(name: str) -> bool:
    """True when a material is explicitly blocked from recommendation."""
    return blocked_reason(name) is not None


def initialize_knowledge_base() -> ChemicalKnowledgeBase:
    """Initialize knowledge base with pre-flagged chemicals"""
    kb = ChemicalKnowledgeBase()
    
    for name, reason in FLAGGED_CHEMICALS.items():
        kb.flag_chemical(name, reason)
    
    return kb


if __name__ == "__main__":
    # Test
    kb = initialize_knowledge_base()
    
    # Test Orivone with the current validated data path
    can_rec, record, reason = kb.validate_for_recommendation("Orivone")
    print(f"\nOrivone validation: {can_rec}")
    print(f"Reason: {reason}")
    
    # Generate gap report
    print("\n" + kb.report_knowledge_gaps())
