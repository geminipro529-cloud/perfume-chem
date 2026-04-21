import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sys, io

# Fix stdout to handle potential Unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PROJECT_ROOT = Path(".").resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Formula and weight definitions (re-pasting to be self-contained)
FORMULA = {
    # --- TOP REGISTER (600µL) ---
    "Cedrat FCF oil Sicilian": 280,   
    "Linalool": 120,                   
    "Aldehyde C12 MNA": 50,           
    "Rose Oxide": 40,                  
    "Scentenal": 30,                   
    "Neroli EO": 60,                   
    "Petitgrain EO": 20,              

    # --- HEART: OPUS V IRIS ENGINE (3270µL) ---
    "Alpha Irone": 750,                
    "Orivone": 130,                    
    "Orris F-TEC": 170,               
    "Alpha Isomethyl Ionone": 250,    
    "I-IRIS F-TEC": 150,              
    "Alpha Ionone": 100,              
    "Beta Ionone": 70,                
    "Allyl Ionone": 30,               
    "Dihydro Beta Ionone": 100,       
    "Irotyl": 50,                      
    "Ultralia": 40,                    
    "Hedione HC": 1400,               
    "Violet Fleuressence": 30,        

    # --- BASE: CRYSTALLINE STRUCTURE (3430µL) ---
    "Iso E Super": 1200,              
    "Ambrox Super": 200,              
    "Amberwood F": 100,               
    "Norlimbanol Dextro": 80,         
    "Clearwood": 230,                  
    "Hexyl Salicylate": 400,          
    "Romandolide": 450,               
    "Ethylene Brassylate": 400,       
    "Habanolide": 100,                
    "Musk Ketone": 50,                
    "Cashmeran": 100,                 
    "Benzyl Benzoate": 80,            
    "Javanol": 80,                     
    "Ebanol": 90,                      
    "Patchouli EO": 30,               
}
DILUTIONS = {
    "Aldehyde C12 MNA": 0.01,
    "Rose Oxide": 0.01,
    "Scentenal": 0.01,
    "Alpha Irone": 0.30,
    "Ambrox Super": 0.30,
    "Musk Ketone": 0.10,
    "Cashmeran": 0.20,
}

from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.synergy_graph import SynergyGraph
from engine.ingredient_catalog import load_ingredient_catalog_index

def run_scoring():
    info = FormulaInfo(
        number=0,
        name="Opus V Iris Crystalline Premiere v4", 
        ingredients=FORMULA,
        dilutions=DILUTIONS,
        concentrate_ml=7.5
    )
    fv = formula_to_vector(info)
    sg = SynergyGraph()
    sg.build(material_names=list(FORMULA.keys()))
    
    # Simple scorer since it didn't accept ingredient_catalog
    scorer = FormulaScorer(synergy_graph=sg)
    scores = scorer.score(fv)
    
    # 1. Output basic scores and character radar
    print("--- SCORING RESULTS ---")
    print(f"Geometric total: {scores.get('geometric_total', 0):.1f}")
    
    print("\n[Axis Scores]")
    for k in sorted(scores.keys()):
        if k.endswith("_score") or k in ["sillage", "longevity", "transparency", "complexity"]:
             print(f"{k:25s}: {scores[k]:.1f}")

    if "character_radar" in scores:
        print("\n[Character Radar]")
        radar = scores["character_radar"]
        for rk, rv in sorted(radar.items(), key=lambda x:x[1], reverse=True):
            print(f"{rk:20s}: {rv:.1f}")

    # 2. Output filler if present
    if "filler_lines" in scores:
        print("\n[FILLER LINES]")
        for line in scores["filler_lines"]: print(line)

    # 3. Handle Luxury Breakdown separately by looking up catalog
    print("\n[Luxury Breakdown]")
    cat_idx = load_ingredient_catalog_index()
    premium_count = 0
    rich_mats = []
    
    # We need to find materials that have is_premium = True
    for mat_name in FORMULA:
        # Check if mat_name in catalog
        entry = cat_idx.get(mat_name)
        if entry:
            # Check for premium
            if hasattr(entry, 'is_premium') and getattr(entry, 'is_premium'):
                premium_count += 1
                rich_mats.append(mat_name)
    
    print(f"Distinct chars: {len(FORMULA)}")
    print(f"Premium fraction: {(premium_count/len(FORMULA))*100:.1f}%")
    print("Rich materials list:")
    for m in sorted(rich_mats):
        print(f"  - {m}")

run_scoring()
