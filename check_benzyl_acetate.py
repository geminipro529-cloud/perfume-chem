"""
Query ingredient intelligence for Benzyl Acetate and display all properties.
"""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.ingredient_intelligence import get_profile, DIMENSIONS, _PROFILES
from engine.odor_thresholds import ODT_DATA
from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.cost_analysis import MATERIAL_COSTS_PER_KG

def display_ingredient_intelligence(material_name: str):
    """Display comprehensive intelligence for a material."""
    print("=" * 80)
    print(f"INGREDIENT INTELLIGENCE REPORT: {material_name.upper()}")
    print("=" * 80)
    
    # Get profile from ingredient intelligence
    profile = get_profile(material_name)
    
    if profile is None:
        print(f"\nNo profile found for '{material_name}'")
        return
    
    # Basic Info
    print("\nBASIC INFORMATION")
    print("-" * 40)
    print(f"  Name:          {profile.name}")
    print(f"  Note:          {profile.note}")
    print(f"  Role:          {profile.role}")
    print(f"  Texture:       {profile.texture}")
    print(f"  Dilution:      {profile.dilution * 100:.0f}%")
    
    # Character Dimensions (13-dimension radar)
    print("\nCHARACTER DIMENSIONS (0-10 scale)")
    print("-" * 40)
    for dim in DIMENSIONS:
        val = profile.character.get(dim, 0.0)
        bar = "#" * int(val) + "-" * (10 - int(val))
        print(f"  {dim:15s}: {val:5.1f} {bar}")
    
    # Dominant character
    dominant = profile.dominant_character()
    tags = profile.character_tags(threshold=4.0)
    print(f"\n  Dominant:      {dominant}")
    print(f"  Tags (>=4.0):  {', '.join(tags) if tags else 'None'}")
    
    # Physical Properties
    print("\nPHYSICAL PROPERTIES")
    print("-" * 40)
    print(f"  Molecular Weight:    {profile.mw:.2f} g/mol" if profile.mw else "  Molecular Weight:    N/A")
    print(f"  Vapor Pressure:      {profile.vp:.3f} Pa" if profile.vp else "  Vapor Pressure:      N/A")
    print(f"  ClogP:               {profile.clogp:.2f}" if profile.clogp else "  ClogP:               N/A")
    print(f"  ODT (air):           {profile.odt:.2f} ppb" if profile.odt else "  ODT (air):           N/A")
    print(f"  ODT (ethanol):       {profile.odt_ppm:.2f} ppm" if profile.odt_ppm else "  ODT (ethanol):       N/A")
    
    # Extended scientific properties
    print("\nSCIENTIFIC EXTENSIONS")
    print("-" * 40)
    print(f"  Activity Coeff (y):  {profile.activity_coef:.2f}")
    print(f"  Hedonic Valence:     {profile.hedonic:+.2f} (-5 to +5)")
    print(f"  OR Family:           {profile.or_family or 'Not classified'}")
    
    # Relationships
    print("\nRELATIONSHIPS")
    print("-" * 40)
    if profile.synergies:
        print(f"  Synergies:     {', '.join(profile.synergies)}")
    else:
        print(f"  Synergies:     None listed")
        
    if profile.avoid:
        print(f"  Avoid:         {', '.join(profile.avoid)}")
    else:
        print(f"  Avoid:         None listed")
    
    # Cross-reference with other data sources
    print("\nCROSS-REFERENCED DATA")
    print("-" * 40)
    
    # Odor Thresholds
    key = material_name.lower()
    if key in ODT_DATA:
        odt = ODT_DATA[key]
        print(f"  Odor Threshold (air): {odt.get('odt_air', 'N/A')} ppb")
        print(f"  Odor Threshold (eth): {odt.get('odt_eth', 'N/A')} ppm")
        print(f"  Character:            {odt.get('char', 'N/A')}")
    
    # IFRA Safety
    if material_name in IFRA_CAT4_LIMITS:
        print(f"  IFRA Limit:           {IFRA_CAT4_LIMITS[material_name]}%")
    else:
        print(f"  IFRA Limit:           Not restricted")
    
    # Cost Analysis
    if key in MATERIAL_COSTS_PER_KG:
        print(f"  Cost:                 ${MATERIAL_COSTS_PER_KG[key]:.2f}/kg")
    
    print("\n" + "=" * 80)
    print("END OF REPORT")
    print("=" * 80)


if __name__ == "__main__":
    # Query Benzyl Acetate
    display_ingredient_intelligence("Benzyl Acetate")
    
    # Also show raw profile data
    print("\n\nRAW PROFILE DATA (_PROFILES)")
    print("=" * 80)
    if "Benzyl Acetate" in _PROFILES:
        import json
        print(json.dumps(_PROFILES["Benzyl Acetate"], indent=2))
