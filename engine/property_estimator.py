"""Fragment-based property estimation for perfumery materials.

Provides estimation of vapor pressure (VP), logP, odor detection threshold (ODT),
activity coefficient, and note tier from SMILES strings and chemical class
information.

Uses only Python stdlib — no RDKit, no OpenBabel, no external chemistry libraries.
Estimation methods:

  * **VP**: Stein-Brown-style group contribution from SMILES → boiling point →
    Clausius-Clapeyron VP at 25 °C.
  * **logP**: Wildman-Crippen-style atom contribution with proximity/ring corrections.
  * **ODT**: Class-bracketed lookup scaled by molecular weight.
  * **Activity coefficient**: Chemical-class lookup (AGENTS.md ranges).
  * **Note tier**: VP-threshold classification (top / heart / base).
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants — group contributions
# ---------------------------------------------------------------------------

# Contributions to the estimated boiling point (arbitrary "Tb units").
# Each functional-group occurrence adds this many units.
# Higher contribution → higher BP → lower VP.
_GROUP_BP_CONTRIB: dict[str, float] = {
    "aliphatic_c": 1.0,  # -CH3 / -CH2- / >CH-
    "aromatic_c": 1.5,  # aromatic carbon
    "olefin": 0.8,  # =CH- (C=C, not C=O)
    "hydroxyl": 10.0,  # -OH alcohol  (large effect: one OH ~ 6 extra carbons)
    "carboxyl": 10.0,  # -COOH
    "ester": 6.0,  # -C(=O)O-
    "amine": 6.0,  # -NH2
    "ketone": 4.0,  # -C(=O)-
    "aldehyde": 4.0,  # -CH=O
    "ether": 1.5,  # -O- (not carbonyl, not hydroxyl)
    "ring": 2.0,  # per ring closure
    "nitro": 6.0,  # -NO2
}

# BP estimate:  Tb_K = _TB_BASE + total_contrib * _TB_SCALE
_TB_BASE: float = 255.0
_TB_SCALE: float = 15.0

# VP-polarity scaling factors for the Antoine-like correlation.
# More polar compounds have a steeper logVP-vs-Tb slope.
_VP_FACTOR_NONPOLAR: float = 0.011
_VP_FACTOR_POLAR: float = 0.014
_VP_FACTOR_VERY_POLAR: float = 0.018

# Atom-type contribution values for logP (Wildman-Crippen style).
_LOGP_CONTRIB: dict[str, float] = {
    "aliphatic_c": 0.2,
    "aromatic_c": 0.1,
    "hydroxyl_o": -0.5,
    "ether_o": -0.3,
    "carbonyl_o": -0.1,
    "nitrogen": -0.5,
    "sulfur": -0.2,
    "fluorine": 0.1,
    "chlorine": 0.3,
    "bromine": 0.4,
    "iodine": 0.5,
}

# ---------------------------------------------------------------------------
# ODT class brackets  (air_ppb_low, air_ppb_high, eth_ppm_low, eth_ppm_high)
# ---------------------------------------------------------------------------
_ODT_BRACKETS: dict[str, tuple[float, float, float, float]] = {
    "esters": (0.001, 0.1, 0.001, 0.01),
    "macrocyclic_musks": (0.0001, 0.001, 0.0001, 0.001),
    "terpenes": (0.01, 1.0, 0.01, 0.5),
    "aldehydes": (0.0001, 0.01, 0.0001, 0.01),
    "alcohols": (0.001, 0.1, 0.001, 0.1),
    "ketones": (0.001, 0.1, 0.001, 0.1),
    "lactones": (0.001, 0.1, 0.001, 0.1),
    "phenolics": (0.01, 1.0, 0.01, 0.5),
}

# ---------------------------------------------------------------------------
# Activity coefficient lookup  (per AGENTS.md)
# ---------------------------------------------------------------------------
_ACTIVITY_COEF: dict[str, float] = {
    "non_polar_hydrocarbons": 3.0,
    "polar_esters": 1.75,
    "mid_polarity_sesquiterpenes_alcohols": 1.5,
    "h_bond_donors_acceptors": 0.6,
    "macrocyclic_musks": 0.5,
}

# ── Local DB path (for validation) ──
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_KB_PATH = _PROJECT_ROOT / "data" / "perfumery_kb.db"


# ===================================================================
# Internal helpers — SMILES parsing
# ===================================================================


def _count_group_features(smiles: str) -> dict[str, float]:
    """Return a dict ``{group_name: count}`` extracted from *smiles*.

    SMILES conventions used:

    - ``C`` / uppercase → aliphatic carbon
    - ``c`` / lowercase → aromatic carbon
    - ``=``  may be  C=O (carbonyl)  or  C=C (olefin)
    - Digits ``1``-``9``  mark ring-closure bonds (each appears twice
      per ring: one open, one close)
    """
    # Strip stereochemistry markers that don't affect functional-group counts.
    s = re.sub(r"[\\/@]", "", smiles)

    feats: dict[str, float] = {}

    # ── Aromatic carbons (lowercase c) ──
    feats["aromatic_c"] = float(s.count("c"))

    # ── Count =O groups (carbonyl oxygen) ──
    n_carbonyl = len(re.findall(r"=O", s))

    # ── Carboxyl / Ester classification ──
    # Forward ester:  R-C(=O)-O-R'  → SMILES substring ``C(=O)O`` + [Cc0-9]
    ester_forward = len(re.findall(r"C\(=O\)O[Cc0-9]", s))
    # Reverse ester:  R-O-C(=O)-R' → SMILES substring ``[Cc0-9]OC(=O)`` + [Cc0-9]
    #   (the O before C=O is the ether bridge — not the carbonyl oxygen)
    ester_reverse = len(re.findall(r"[Cc0-9]OC\(=O\)[Cc0-9]", s))

    feats["ester"] = float(ester_forward + ester_reverse)

    # Carboxyl: C(=O)O where the O is *not* bridged to a C
    #   (i.e. not followed by C, c, or digit, and not a reverse ester)
    feats["carboxyl"] = float(len(re.findall(r"C\(=O\)O(?:[^Cc0-9]|$)", s)))

    # ── Ketone: remaining =O that are not in carboxyl or ester ──
    feats["ketone"] = max(0.0, float(n_carbonyl) - feats["carboxyl"] - feats["ester"])

    # ── Aldehyde:  terminal ``=O`` (C=O at end of SMILES) ──
    # In canonical SMILES an aldehyde always writes the =O at the end.
    # We explicitly *exclude* ``C(=O)`` patterns (esters, ketones, acids).
    feats["aldehyde"] = 1.0 if re.search(r"(?<!C\()=O$", s) else 0.0
    # Adjust ketone — the aldehyde's =O was already counted in n_carbonyl
    # but not necessarily subtracted via the ester/carboxyl logic
    if feats["aldehyde"] and feats["ketone"] > 0:
        feats["ketone"] = max(0.0, feats["ketone"] - 1.0)

    # ── Olefin  C=C  (count = signs minus those in =O contexts) ──
    total_eq = s.count("=")
    eq_in_carbonyl = n_carbonyl  # every =O uses one =
    feats["olefin"] = float(max(0, total_eq - eq_in_carbonyl))

    # ── Hydroxyl O  —  O atoms not accounted for by carbonyl ──
    # Total O count minus O in =O, minus the bridging O in carboxyl/ester
    o_total = float(s.count("O"))
    o_accounted = float(n_carbonyl) + feats["carboxyl"] + feats["ester"]
    feats["hydroxyl"] = max(0.0, o_total - o_accounted)

    # ── Ether  (any O in C-O-C not already counted) ──
    # Very rough heuristic: if we have "extra" O beyond what we've matched,
    # those could be in ether linkages.
    o_still_unaccounted = o_total - o_accounted - feats["hydroxyl"]
    feats["ether"] = max(0.0, o_still_unaccounted)

    # ── Aliphatic C count (uppercase C) ──
    all_upper_c = float(len(re.findall(r"C", s)))  # noqa: N806
    # Carbons that are part of special functional groups
    c_special = feats["carboxyl"] + feats["ester"] + feats["ketone"] + feats["aldehyde"]
    feats["aliphatic_c"] = max(0.0, all_upper_c - c_special)

    # ── Ring closures  —  count digits, each ring uses 2 stops ──
    n_digits = len(re.findall(r"[1-9]", s))
    feats["ring"] = float(n_digits // 2)

    # ── Nitrogen ──
    feats["nitrogen"] = float(len(re.findall(r"[Nn]", s)))

    # ── Halogens ──
    feats["fluorine"] = float(len(re.findall(r"(?<!l)F(?!l)", s)))
    feats["chlorine"] = float(s.count("Cl"))
    feats["bromine"] = float(s.count("Br"))
    feats["iodine"] = float(s.count("I"))

    # ── Nitro  [N+](=O)[O-] ──
    feats["nitro"] = float(len(re.findall(r"\[N\+?\]\(=O\)\[O-\]", s)))

    # ── Sulfur ──
    feats["sulfur"] = float(len(re.findall(r"[Ss]", s)))

    return feats


def _has_polar_group(features: dict[str, float]) -> bool:
    """Return True if any polar functional group is present."""
    polar_keys = {"hydroxyl", "ester", "ketone", "aldehyde"}
    return any(features.get(k, 0) > 0 for k in polar_keys)


def _has_very_polar_group(features: dict[str, float]) -> bool:
    """Return True if a strongly polar group (carboxyl, nitro) is present."""
    return features.get("carboxyl", 0) > 0 or features.get("nitro", 0) > 0


def _vp_factor(features: dict[str, float]) -> float:
    """Return the VP log-slope factor based on polarity."""
    if _has_very_polar_group(features):
        return _VP_FACTOR_VERY_POLAR
    if _has_polar_group(features):
        return _VP_FACTOR_POLAR
    return _VP_FACTOR_NONPOLAR


# ===================================================================
# 1.  VP estimation  (Stein-Brown style)
# ===================================================================


def estimate_vp(smiles: str) -> float:
    """Estimate vapour pressure at 25 °C in Pa from a SMILES string.

    Uses a Stein-Brown-inspired group-contribution approach:

    1. Count functional groups via regex on the SMILES.
    2. Sum contributions → estimated boiling point (K).
    3. Convert BP to VP at 25 °C via a polarity-calibrated Antoine-like
       correlation.

    Parameters
    ----------
    smiles : str
        A valid SMILES string for a single molecule.

    Returns
    -------
    float
        Estimated vapour pressure in Pa.

    Raises
    ------
    ValueError
        If *smiles* is empty or obviously invalid.
    """
    _validate_smiles(smiles)

    features = _count_group_features(smiles)

    # ── Sum group contributions to boiling point ──
    contrib = 0.0
    contrib += features.get("aliphatic_c", 0) * _GROUP_BP_CONTRIB["aliphatic_c"]
    contrib += features.get("aromatic_c", 0) * _GROUP_BP_CONTRIB["aromatic_c"]
    contrib += features.get("olefin", 0) * _GROUP_BP_CONTRIB["olefin"]
    contrib += features.get("hydroxyl", 0) * _GROUP_BP_CONTRIB["hydroxyl"]
    contrib += features.get("carboxyl", 0) * _GROUP_BP_CONTRIB["carboxyl"]
    contrib += features.get("ester", 0) * _GROUP_BP_CONTRIB["ester"]
    contrib += features.get("amine", 0) * _GROUP_BP_CONTRIB["amine"]
    contrib += features.get("ketone", 0) * _GROUP_BP_CONTRIB["ketone"]
    contrib += features.get("aldehyde", 0) * _GROUP_BP_CONTRIB["aldehyde"]
    contrib += features.get("ether", 0) * _GROUP_BP_CONTRIB["ether"]
    contrib += features.get("ring", 0) * _GROUP_BP_CONTRIB["ring"]
    contrib += features.get("nitro", 0) * _GROUP_BP_CONTRIB["nitro"]

    # ── Convert contribution sum to boiling point (K) ──
    tb_k: float = _TB_BASE + contrib * _TB_SCALE

    # ── Clausius-Clapeyron-like to get VP at 298 K (25 °C) ──
    factor = _vp_factor(features)
    log10_vp = 4.5 - (tb_k - 273.0) * factor
    vp_pa = 10.0**log10_vp

    return vp_pa


# ===================================================================
# 2.  logP estimation  (Wildman-Crippen style)
# ===================================================================


def estimate_logp(smiles: str) -> float:
    """Estimate logP (octanol-water partition coefficient) from SMILES.

    Uses atom-type contribution counting with ring and proximity corrections.

    Parameters
    ----------
    smiles : str
        A valid SMILES string.

    Returns
    -------
    float
        Estimated logP.

    Raises
    ------
    ValueError
        If *smiles* is empty or obviously invalid.
    """
    _validate_smiles(smiles)

    features = _count_group_features(smiles)

    # ── Sum atom-type contributions ──
    logp_val = 0.0
    logp_val += features.get("aliphatic_c", 0) * _LOGP_CONTRIB["aliphatic_c"]
    logp_val += features.get("aromatic_c", 0) * _LOGP_CONTRIB["aromatic_c"]

    # Partition O contributions
    hydroxyl_o = features.get("hydroxyl", 0)
    ether_o = features.get("ether", 0)
    carbonyl_o = (
        features.get("ketone", 0)
        + features.get("aldehyde", 0)
        + features.get("carboxyl", 0)
        + features.get("ester", 0)
    )
    logp_val += hydroxyl_o * _LOGP_CONTRIB["hydroxyl_o"]
    logp_val += ether_o * _LOGP_CONTRIB["ether_o"]
    logp_val += carbonyl_o * _LOGP_CONTRIB["carbonyl_o"]

    logp_val += features.get("nitrogen", 0) * _LOGP_CONTRIB["nitrogen"]
    logp_val += features.get("sulfur", 0) * _LOGP_CONTRIB["sulfur"]
    logp_val += features.get("fluorine", 0) * _LOGP_CONTRIB["fluorine"]
    logp_val += features.get("chlorine", 0) * _LOGP_CONTRIB["chlorine"]
    logp_val += features.get("bromine", 0) * _LOGP_CONTRIB["bromine"]
    logp_val += features.get("iodine", 0) * _LOGP_CONTRIB["iodine"]

    # ── Proximity correction: two H-bond donors within 3 bonds → -0.3 ──
    # Approximate: if we have hydroxyl + carboxyl/amine, apply correction
    h_bond_donors = hydroxyl_o + features.get("carboxyl", 0) * 2 + features.get("amine", 0)
    if h_bond_donors >= 2:
        logp_val -= 0.3

    # ── Ring correction: -0.1 per ring ──
    logp_val -= features.get("ring", 0) * 0.1

    return logp_val


# ===================================================================
# 3.  ODT estimation  (class-bracketed)
# ===================================================================


def estimate_odt(
    chemical_class: str,
    mw: float,
    logp: float,
) -> tuple[float, float]:
    """Estimate odour detection threshold (ODT) from chemical class and MW.

    Parameters
    ----------
    chemical_class : str
        One of the recognised bracketed classes (e.g. ``"esters"``,
        ``"terpenes"``).  Falls back to ``"terpenes"`` if not found.
    mw : float
        Molecular weight in g/mol.  Used to scale the threshold within
        the bracket (higher MW → lower threshold → more potent).
    logp : float
        Octanol-water partition coefficient (secondary modifier; higher
        logP → slightly lower threshold).

    Returns
    -------
    tuple[float, float]
        ``(odt_air_ppb, odt_eth_ppm)`` — estimated thresholds in air (ppb)
        and ethanol solution (ppm).
    """
    # Look up bracket — fall back to terpenes if unknown
    bracket = _ODT_BRACKETS.get(chemical_class, _ODT_BRACKETS["terpenes"])

    air_low, air_high, eth_low, eth_high = bracket

    # MW scaling: MW=50 → scale≈0.9 (toward high end = less potent)
    #             MW=500 → scale≈0.1 (toward low end = more potent)
    mw_weight = max(0.0, min(1.0, 1.0 - (mw - 50.0) / 450.0))

    # logP modifier: higher logP → slightly lower threshold
    logp_mod = max(0.5, min(1.5, 1.0 - logp * 0.05))

    odt_air = air_low + (air_high - air_low) * mw_weight * logp_mod
    odt_eth = eth_low + (eth_high - eth_low) * mw_weight * logp_mod

    return (odt_air, odt_eth)


# ===================================================================
# 4.  Activity coefficient estimation
# ===================================================================


def estimate_activity_coef(chemical_class: str) -> float:
    """Return the estimated activity coefficient for a chemical class.

    Values from AGENTS.md (ethanol matrix, ~20 °C):

    ==========================================  =====
    Class                                        γ
    ==========================================  =====
    ``non_polar_hydrocarbons``                   3.0
    ``polar_esters``                             1.75
    ``mid_polarity_sesquiterpenes_alcohols``     1.5
    ``h_bond_donors_acceptors``                  0.6
    ``macrocyclic_musks``                        0.5
    ==========================================  =====

    Parameters
    ----------
    chemical_class : str
        One of the five class keys above.

    Returns
    -------
    float
        Estimated activity coefficient.

    Raises
    ------
    ValueError
        If *chemical_class* is not recognised.
    """
    gamma = _ACTIVITY_COEF.get(chemical_class)
    if gamma is None:
        msg = f"Unknown chemical class: {chemical_class!r}. Must be one of {set(_ACTIVITY_COEF)}"
        raise ValueError(msg)
    return gamma


# ===================================================================
# 5.  Note-tier estimation
# ===================================================================


def estimate_note_tier(vp_pa: float) -> str:
    """Classify a material's note tier from vapour pressure (Pa).

    Thresholds (from AGENTS.md):

        - ``"top"``   → VP > 2 Pa
        - ``"heart"`` → 0.1 Pa ≤ VP ≤ 2 Pa
        - ``"base"``  → VP < 0.1 Pa

    Parameters
    ----------
    vp_pa : float
        Vapour pressure at 25 °C in Pa.

    Returns
    -------
    str
        ``"top"``, ``"heart"``, or ``"base"``.
    """
    if vp_pa > 2.0:
        return "top"
    if vp_pa >= 0.1:
        return "heart"
    return "base"


# ===================================================================
# 6.  Combined estimator
# ===================================================================


def estimate_all(
    smiles: str,
    chemical_class: str | None = None,
    mw: float | None = None,
) -> dict[str, Any]:
    """Run all estimators and return a dict of results.

    Parameters
    ----------
    smiles : str
        SMILES string of the molecule.
    chemical_class : str or None
        Chemical class for ODT and activity coefficient lookups.
        If ``None``, the function tries to infer a reasonable default
        based on the functional groups present in the SMILES, falling
        back to ``"default"``.
    mw : float or None
        Molecular weight in g/mol.  If ``None``, a rough estimate is
        computed from the SMILES.

    Returns
    -------
    dict
        Keys: ``vp_pa``, ``logp``, ``odt_air_ppb``, ``odt_eth_ppm``,
        ``activity_coef``, ``note_tier``.
    """
    if mw is None:
        mw = _estimate_mw(smiles)

    vp_pa = estimate_vp(smiles)
    logp_val = estimate_logp(smiles)

    # Infer chemical class if not provided
    if chemical_class is None:
        chemical_class = _infer_chemical_class(smiles, vp_pa)

    odt_air, odt_eth = estimate_odt(chemical_class, mw, logp_val)

    try:
        activity_coef = estimate_activity_coef(chemical_class)
    except ValueError:
        activity_coef = 1.5  # mid-range default

    note_tier = estimate_note_tier(vp_pa)

    return {
        "vp_pa": vp_pa,
        "logp": logp_val,
        "odt_air_ppb": odt_air,
        "odt_eth_ppm": odt_eth,
        "activity_coef": activity_coef,
        "note_tier": note_tier,
    }


# ===================================================================
# Internal helpers
# ===================================================================


def _infer_chemical_class(smiles: str, vp_pa: float | None = None) -> str:
    """Guess a chemical class from SMILES for ODT bracketing."""
    features = _count_group_features(smiles)
    if features.get("carboxyl", 0) > 0:
        return "esters"  # closest available bracket for acids
    if features.get("ester", 0) > 0:
        return "esters"
    if features.get("aldehyde", 0) > 0:
        return "aldehydes"
    if features.get("ketone", 0) > 0:
        return "ketones"
    if features.get("hydroxyl", 0) > 0:
        return "alcohols"
    if features.get("aromatic_c", 0) > 0 and features.get("hydroxyl", 0) > 0:
        return "phenolics"
    if features.get("olefin", 0) > 0 or features.get("ring", 0) > 0:
        return "terpenes"
    return "terpenes"


def _validate_smiles(smiles: str) -> None:
    """Raise ``ValueError`` if *smiles* is empty or contains no atoms."""
    if not smiles or not isinstance(smiles, str):
        msg = f"SMILES must be a non-empty string, got {type(smiles).__name__}: {smiles!r}"
        raise ValueError(msg)
    # Check for a carbon atom — ``C`` (not part of ``Cl``) or aromatic ``c``.
    has_carbon = "c" in smiles or bool(re.search(r"(?:^|[^lL])C(?:[^lL]|$)", smiles))
    if not has_carbon:
        msg = f"SMILES must contain at least one carbon atom: {smiles!r}"
        raise ValueError(msg)


# Rough atomic masses for MW estimation.
_ATOMIC_MASSES: dict[str, float] = {
    "C": 12.011,
    "c": 12.011,
    "O": 15.999,
    "N": 14.007,
    "n": 14.007,
    "S": 32.06,
    "s": 32.06,
    "F": 18.998,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.90,
    "P": 30.974,
    "H": 1.008,
}


def _estimate_mw(smiles: str, add_implicit_h: bool = True) -> float:
    """Estimate molecular weight from a SMILES string.

    A rough estimate that counts explicit atoms and adds implicit hydrogens
    based on average valence.  Not accurate for charged species or
    coordination compounds.
    """
    s = re.sub(r"[\\/@\[\]{}()=#+\-]", "", smiles)
    # Remove digits
    s = re.sub(r"[0-9]", "", s)

    # Count multi-char symbols first
    multi_atoms = {"Cl": 0, "Br": 0}
    for sym in multi_atoms:
        multi_atoms[sym] = s.count(sym)
        s = s.replace(sym, "")

    # Count single-char atoms
    single_atom_counts: dict[str, int] = {}
    for ch in s:
        if ch.isalpha():
            single_atom_counts[ch] = single_atom_counts.get(ch, 0) + 1

    total = 0.0
    for sym, cnt in multi_atoms.items():
        total += _ATOMIC_MASSES.get(sym, 0.0) * cnt
    for sym, cnt in single_atom_counts.items():
        total += _ATOMIC_MASSES.get(sym, 0.0) * cnt

    # Add implicit hydrogens (rough: ~1.5 per carbon)
    if add_implicit_h:
        c_count = single_atom_counts.get("C", 0) + single_atom_counts.get("c", 0)
        total += c_count * 1.5 * 1.008

    return total


# ===================================================================
# Validation against the database
# ===================================================================


def _load_db_materials() -> list[dict[str, Any]]:
    """Load materials that have both SMILES and VP from the KB database."""
    import sqlite3

    if not _KB_PATH.exists():
        return []

    conn = sqlite3.connect(str(_KB_PATH))
    cursor = conn.execute(
        "SELECT canonical_name, vp_25c_pa, logp, smiles "
        "FROM materials "
        "WHERE vp_25c_pa > 0 AND logp IS NOT NULL AND smiles IS NOT NULL"
    )
    rows = cursor.fetchall()
    conn.close()

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name, vp, logp_val, smi in rows:
        if smi in seen:
            continue
        seen.add(smi)
        results.append({"name": name, "vp_pa": vp, "logp": logp_val, "smiles": smi})
    return results


def validate_vp_estimates() -> dict[str, Any]:
    """Run VP estimates against DB materials and return R² statistics.

    Returns
    -------
    dict
        Keys: ``r_squared`` (R² on log₁₀ scale), ``n`` (sample count),
        ``materials`` (list of per-material comparisons).
    """
    materials = _load_db_materials()
    if not materials:
        return {"r_squared": float("nan"), "n": 0, "materials": []}

    comparisons: list[dict[str, Any]] = []
    log_actual: list[float] = []
    log_predicted: list[float] = []

    for mat in materials:
        try:
            pred_vp = estimate_vp(mat["smiles"])
        except (ValueError, Exception):
            continue

        actual_vp = mat["vp_pa"]
        log_a = math.log10(max(actual_vp, 1e-12))
        log_p = math.log10(max(pred_vp, 1e-12))
        log_actual.append(log_a)
        log_predicted.append(log_p)

        comparisons.append(
            {
                "name": mat["name"],
                "actual_vp_pa": actual_vp,
                "predicted_vp_pa": pred_vp,
                "log10_actual": round(log_a, 4),
                "log10_predicted": round(log_p, 4),
                "ratio": round(pred_vp / max(actual_vp, 1e-12), 2),
            }
        )

    n = len(log_actual)
    if n < 3:
        return {"r_squared": float("nan"), "n": n, "materials": comparisons}

    mean_a = sum(log_actual) / n
    ss_res = sum((la - lp) ** 2 for la, lp in zip(log_actual, log_predicted))
    ss_tot = sum((la - mean_a) ** 2 for la in log_actual)

    r_squared = 1.0 - ss_res / max(ss_tot, 1e-12)

    return {
        "r_squared": round(r_squared, 4),
        "n": n,
        "materials": comparisons,
    }


def validate_logp_estimates() -> dict[str, Any]:
    """Run logP estimates against DB materials and return R² statistics.

    Returns
    -------
    dict
        Keys: ``r_squared``, ``n``, ``materials``.
    """
    materials = _load_db_materials()
    if not materials:
        return {"r_squared": float("nan"), "n": 0, "materials": []}

    comparisons: list[dict[str, Any]] = []
    actual_vals: list[float] = []
    predicted_vals: list[float] = []

    for mat in materials:
        try:
            pred_logp = estimate_logp(mat["smiles"])
        except (ValueError, Exception):
            continue

        actual_logp = mat["logp"]
        actual_vals.append(actual_logp)
        predicted_vals.append(pred_logp)

        comparisons.append(
            {
                "name": mat["name"],
                "actual_logp": actual_logp,
                "predicted_logp": pred_logp,
            }
        )

    n = len(actual_vals)
    if n < 3:
        return {"r_squared": float("nan"), "n": n, "materials": comparisons}

    mean_a = sum(actual_vals) / n
    ss_res = sum((a - p) ** 2 for a, p in zip(actual_vals, predicted_vals))
    ss_tot = sum((a - mean_a) ** 2 for a in actual_vals)

    r_squared = 1.0 - ss_res / max(ss_tot, 1e-12)

    return {
        "r_squared": round(r_squared, 4),
        "n": n,
        "materials": comparisons,
    }
