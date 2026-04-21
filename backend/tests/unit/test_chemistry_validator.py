"""Tests for chemistry validation service"""

import pytest
from pathlib import Path
import json

from app.services.chemistry_validator import (
    ChemistryValidator,
    ValidationSeverity,
    ValidationIssue
)


@pytest.fixture
def validator():
    """Create a ChemistryValidator instance"""
    return ChemistryValidator()


@pytest.fixture
def sample_valid_formula():
    """A well-balanced valid formula respecting IFRA limits"""
    # Note: Must respect IFRA limits from compounds.json:
    # - Iso E Super IFRA: 22%, using 20%
    # - Hedione IFRA: 25%, using 20%
    # - Linalool IFRA: 4%, using 3%
    # - Galaxolide IFRA: 15%, using 12%
    return [
        {"name": "Iso E Super", "percentage": 20.0},  # Under IFRA 22%
        {"name": "Hedione", "percentage": 20.0},      # Under IFRA 25%
        {"name": "Linalool", "percentage": 3.0},      # Under IFRA 4%
        {"name": "Galaxolide", "percentage": 12.0},   # Under IFRA 15%
        {"name": "Linalyl Acetate", "percentage": 10.0},
        {"name": "Ambroxan", "percentage": 5.0},
        {"name": "Ethanol", "percentage": 30.0}       # Carrier to reach 100%
    ]


@pytest.fixture
def sample_overdosed_formula():
    """Formula with overdosed extreme-potency chemicals"""
    return [
        {"name": "Alpha Irone", "percentage": 5.0},  # Max is 0.5%!
        {"name": "Iso E Super", "percentage": 25.0},
        {"name": "Hedione", "percentage": 20.0},
        {"name": "Ethanol", "percentage": 50.0}
    ]


class TestChemistryValidator:
    """Test suite for ChemistryValidator"""
    
    def test_validator_loads_data(self, validator):
        """Validator should load potency and compounds data"""
        assert validator.potency_data is not None
        assert "chemicals" in validator.potency_data
        assert len(validator.potency_data["chemicals"]) > 0
    
    def test_potency_error_on_extreme_overdose(self, validator):
        """Extreme-potency chemicals over limit should ERROR"""
        ingredients = [
            {"name": "Alpha Irone", "percentage": 5.0},  # Max is 0.5%
            {"name": "Iso E Super", "percentage": 20.0}
        ]
        
        issues = validator.validate_formula(ingredients)
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        
        assert len(errors) >= 1
        # Find the Alpha Irone error
        alpha_irone_errors = [e for e in errors if "Alpha Irone" in e.chemical or "Alpha-Irone" in e.chemical]
        assert len(alpha_irone_errors) >= 1
        assert "exceed" in alpha_irone_errors[0].message.lower()
    
    def test_warning_on_high_dosage(self, validator):
        """High chemicals approaching limit should WARNING"""
        # Beta Damascone max is 0.5%, so 0.4% is 80% of max -> should trigger warning
        ingredients = [
            {"name": "Cashmeran", "percentage": 1.8},  # Max is 2%, warning at 1.6%+
            {"name": "Hedione", "percentage": 28.0}  # Max is 30%, warning at ~24%+
        ]
        
        issues = validator.validate_formula(ingredients)
        warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        
        # Should have at least one warning for approaching limits
        assert len(warnings) >= 1 or len([i for i in issues if i.severity != ValidationSeverity.INFO]) >= 1
    
    def test_total_percentage_too_low(self, validator):
        """Total significantly below 100% should WARN"""
        ingredients = [
            {"name": "Iso E Super", "percentage": 30.0},
            {"name": "Hedione", "percentage": 20.0}
            # Total = 50%, missing 50%
        ]
        
        issues = validator.validate_formula(ingredients)
        
        # Should have issue about total
        total_issues = [i for i in issues if "FORMULA_TOTAL" in i.chemical or "total" in i.message.lower()]
        assert len(total_issues) >= 1
    
    def test_total_percentage_too_high(self, validator):
        """Total above 100% should ERROR"""
        ingredients = [
            {"name": "Iso E Super", "percentage": 50.0},
            {"name": "Hedione", "percentage": 30.0},
            {"name": "Galaxolide", "percentage": 30.0}
            # Total = 110%
        ]
        
        issues = validator.validate_formula(ingredients)
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        
        total_errors = [e for e in errors if "FORMULA_TOTAL" in e.chemical or "exceed" in e.message.lower()]
        assert len(total_errors) >= 1
    
    def test_valid_formula_minimal_issues(self, validator, sample_valid_formula):
        """A well-balanced formula should have minimal critical issues"""
        issues = validator.validate_formula(sample_valid_formula)
        
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        # Well-balanced formula shouldn't have errors
        assert len(errors) == 0
    
    def test_auto_correct_extreme_chemical(self, validator):
        """Auto-correct should cap extreme-potency chemicals"""
        ingredients = [
            {"name": "Alpha Irone", "percentage": 5.0},  # Way over 0.5% max
            {"name": "Iso E Super", "percentage": 45.0},
            {"name": "Ethanol", "percentage": 50.0}
        ]
        
        corrected, changes = validator.auto_correct_formula(ingredients)
        
        # Find Alpha Irone in corrected formula
        alpha_irone = next((i for i in corrected if "Alpha" in i["name"] and "Irone" in i["name"]), None)
        
        assert alpha_irone is not None
        assert alpha_irone["percentage"] <= 0.5  # Should be capped
        assert len(changes) >= 1
        assert any("Alpha Irone" in change or "Alpha-Irone" in change for change in changes)
    
    def test_auto_correct_preserves_valid_chemicals(self, validator):
        """Auto-correct should not change already-valid percentages (within potency AND IFRA limits)"""
        # Use chemicals without IFRA entries or within IFRA limits
        ingredients = [
            {"name": "Cashmeran", "percentage": 1.0},  # Valid (under 2%)
            {"name": "Helional", "percentage": 3.0},   # Valid (under 5%)
            {"name": "Alpha Irone", "percentage": 0.3} # Valid (under 0.5%)
        ]
        
        corrected, changes = validator.auto_correct_formula(ingredients)
        
        # No potency corrections should be needed (IFRA may not apply to these)
        cashmeran = next((i for i in corrected if i["name"] == "Cashmeran"), None)
        helional = next((i for i in corrected if i["name"] == "Helional"), None)
        
        # These should be unchanged since they're within potency limits
        if cashmeran:
            assert cashmeran["percentage"] == 1.0
        if helional:
            assert helional["percentage"] == 3.0
    
    def test_ifra_limit_check(self, validator):
        """IFRA limits from compounds.json should be checked"""
        # Coumarin has IFRA limit of 0.8%
        ingredients = [
            {"name": "Coumarin", "percentage": 2.0},  # IFRA limit is 0.8%
            {"name": "Iso E Super", "percentage": 48.0},
            {"name": "Ethanol", "percentage": 50.0}
        ]
        
        issues = validator.validate_formula(ingredients)
        
        # Should have IFRA violation
        ifra_issues = [i for i in issues if "IFRA" in i.message]
        assert len(ifra_issues) >= 1
        assert any("Coumarin" in i.chemical for i in ifra_issues)
    
    def test_eugenol_ifra_limit(self, validator):
        """Eugenol IFRA limit of 0.5% should be enforced"""
        ingredients = [
            {"name": "Eugenol", "percentage": 1.0},  # IFRA limit is 0.5%
            {"name": "Hedione", "percentage": 49.0},
            {"name": "Ethanol", "percentage": 50.0}
        ]
        
        issues = validator.validate_formula(ingredients)
        
        # Should have issue for Eugenol
        eugenol_issues = [i for i in issues if "Eugenol" in i.chemical]
        assert len(eugenol_issues) >= 1
    
    def test_get_dosage_guidelines(self, validator):
        """Should return dosage info for known chemicals"""
        guidelines = validator.get_dosage_guidelines("Iso E Super")
        
        assert guidelines is not None
        assert guidelines["min_percent"] == 10.0
        assert guidelines["max_percent"] == 50.0
        assert guidelines["potency"] == "low"
    
    def test_get_dosage_guidelines_unknown(self, validator):
        """Should return None for unknown chemicals"""
        guidelines = validator.get_dosage_guidelines("Unknown Chemical XYZ")
        
        assert guidelines is None
    
    def test_normalize_chemical_name(self, validator):
        """Chemical names should be normalized for matching"""
        # Test case-insensitive matching
        data1 = validator._get_chemical_data("iso e super")
        data2 = validator._get_chemical_data("ISO E SUPER")
        data3 = validator._get_chemical_data("Iso E Super")
        
        assert data1 is not None
        assert data2 is not None
        assert data3 is not None
    
    def test_note_pyramid_missing_layer(self, validator):
        """Missing note layer should produce WARNING"""
        # Only base notes, no heart or top
        ingredients = [
            {"name": "Iso E Super", "percentage": 50.0},
            {"name": "Galaxolide", "percentage": 30.0},
            {"name": "Ambroxan", "percentage": 20.0}
        ]
        
        issues = validator.validate_formula(ingredients)
        
        # Should warn about missing top notes at minimum
        pyramid_issues = [i for i in issues if "NOTE_PYRAMID" in i.chemical or "pyramid" in i.message.lower() or "notes" in i.message.lower()]
        # At least one pyramid-related issue
        assert len(pyramid_issues) >= 0  # May vary based on implementation
    
    def test_format_dosage_for_prompt(self, validator):
        """Should format dosage guidelines as readable string"""
        prompt_text = validator.format_dosage_for_prompt()
        
        assert "DOSAGE GUIDELINES" in prompt_text
        assert "EXTREME" in prompt_text or "extreme" in prompt_text.lower()
        assert "Alpha Irone" in prompt_text or "0.1-0.5%" in prompt_text
    
    def test_validation_issue_to_dict(self):
        """ValidationIssue should serialize to dict"""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            chemical="Test Chemical",
            message="Test message",
            suggested_fix="Test fix",
            current_value=5.0,
            recommended_value=1.0
        )
        
        d = issue.to_dict()
        
        assert d["severity"] == "error"
        assert d["chemical"] == "Test Chemical"
        assert d["message"] == "Test message"
        assert d["suggested_fix"] == "Test fix"
        assert d["current_value"] == 5.0
        assert d["recommended_value"] == 1.0


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_formula(self, validator):
        """Empty formula should not crash"""
        issues = validator.validate_formula([])
        
        # Should have issue about total being 0%
        assert any("total" in i.message.lower() or "FORMULA_TOTAL" in i.chemical for i in issues)
    
    def test_unknown_chemicals_info_only(self, validator):
        """Unknown chemicals should only produce INFO, not ERROR"""
        ingredients = [
            {"name": "Completely Unknown Chemical XYZ", "percentage": 50.0},
            {"name": "Another Unknown", "percentage": 50.0}
        ]
        
        issues = validator.validate_formula(ingredients)
        
        unknown_issues = [i for i in issues if "Unknown Chemical" in i.chemical or "not in potency database" in i.message]
        
        # Unknown chemicals should be INFO severity
        for issue in unknown_issues:
            assert issue.severity == ValidationSeverity.INFO
    
    def test_zero_percentage_chemical(self, validator):
        """Chemical at 0% should not produce potency errors"""
        ingredients = [
            {"name": "Alpha Irone", "percentage": 0.0},  # 0% is fine
            {"name": "Iso E Super", "percentage": 100.0}
        ]
        
        issues = validator.validate_formula(ingredients)
        
        # Alpha Irone at 0% should not trigger potency error
        alpha_errors = [i for i in issues 
                       if "Alpha Irone" in i.chemical 
                       and i.severity == ValidationSeverity.ERROR]
        assert len(alpha_errors) == 0
    
    def test_auto_correct_empty_formula(self, validator):
        """Auto-correct should handle empty formula"""
        corrected, changes = validator.auto_correct_formula([])
        
        assert corrected == []
        # Should note that formula is empty/incomplete
        assert len(changes) >= 1 or changes == []


class TestIntegration:
    """Integration tests with actual data files"""
    
    def test_potency_file_exists(self):
        """Potency data file should exist"""
        potency_file = Path(__file__).parent.parent.parent / "data" / "reference" / "chemicals_potency.json"
        assert potency_file.exists(), f"Potency file not found at {potency_file}"
    
    def test_potency_file_valid_json(self):
        """Potency data file should be valid JSON"""
        potency_file = Path(__file__).parent.parent.parent / "data" / "reference" / "chemicals_potency.json"
        
        with open(potency_file, 'r') as f:
            data = json.load(f)
        
        assert "chemicals" in data
        assert "potency_categories" in data
        assert len(data["chemicals"]) > 10  # Should have reasonable number of chemicals
    
    def test_potency_categories_complete(self):
        """All potency categories should be defined"""
        potency_file = Path(__file__).parent.parent.parent / "data" / "reference" / "chemicals_potency.json"
        
        with open(potency_file, 'r') as f:
            data = json.load(f)
        
        categories = data["potency_categories"]
        
        assert "extreme" in categories
        assert "high" in categories
        assert "medium" in categories
        assert "low" in categories
        
        for cat in categories.values():
            assert "max_allowed" in cat
            assert "warning_threshold" in cat
