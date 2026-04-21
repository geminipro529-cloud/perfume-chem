"""Chemistry calculations for perfumery"""

from typing import Dict, List, Any, Optional
from app.core.exceptions import (
    DilutionCalculationError,
    IFRAComplianceError,
    FormulaBalanceError
)


def calculate_dilution(
    concentrate_volume: float,
    concentrate_percent: float,
    target_percent: float
) -> Dict[str, float]:
    """
    Calculate dilution using C1V1 = C2V2
    
    Args:
        concentrate_volume: Volume of concentrated material (ml)
        concentrate_percent: Concentration of material (%)
        target_percent: Desired final concentration (%)
    
    Returns:
        Dictionary with total_volume and solvent_to_add
    
    Raises:
        DilutionCalculationError: If calculation is invalid
    """
    if target_percent >= concentrate_percent:
        raise DilutionCalculationError(
            "Target concentration must be less than concentrate concentration"
        )
    
    if target_percent <= 0 or concentrate_percent <= 0:
        raise DilutionCalculationError(
            "Concentrations must be positive"
        )
    
    # C1V1 = C2V2
    # V2 = (C1 * V1) / C2
    total_volume = (concentrate_percent * concentrate_volume) / target_percent
    solvent_to_add = total_volume - concentrate_volume
    
    return {
        "concentrate_volume": concentrate_volume,
        "total_volume": total_volume,
        "solvent_to_add": solvent_to_add,
        "final_concentration": target_percent
    }


def calculate_drops_to_ml(drops: int, drop_size: float = 0.05) -> float:
    """
    Convert drops to milliliters
    
    Args:
        drops: Number of drops
        drop_size: Size of each drop in ml (default 0.05ml)
    
    Returns:
        Volume in milliliters
    """
    return drops * drop_size


def calculate_ml_to_drops(volume_ml: float, drop_size: float = 0.05) -> int:
    """
    Convert milliliters to drops
    
    Args:
        volume_ml: Volume in milliliters
        drop_size: Size of each drop in ml (default 0.05ml)
    
    Returns:
        Number of drops (rounded)
    """
    return round(volume_ml / drop_size)


def validate_formula_balance(ingredients: List[Dict[str, Any]]) -> bool:
    """
    Validate that formula ingredients sum to 100%
    
    Args:
        ingredients: List of ingredients with 'percentage' field
    
    Returns:
        True if balanced
    
    Raises:
        FormulaBalanceError: If percentages don't sum to ~100%
    """
    total = sum(ing.get('percentage', 0) for ing in ingredients)
    
    # Allow small tolerance for rounding errors
    if not (99.9 <= total <= 100.1):
        raise FormulaBalanceError(total)
    
    return True


def validate_ifra_compliance(
    ingredients: List[Dict[str, Any]],
    category: int = 4
) -> List[str]:
    """
    Check IFRA compliance for a formula
    
    Args:
        ingredients: List of ingredients with ifra_limit and percentage
        category: IFRA category (1-11, default 4 for fine fragrance)
    
    Returns:
        List of violation descriptions (empty if compliant)
    
    Raises:
        IFRAComplianceError: If violations found
    """
    violations = []

    for ing in ingredients:
        limit = ing.get('ifra_max_level')
        actual = ing.get('percentage', 0)

        if limit is not None and actual > limit:
            violation_msg = (
                f"{ing.get('name', 'Unknown')}: {actual:.2f}% "
                f"exceeds IFRA cat {category} limit of {limit}%"
            )
            violations.append(violation_msg)
    
    if violations:
        raise IFRAComplianceError(
            ingredient=violations[0].split(':')[0],
            limit=0,  # Will be overridden by message
            actual=0
        )
    
    return violations


def calculate_formula_cost(
    ingredients: List[Dict[str, Any]],
    total_volume_ml: float = 100
) -> Optional[float]:
    """
    Calculate total cost of a formula
    
    Args:
        ingredients: List with 'percentage' and 'cost_per_gram'
        total_volume_ml: Total volume to calculate for
    
    Returns:
        Total cost, or None if cost data incomplete
    """
    # Average density for fragrance compounds ~0.9 g/ml
    density = 0.9
    total_mass_g = total_volume_ml * density
    
    total_cost = 0.0
    
    for ing in ingredients:
        percentage = ing.get('percentage', 0) / 100
        cost_per_g = ing.get('cost_per_gram')
        
        if cost_per_g is None:
            return None  # Can't calculate without all costs
        
        mass_g = total_mass_g * percentage
        total_cost += mass_g * cost_per_g
    
    return total_cost


def calculate_note_distribution(
    ingredients: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate distribution of top/heart/base notes
    
    Args:
        ingredients: List with 'volatility' and 'percentage' fields
    
    Returns:
        Dictionary with percentages for each note tier
    """
    distribution = {
        "top": 0.0,
        "heart": 0.0,
        "base": 0.0
    }
    
    for ing in ingredients:
        volatility = ing.get('volatility', '').lower()
        percentage = ing.get('percentage', 0)

        if 'top' in volatility:
            distribution['top'] += percentage
        elif 'heart' in volatility or 'middle' in volatility:
            distribution['heart'] += percentage
        elif 'base' in volatility:
            distribution['base'] += percentage
    
    return distribution


def estimate_longevity(note_distribution: Dict[str, float]) -> float:
    """
    Estimate perfume longevity based on note distribution
    
    Args:
        note_distribution: Dict with top/heart/base percentages
    
    Returns:
        Estimated longevity in hours
    """
    # Simple heuristic: more base notes = longer lasting
    # Top: 0.5-2 hours, Heart: 2-6 hours, Base: 6-24 hours
    
    top_percent = note_distribution.get('top', 0) / 100
    heart_percent = note_distribution.get('heart', 0) / 100
    base_percent = note_distribution.get('base', 0) / 100
    
    weighted_longevity = (
        top_percent * 1.5 +
        heart_percent * 4.0 +
        base_percent * 12.0
    )
    
    return max(1.0, min(24.0, weighted_longevity))


def estimate_sillage(
    top_percent: float,
    concentration: float,
    avg_vp: float | None = None,
    avg_mw: float | None = None,
) -> str:
    """
    Estimate sillage based on top notes, concentration, and optional
    physical-chemistry data (vapor pressure / molecular weight).
    
    Args:
        top_percent: Percentage of top notes
        concentration: Total fragrance concentration
        avg_vp: Average vapor pressure of the formula (Pa), optional
        avg_mw: Average molecular weight of the formula, optional
    
    Returns:
        Sillage description
    """
    score = (top_percent / 100 * 0.6) + (concentration / 100 * 0.4)

    # When physical data is available, blend in a VP/MW-based factor
    if avg_vp is not None and avg_mw is not None and avg_mw > 0:
        import math
        phys_factor = avg_vp / math.sqrt(avg_mw)
        # Normalize: typical range ~0.0001 (base) to 0.3 (citrus)
        phys_score = min(phys_factor / 0.15, 1.0)
        # Blend 70% note-based, 30% physical
        score = score * 0.7 + phys_score * 0.3
    
    if score < 0.15:
        return "intimate"
    elif score < 0.30:
        return "moderate"
    elif score < 0.50:
        return "strong"
    else:
        return "enormous"
