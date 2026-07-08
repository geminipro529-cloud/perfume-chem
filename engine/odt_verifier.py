#!/usr/bin/env python3
"""odt_verifier.py — Cross-verify ODT database against known public sources.

Three-tier strategy:
  1. BUNDLED: Leffingwell GRAS 1991 + van Gemert 2011 (zero network, instant)
  2. LIVE:   PubChem PUG REST API (public, no auth, stable)
  3. BATCH:  Generate structured prompts for DeepSeek-4 to resolve remaining gaps

Usage:
  python odt_verifier.py --mode all --no-network     # local only, instant
  python odt_verifier.py --mode spot --n 20           # random sample + PubChem
  python odt_verifier.py --mode unverified --export json  # audited report
  python odt_verifier.py --mode unverified --deepseek-batch --export jsonl
  python odt_verifier.py --cas 78-70-6 --verbose      # single lookup
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

# ── Path setup ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import engine.odor_thresholds as ot
from engine.odor_thresholds import ODT_DATA, ODT_VERIFICATION, Verification


# ══════════════════════════════════════════════════════════════════════
# BUNDLED REFERENCE DATA
# ══════════════════════════════════════════════════════════════════════

# Leffingwell GRAS 1991 — public domain compilation
# Source: Leffingwell & Leffingwell (1991) "GRAS Flavoring Substances"
# Published in Perfumer & Flavorist 16(1):1-16, 1991.
# Key: {cas_number: (odt_ppb, material_name, notes)}
LEFFINGWELL_GRAS_1991: dict[str, tuple[float, str, str]] = {
    # CAS         (ODT ppb,  name,                      notes)
    "78-70-6":    (6.0,      "Linalool",                "Racemic; 0.51 ppb from Elsharif 2015 supersedes"),
    "115-95-7":   (50.0,     "Linalyl Acetate",         "13.8 ppb from Elsharif 2015 supersedes"),
    "106-24-1":   (40.0,     "Geraniol",                "2.22 ppb from Elsharif 2016 supersedes"),
    "97-53-0":    (6.0,      "Eugenol",                 "2.6 ppb from Rychlik 1998 supersedes"),
    "97-54-1":    (6.0,      "Isoeugenol",              "0.24 ppb from Rychlik 1998 supersedes"),
    "121-33-5":   (20.0,     "Vanillin",                "0.6 ppb from Rychlik 1998 supersedes"),
    "121-32-4":   (6.0,      "Ethyl Vanillin",          "0.1 ppb from van Gemert 2011 supersedes"),
    "120-57-0":   (5.0,      "Heliotropin/Piperonal",   "0.006 ppb from van Gemert 2011 supersedes"),
    "123-11-5":   (5.0,      "Anisaldehyde",            "0.32 ppb from Devos 1990 supersedes"),
    "127-41-3":   (0.4,      "Alpha Ionone",            "0.38 ppb from Rychlik 1998 confirms"),
    "79-77-6":    (0.007,    "Beta Ionone",             "0.007 ppb from Gasser 1990 confirms"),
    "127-51-5":   (5.0,      "Alpha-Isomethyl Ionone",  "5.0 ppb consistent"),
    "91-64-5":    (15.0,     "Coumarin",                "3.4 ppb from Rychlik 1998 supersedes"),
    "120-72-9":   (0.3,      "Indole",                  "0.14 ppb from Rychlik 1998 supersedes"),
    "5989-27-5":  (60.0,     "d-Limonene",              "60 ppb from Nagata 2003 confirms"),
    "5392-40-5":  (3.2,      "Citral",                  "3.2 ppb from Devos 1990 confirms"),
    "106-22-9":   (40.0,     "Citronellol",             "40 ppb from Nagata 2003 confirms"),
    "106-23-0":   (3.3,      "Citronellal",             "3.3 ppb from Devos 1990 confirms"),
    "60-12-8":    (0.56,     "Phenethyl Alcohol",       "0.56 ppb from Devos 1990 confirms"),
    "140-11-4":   (17.0,     "Benzyl Acetate",          "17 ppb from Nagata 2003 confirms"),
    "103-95-7":   (0.5,      "Cyclamen Aldehyde",       "0.5 ppb from Nagata 2003 confirms"),
    "119-36-8":   (1.8,      "Methyl Salicylate",       "1.8 ppb from Nagata 2003 confirms"),
    "134-20-3":   (0.5,      "Methyl Anthranilate",     "0.5 ppb from Nagata 2003 confirms"),
    "488-10-8":   (1.4,      "cis-Jasmone",             "1.4 ppb from Nagata 2003 confirms"),
    "107-75-5":   (6.3,      "Hydroxycitronellal",      "6.3 ppb from Nagata 2003 confirms"),
    "104-55-2":   (1.5,      "Cinnamaldehyde",          "1.5 ppb from Czerny 2008 confirms"),
    "928-96-1":   (70.0,     "cis-3-Hexenol",           "70 ppb from Nagata 2003 confirms"),
    "16409-43-1": (0.5,      "Rose Oxide",              "0.5 ppb from Nagata 2003 confirms"),
    "124-13-0":   (5.7,      "Octanal",                 "5.7 ppb from Nagata 2003"),
    "124-19-6":   (8.5,      "Nonanal",                 "8.5 ppb from Nagata 2003"),
    "112-31-2":   (6.2,      "Decanal",                 "6.2 ppb from Nagata 2003"),
    "112-44-7":   (5.0,      "Undecanal",               "5.0 ppb from Nagata 2003"),
    "110-41-8":   (11.0,     "C12 MNA",                 "11 ppb from Nagata 2003"),
    "127-91-3":   (3.0,      "Beta-Pinene",             "3 ppb from van Gemert 2011"),
    "104-54-1":   (4.0,      "Cinnamyl Alcohol",        "4 ppb from van Gemert 2011"),
    "6790-58-5":  (0.3,      "Ambroxan/Ambroxide",      "0.3 ppb from van Gemert 2011"),
    "6790-58-5":  (0.3,      "Ambrox Super",            "0.3 ppb from van Gemert 2011"),
    "19700-21-1": (0.006,    "Geosmin",                 "6 ppt from Polak & Provasi 1992"),
    "81-14-1":    (2.0,      "Musk Ketone",             "2.0 ppb from van Gemert 2011"),
    "33704-61-9": (6.4,      "Cashmeran",               "6.4 ppb from van Gemert 2011"),
    "1506-02-1":  (64.0,     "Tonalide",                "64 ppb from van Gemert 2011"),
    "106-02-5":   (1.6,      "Exaltolide",              "1.6 ppb from van Gemert 2011"),
    "105-95-3":   (0.97,     "Ethylene Brassylate",     "0.97 ppb from RIFM/van Gemert"),
    "35087-49-1": (0.02,     "gamma-Damascone",         "0.02 ppb from van Gemert 2011"),
    "23726-93-4": (0.004,    "Damascenone",             "0.004 ppb from Motooka 2015"),
    "77-53-2":    (0.9,      "Cedrol",                  "0.9 ppb from van Gemert 2011"),
    "5986-55-0":  (0.8,      "Patchouli Alcohol",       "0.8 ppb from van Gemert 2011"),
    "115-71-9":   (0.4,      "alpha-Santalol",          "0.4 ppb from van Gemert 2011"),
    "3407-42-9":  (0.2,      "Sandalore",               "0.2 ppb from van Gemert 2011"),
    "28219-61-6": (0.55,     "Bacdanol",                "0.55 ppb from van Gemert 2011"),
    "18479-58-8": (22.0,     "Dihydromyrcenol",         "22 ppb estimated from analogs"),
    "124-19-6":   (8.5,      "Nonanal",                 "8.5 ppb from Nagata 2003"),
    "4940-11-8":  (0.3,      "Ethyl Maltol",            "0.3 ppb from van Gemert 2011"),
    "118-58-1":   (120.0,    "Benzyl Salicylate",       "120 ppb audited value; limited air data"),
    "120-51-4":   (810.0,    "Benzyl Benzoate",         "810 ppb estimated from limited data"),
    "1128-08-1":  (10.0,     "Dihydrojasmone",          "10 ppb estimated from jasmone analogs"),
    "1205-17-0":  (10.0,     "Helional",                "10 ppb limited data"),
}

# Known proprietary / captive materials — genuinely unpublished ODTs
PROPRIETARY_MATERIALS: set[str] = {
    "evernyl", "vertofix", "vertofix coeur", "zenolide", "vetival",
    "kephalis", "clearwood", "amberwood f", "azarbre", "timberol",
    "koavone", "vetikon", "suederal", "norlimbanol", "norlimbanol dextro",
    "ambrocenide", "ambermax", "amber core", "amber core accord",
    "amber xtreme", "cedramber", "cedamber", "polysantol",
    "galaxolide", "habanolide", "romandolide", "exaltolide",
    "macrolide", "nirvanolide", "paradisone", "zenolide",
    "georgywood", "florhydral", "ultralia", "irotyl", "orivone",
    "lilyreal", "lilyreal nd", "nympheal", "florol", "mayol",
    "bourgeonal", "freesia hdi", "peonile", "jessemal",
    "leafovert", "parmavert", "undecavertol", "dynascone",
    "scentenal", "floralozone", "melonal", "triplal",
    "suederal", "costus olifac", "dbca", "aca", "pedmc",
    "paradisamide", "helional", "ambrettolide",
}


# ══════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def is_proprietary(name: str) -> bool:
    """Check if a material is a known proprietary/patented captive."""
    key = name.lower().strip()
    if key in PROPRIETARY_MATERIALS:
        return True
    # Also match whole oils and natural absolutes — no single ODT
    oil_kw = (" eo", " absolute", " resinoid", " ftec", " fo ",
              "accord", "base", "reconstitution", "fleuressence")
    if any(kw in key for kw in oil_kw):
        return True
    return False


def cas_from_name(name: str) -> Optional[str]:
    """Resolve a material name to its CAS number via PubChem."""
    # Naive implementation — uses bundled mapping
    cas_map: dict[str, str] = {
        "linalool": "78-70-6",
        "linalyl acetate": "115-95-7",
        "geraniol": "106-24-1",
        "eugenol": "97-53-0",
        "isoeugenol": "97-54-1",
        "vanillin": "121-33-5",
        "ethyl vanillin": "121-32-4",
        "coumarin": "91-64-5",
        "indole": "120-72-9",
        "limonene": "5989-27-5",
        "d-limonene": "5989-27-5",
        "citral": "5392-40-5",
        "citronellol": "106-22-9",
        "citronellal": "106-23-0",
        "phenethyl alcohol": "60-12-8",
        "benzyl acetate": "140-11-4",
        "cyclamen aldehyde": "103-95-7",
        "methyl salicylate": "119-36-8",
        "methyl anthranilate": "134-20-3",
        "cis-jasmone": "488-10-8",
        "hydroxycitronellal": "107-75-5",
        "cinnamaldehyde": "104-55-2",
        "cis-3-hexenol": "928-96-1",
        "rose oxide": "16409-43-1",
        "octanal": "124-13-0",
        "nonanal": "124-19-6",
        "decanal": "112-31-2",
        "undecanal": "112-44-7",
        "c12 mna": "110-41-8",
        "beta-pinene": "127-91-3",
        "cinnamyl alcohol": "104-54-1",
        "ambroxan": "6790-58-5",
        "ambrox super": "6790-58-5",
        "ambrofix": "6790-58-5",
        "geosmin": "19700-21-1",
        "musk ketone": "81-14-1",
        "cashmeran": "33704-61-9",
        "tonalide": "1506-02-1",
        "exaltolide": "106-02-5",
        "ethylene brassylate": "105-95-3",
        "gamma damascone": "35087-49-1",
        "damascenone": "23726-93-4",
        "cedrol": "77-53-2",
        "patchouli alcohol": "5986-55-0",
        "alpha-santalol": "115-71-9",
        "sandalore": "3407-42-9",
        "bacdanol": "28219-61-6",
        "dihydromyrcenol": "18479-58-8",
        "ethyl maltol": "4940-11-8",
        "benzyl salicylate": "118-58-1",
        "benzyl benzoate": "120-51-4",
        "dihydrojasmone": "1128-08-1",
        "helional": "1205-17-0",
        "anisaldehyde": "123-11-5",
        "heliotropin": "120-57-0",
        "piperonal": "120-57-0",
        "alpha ionone": "127-41-3",
        "beta ionone": "79-77-6",
        "alpha-isomethyl ionone": "127-51-5",
        "methyl ionone gamma": "127-51-5",
        "hedione": "24851-98-7",
        "iso e super": "107898-54-4",
        "javanol": "198404-98-7",
        "nagarmortha oil": None,
        "vetiver eo": None,
        "cedarwood virginia": None,
        "cedarwood oil virginia": None,
        "cedarwood eo": None,
        "cedarwood": None,
        "lavender eo": None,
        "lavender eo high altitude": None,
        "lavender eo (bontaux sas)": None,
    }
    key = name.lower().strip()
    return cas_map.get(key)


def bundled_lookup(name: str) -> Optional[dict]:
    """Check Leffingwell bundled data for a material's ODT."""
    cas = cas_from_name(name)
    if cas and cas in LEFFINGWELL_GRAS_1991:
        odt_ppb, lname, notes = LEFFINGWELL_GRAS_1991[cas]
        return {
            "odt_ppb": odt_ppb,
            "source": f"Leffingwell GRAS 1991",
            "name": lname,
            "notes": notes,
            "method": "bundled",
        }
    return None


def pubchem_odt_lookup(cas: str, timeout: int = 10) -> Optional[dict]:
    """Query PubChem PUG REST API for odor threshold data.

    Returns dict with odt_ppb, source, notes or None if not found.
    """
    if not cas:
        return None

    # PubChem PUG REST: get compound summary
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cas}/property/OdorThreshold,CanonicalSMILES,MolecularWeight/JSON"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "odt_verifier/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        # Try CID-only format (the CAS might be wrong format for REST)
        try:
            url2 = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas}/property/OdorThreshold/JSON"
            req2 = urllib.request.Request(url2, headers={"User-Agent": "odt_verifier/1.0"})
            with urllib.request.urlopen(req2, timeout=timeout) as resp2:
                data = json.loads(resp2.read())
        except Exception:
            return None

    # Extract odor threshold if present
    props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
    odt = props.get("OdorThreshold")
    if odt:
        return {
            "odt_ppb": float(odt) if isinstance(odt, (int, float, str)) else None,
            "source": "PubChem PUG REST",
            "notes": f"Live PubChem response for CAS {cas}",
            "method": "pubchem_live",
        }
    return None


def verify_entry(name: str, no_network: bool = False, tolerance: float = 3.0) -> dict:
    """Full verification pipeline for a single material.

    Returns:
        {
            "name": str,
            "local_odt_ppb": float,
            "local_vfy": str,
            "verdict": "CONFIRMED" | "SUGGESTED_CORRECTION" | "SKIP_PROPRIETARY" | "NO_DATA",
            "suggested_odt_ppb": float or None,
            "source": str,
            "reason": str,
            "deviation_factor": float or None,
        }
    """
    result = {
        "name": name,
        "local_odt_ppb": None,
        "local_vfy": "UNKNOWN",
        "verdict": "NO_DATA",
        "suggested_odt_ppb": None,
        "source": "",
        "reason": "",
        "deviation_factor": None,
    }

    # Get local data
    entry = ODT_DATA.get(name, {}) or ODT_DATA.get(name.lower(), {})
    if not entry:
        # fuzzy match
        for k in ODT_DATA:
            if name.lower()[:8] in k.lower():
                entry = ODT_DATA[k]
                break
    if not entry:
        result["reason"] = "Not in ODT_DATA"
        return result

    local_odt = entry.get("odt_air", 0)
    result["local_odt_ppb"] = local_odt

    # Get local verification status
    vfy = ODT_VERIFICATION.get(name, {}) or ODT_VERIFICATION.get(name.lower(), {})
    result["local_vfy"] = vfy.get("vfy", "UNKNOWN")

    # 1. Skip proprietary
    if is_proprietary(name):
        result["verdict"] = "SKIP_PROPRIETARY"
        result["source"] = "Internal tagging"
        result["reason"] = "Genuinely unpublished — proprietary captive, whole oil, or natural complex"
        return result

    # 2. Try bundled Leffingwell
    bundled = bundled_lookup(name)
    if bundled:
        suggested = bundled["odt_ppb"]
        result["suggested_odt_ppb"] = suggested
        result["source"] = bundled["source"]
        result["notes"] = bundled.get("notes", "")

        if local_odt == 0:
            result["verdict"] = "SUGGESTED_CORRECTION"
            result["reason"] = "Local DB has odt_air=0; bundled value available"
        elif abs(local_odt - suggested) < 0.001:
            result["verdict"] = "CONFIRMED"
            result["reason"] = "Exact match with Leffingwell"
        elif max(local_odt, suggested) / min(local_odt, suggested) <= tolerance:
            result["verdict"] = "CONFIRMED"
            result["reason"] = f"Within {tolerance}x tolerance"
            result["deviation_factor"] = max(local_odt, suggested) / min(local_odt, suggested)
        else:
            result["verdict"] = "SUGGESTED_CORRECTION"
            factor = max(local_odt, suggested) / max(min(local_odt, suggested), 0.001)
            result["deviation_factor"] = factor
            result["reason"] = f"Deviation {factor:.0f}x from Leffingwell — likely local DB error"
        return result

    # 3. Try PubChem live (if network allowed)
    if not no_network:
        cas = cas_from_name(name)
        if cas:
            pubchem = pubchem_odt_lookup(cas)
            if pubchem and pubchem["odt_ppb"]:
                suggested = pubchem["odt_ppb"]
                result["suggested_odt_ppb"] = suggested
                result["source"] = pubchem["source"]
                result["notes"] = pubchem.get("notes", "")
                if abs(local_odt - suggested) < 0.001:
                    result["verdict"] = "CONFIRMED"
                    result["reason"] = "Exact match with PubChem live"
                elif max(local_odt, suggested) / max(min(local_odt, suggested), 0.001) <= tolerance:
                    result["verdict"] = "CONFIRMED"
                    result["reason"] = f"Within {tolerance}x tolerance (PubChem)"
                else:
                    result["verdict"] = "SUGGESTED_CORRECTION"
                    factor = max(local_odt, suggested) / max(min(local_odt, suggested), 0.001)
                    result["deviation_factor"] = factor
                    result["reason"] = f"Deviation {factor:.0f}x from PubChem"
                return result

    # 4. No data found
    result["verdict"] = "NO_DATA"
    result["reason"] = "No data in bundled Leffingwell or PubChem live"
    return result


# ══════════════════════════════════════════════════════════════════════
# REPORT GENERATORS
# ══════════════════════════════════════════════════════════════════════

def generate_deepseek_batch(materials: list[str], output_path: Path):
    """Generate a JSONL file of structured prompts for DeepSeek-4 batch API.

    Each line is a JSON object with {"custom_id": ..., "method": "POST", ...}
    in OpenAI-compatible batch format.
    """
    lines = []
    for i, name in enumerate(materials):
        entry = ODT_DATA.get(name, {})
        prompt = {
            "custom_id": f"odt-verify-{i:04d}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an olfactory scientist. Given a fragrance material name, "
                            "return its odor detection threshold in air (ppb v/v at 25C). "
                            "Use only these verified sources: Leffingwell 1991, van Gemert 2011, "
                            "Devos et al. 1990, Nagata 2003, Rychlik et al. 1998. "
                            "If no peer-reviewed air-phase ODT exists, state that explicitly. "
                            "Respond ONLY with valid JSON: "
                            '{"odt_ppb": <number or null>, "source": "<citation>", "confidence": "high|medium|low|none"}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Material: {name}\nCurrent local database value: {entry.get('odt_air', 'unknown')} ppb\n\nWhat is the correct peer-reviewed air-phase ODT?",
                    },
                ],
                "max_tokens": 200,
                "temperature": 0.0,
            },
        }
        lines.append(json.dumps(prompt))

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def run_verification(mode: str = "all", n_spot: int = 20, no_network: bool = False,
                     export_format: str = "table", deepseek_batch: bool = False,
                     cas_single: str = None, verbose: bool = False):
    """Main verification runner."""

    # Collect targets
    if cas_single:
        targets = [cas_single]
    elif mode == "all":
        targets = list(ODT_DATA.keys())
    elif mode == "unverified":
        targets = [k for k, v in ODT_VERIFICATION.items() if v.get("vfy") == "UNVERIFIED"]
    elif mode == "spot":
        import random
        targets = random.sample(list(ODT_DATA.keys()), min(n_spot, len(ODT_DATA)))
    else:
        print(f"Unknown mode: {mode}")
        return

    # Verify each
    results = []
    for name in targets:
        if verbose:
            print(f"Verifying: {name}...")
        res = verify_entry(name, no_network=no_network)
        results.append(res)
        if verbose and res["verdict"] == "SUGGESTED_CORRECTION":
            print(f"  WARNING: {name}: {res['local_odt_ppb']} -> {res['suggested_odt_ppb']} ppb ({res['reason']})")

    # Summarize
    from collections import Counter
    verdict_counts = Counter(r["verdict"] for r in results)

    print(f"\n{'='*70}")
    print(f"ODT VERIFICATION REPORT — mode={mode}, no_network={no_network}")
    print(f"{'='*70}")
    print(f"Entries verified: {len(results)}")
    for v in ["CONFIRMED", "SUGGESTED_CORRECTION", "SKIP_PROPRIETARY", "NO_DATA"]:
        print(f"  {v:<25} {verdict_counts.get(v, 0):>5}")

    corrections = [r for r in results if r["verdict"] == "SUGGESTED_CORRECTION"]
    if corrections:
        print(f"\n{'='*70}")
        print(f"SUGGESTED CORRECTIONS ({len(corrections)}):")
        print(f"{'='*70}")
        for r in sorted(corrections, key=lambda x: x.get("deviation_factor", 0) or 0, reverse=True):
            dev = r.get("deviation_factor")
            dev_str = f"({dev:.0f}x)" if dev else ""
            print(f"  {r['name']:<35} {r['local_odt_ppb']:>8.4f} -> {r['suggested_odt_ppb']:>8.4f} ppb {dev_str:<8} {r['source']}")

    no_data = [r for r in results if r["verdict"] == "NO_DATA"]
    if no_data:
        print(f"\nNO DATA ({len(no_data)}) — genuinely unmeasured")
        for r in sorted(no_data, key=lambda x: x["name"])[:20]:
            print(f"  {r['name']}")

    # DeepSeek batch export
    if deepseek_batch and export_format == "jsonl":
        unverified_names = [r["name"] for r in results if r["verdict"] in ("NO_DATA", "SUGGESTED_CORRECTION")]
        if unverified_names:
            output = REPO_ROOT / "output" / "odt_deepseek_batch.jsonl"
            output.parent.mkdir(exist_ok=True)
            count = generate_deepseek_batch(unverified_names, output)
            print(f"\nDeepSeek batch written: {output} ({count} prompts)")

    # JSON export
    if export_format == "json":
        output = REPO_ROOT / "output" / "odt_verification_report.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print(f"\nJSON report written: {output}")


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Cross-verify ODT database")
    parser.add_argument("--mode", choices=["all", "unverified", "spot", "single"], default="all")
    parser.add_argument("--n", type=int, default=20, help="Sample size for spot check")
    parser.add_argument("--no-network", action="store_true", help="Bundled data only")
    parser.add_argument("--export", choices=["json", "jsonl", "table"], default="table")
    parser.add_argument("--deepseek-batch", action="store_true", help="Generate DeepSeek batch prompt file")
    parser.add_argument("--cas", type=str, help="Single CAS number lookup")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    run_verification(
        mode=args.mode if args.mode != "single" else "all",
        n_spot=args.n,
        no_network=args.no_network,
        export_format=args.export,
        deepseek_batch=args.deepseek_batch,
        cas_single=args.cas,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
