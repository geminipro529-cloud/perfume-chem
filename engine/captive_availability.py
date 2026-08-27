"""
captive_availability.py — SUPPLY_CHAIN_PLAUSIBILITY category module.

Cross-references the perfumer's employer (Firmenich, Givaudan, IFF, Symrise, etc.)
with known captive molecules available only to that house. If a Givaudan captive is
hypothesized in a Firmenich formula, the score drops sharply. Also checks material
launch year vs fragrance year.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ── Captive material registry ──────────────────────────────────────────────────
CAPTIVE_MATERIALS: dict[str, dict] = {
    # material_name_lower → {house, launch_year, status, notes}
    # Firmenich captives
    "hedione":              {"house": "firmenich", "launch_year": 1966, "status": "licensed", "notes": "Now licensed broadly; still Firmenich origin"},
    "hedione hc":           {"house": "firmenich", "launch_year": 1990, "status": "captive", "notes": "High-cis variant, primarily Firmenich"},
    "habanolide":           {"house": "firmenich", "launch_year": 1965, "status": "captive", "notes": "Ethylene brassylate variant, Firmenich"},
    "norlimbanol":          {"house": "firmenich", "launch_year": 2009, "status": "captive", "notes": "Woody, firmenich only"},
    "karanal":              {"house": "firmenich", "launch_year": 2003, "status": "captive", "notes": "Sandalwood effect, Firmenich"},
    "koavone":              {"house": "firmenich", "launch_year": 1996, "status": "captive", "notes": "Woody cedarwood, Firmenich"},
    "clearwood":            {"house": "firmenich", "launch_year": 2013, "status": "captive", "notes": "Patchouli-wood, Firmenich"},
    "ambrox super":         {"house": "firmenich", "launch_year": 1980, "status": "licensed", "notes": "Ambroxide, Firmenich, widely used"},
    "ambrox":               {"house": "firmenich", "launch_year": 1980, "status": "licensed", "notes": "Ambroxide"},
    "polysantol":           {"house": "firmenich", "launch_year": 1975, "status": "captive", "notes": "Sandalwood, Firmenich, widely used now"},
    # Givaudan captives
    "javanol":              {"house": "givaudan", "launch_year": 2006, "status": "captive", "notes": "Premium sandalwood, Givaudan/Roche"},
    "timberol":             {"house": "givaudan", "launch_year": 2001, "status": "captive", "notes": "Dry cedar, Givaudan"},
    "ebanol":               {"house": "givaudan", "launch_year": 1999, "status": "captive", "notes": "Creamy sandalwood, Givaudan"},
    "akigalawood":          {"house": "givaudan", "launch_year": 2014, "status": "captive", "notes": "Patchouli facet, Givaudan"},
    "romandolide":          {"house": "givaudan", "launch_year": 2009, "status": "captive", "notes": "Macrocyclic musk, Givaudan"},
    "georgywood":           {"house": "givaudan", "launch_year": 2010, "status": "captive", "notes": "Woody amber, Givaudan"},
    "paradisone":           {"house": "givaudan", "launch_year": 1987, "status": "captive", "notes": "Fruity, Givaudan"},
    # IFF captives
    "sylvamber":            {"house": "iff", "launch_year": 2002, "status": "captive", "notes": "Amber musky, IFF"},
    "iso e super":          {"house": "iff", "launch_year": 1973, "status": "licensed", "notes": "IFF Fragrance patent expired, widely licensed"},
    "galaxolide":           {"house": "iff", "launch_year": 1965, "status": "licensed", "notes": "IFF origin, widely licensed"},
    "ambrocenide":          {"house": "iff", "launch_year": 2010, "status": "captive", "notes": "Ambergris effect, IFF captive"},
    "santaliff":            {"house": "iff", "launch_year": 2001, "status": "captive", "notes": "Sandalwood, IFF"},
    "florosa":              {"house": "iff", "launch_year": 2003, "status": "captive", "notes": "Rose-woody, IFF"},
    "damascenone":          {"house": "iff", "launch_year": 1970, "status": "licensed", "notes": "Rose, trace, widely used"},
    # Symrise captives
    "veramoss":             {"house": "symrise", "launch_year": 2003, "status": "captive", "notes": "Oakmoss replacement, Symrise"},
    "natrosol":             {"house": "symrise", "launch_year": 2008, "status": "captive", "notes": "Sandalwood, Symrise"},
    "muscone":              {"house": "symrise", "launch_year": 1906, "status": "licensed", "notes": "Natural musk, all houses"},
    # Pfizer / PFW
    "calone":               {"house": "pfizer/pfw", "launch_year": 1951, "status": "licensed", "notes": "Aquatic, widely licensed"},
}

# ── House employer registry ────────────────────────────────────────────────────
HOUSE_EMPLOYERS: dict[str, list[dict]] = {
    # perfumer_name_lower → list of {employer, from_year, to_year or None}
    "jacques cavallier-belletrud": [{"employer": "firmenich", "from_year": 1990, "to_year": None}],
    "alberto morillas":            [{"employer": "firmenich", "from_year": 1978, "to_year": None}],
    "jean-claude ellena":          [
        {"employer": "independent", "from_year": 1999, "to_year": 2012},
        {"employer": "hermes",      "from_year": 2004, "to_year": 2016},
    ],
    "dominique ropion":            [{"employer": "iff",         "from_year": 1989, "to_year": None}],
    "olivier polge":               [
        {"employer": "iff",    "from_year": 2000, "to_year": 2013},
        {"employer": "chanel", "from_year": 2013, "to_year": None},
    ],
    "francis kurkdjian":           [
        {"employer": "givaudan",   "from_year": 1995, "to_year": 2009},
        {"employer": "independent","from_year": 2009, "to_year": None},
    ],
    "harry fremont":               [{"employer": "firmenich", "from_year": 1985, "to_year": None}],
    "carlos benaim":               [{"employer": "iff",       "from_year": 1983, "to_year": None}],
    "anne flipo":                  [{"employer": "iff",       "from_year": 1990, "to_year": None}],
    "michel girard":               [{"employer": "iff",       "from_year": 1980, "to_year": None}],
    "geza schoen":                 [{"employer": "independent","from_year": 2000, "to_year": None}],
    "bertrand duchaufour":         [{"employer": "indoors",    "from_year": 2000, "to_year": None}],
    "pierre bourdon":              [{"employer": "givaudan",   "from_year": 1972, "to_year": 2010}],
    "frank voelkl":                [{"employer": "givaudan",   "from_year": 1999, "to_year": None}],
    "calice becker":               [{"employer": "givaudan",   "from_year": 1990, "to_year": None}],
    "yann vasnier":                [{"employer": "iff",        "from_year": 2000, "to_year": None}],
    "nathalie lorson":             [{"employer": "firmenich",  "from_year": 1995, "to_year": None}],
    "nicolas beaulieu":            [{"employer": "symrise",    "from_year": 2005, "to_year": None}],
    "olivier cresp":               [{"employer": "firmenich",  "from_year": 1993, "to_year": None}],
}

# Employers that are effectively "open" — independent perfumers or brand in-house
# can sometimes negotiate access but we treat them conservatively (no captive access).
_OPEN_EMPLOYERS = {"independent", "hermes", "chanel", "indoors"}


# ── Dataclasses ────────────────────────────────────────────────────────────────
@dataclass
class CaptiveConstraint:
    material: str
    captive_house: str       # which house owns it, or "commodity"
    perfumer_employer: str   # perfumer's employer at launch date
    launch_year: int         # when material was commercialized
    fragrance_year: int      # when fragrance was launched
    is_available: bool       # True if perfumer could have accessed it
    is_plausible: bool       # True if temporal AND supply chain works
    penalty: float           # 0.0 = no issue, 0.5 = unlikely, 1.0 = impossible
    note: str = ""


@dataclass
class CaptiveAnalysisResult:
    target_name: str
    perfumer: str
    employer_at_launch: str
    fragrance_year: int
    constraints: list[CaptiveConstraint] = field(default_factory=list)
    impossible_materials: list[str] = field(default_factory=list)   # captive from rival house
    anachronistic_materials: list[str] = field(default_factory=list)  # launched after fragrance
    plausible_materials: list[str] = field(default_factory=list)
    score: float = 0.0       # 0-100 SUPPLY_CHAIN_PLAUSIBILITY score


# ── Internal helpers ───────────────────────────────────────────────────────────

def _employer_at_year(perfumer_key: str, year: int) -> str:
    """Return the employer for a perfumer at a given year, or 'unknown'."""
    records = HOUSE_EMPLOYERS.get(perfumer_key, [])
    # Prefer the record whose range best covers the year; if multiple match, take
    # the most recent start date (most specific).
    candidates = [
        r for r in records
        if r["from_year"] <= year and (r["to_year"] is None or r["to_year"] >= year)
    ]
    if not candidates:
        return "unknown"
    # Pick candidate with highest from_year (most recent assignment)
    return max(candidates, key=lambda r: r["from_year"])["employer"]


def _normalize(name: str) -> str:
    return name.strip().lower()


def _confidence_multiplier(posterior: float, confirmed_materials: set[str], material_key: str) -> float:
    """
    Returns a weighting factor based on how certain we are about the material.
    confirmed: ×3, high posterior (>0.7): ×2, moderate (0.3-0.7): ×1
    """
    if material_key in confirmed_materials:
        return 3.0
    if posterior >= 0.7:
        return 2.0
    return 1.0


# ── Analysis function ──────────────────────────────────────────────────────────

def analyze_captive_availability(
    target_name: str,
    perfumer: str,
    year: int,
    material_posteriors: dict[str, float],
    confirmed_materials: Optional[list[str]] = None,
) -> CaptiveAnalysisResult:
    """
    Analyse supply-chain plausibility for a set of hypothesised materials.

    Parameters
    ----------
    target_name : str
        Name of the fragrance being reconstructed.
    perfumer : str
        Name of the perfumer (matched case-insensitively against HOUSE_EMPLOYERS).
    year : int
        Launch year of the fragrance.
    material_posteriors : dict[str, float]
        Mapping of material name → posterior probability (0–1).
    confirmed_materials : list[str], optional
        Materials whose presence has been independently confirmed (e.g., via GCMS).

    Returns
    -------
    CaptiveAnalysisResult
    """
    perfumer_key = _normalize(perfumer)
    employer = _employer_at_year(perfumer_key, year)
    confirmed_set: set[str] = {_normalize(m) for m in (confirmed_materials or [])}

    result = CaptiveAnalysisResult(
        target_name=target_name,
        perfumer=perfumer,
        employer_at_launch=employer,
        fragrance_year=year,
    )

    employer_known = perfumer_key in HOUSE_EMPLOYERS
    total_penalty = 0.0

    for raw_name, posterior in material_posteriors.items():
        if posterior < 0.3:
            continue

        mat_key = _normalize(raw_name)
        multiplier = _confidence_multiplier(posterior, confirmed_set, mat_key)

        if mat_key not in CAPTIVE_MATERIALS:
            # Commodity — no supply-chain constraint
            constraint = CaptiveConstraint(
                material=raw_name,
                captive_house="commodity",
                perfumer_employer=employer,
                launch_year=0,
                fragrance_year=year,
                is_available=True,
                is_plausible=True,
                penalty=0.0,
                note="Commodity material; no captive restriction.",
            )
            result.constraints.append(constraint)
            result.plausible_materials.append(raw_name)
            continue

        info = CAPTIVE_MATERIALS[mat_key]
        captive_house = info["house"]
        launch_year = info["launch_year"]
        status = info["status"]

        # ── Temporal check ────────────────────────────────────────────────────
        if launch_year > year:
            constraint = CaptiveConstraint(
                material=raw_name,
                captive_house=captive_house,
                perfumer_employer=employer,
                launch_year=launch_year,
                fragrance_year=year,
                is_available=False,
                is_plausible=False,
                penalty=1.0,
                note=(
                    f"Anachronistic: {raw_name} commercialised in {launch_year}, "
                    f"fragrance launched in {year}."
                ),
            )
            result.constraints.append(constraint)
            result.anachronistic_materials.append(raw_name)
            total_penalty += 1.0 * multiplier
            continue

        # ── Supply-chain check ────────────────────────────────────────────────
        if status == "licensed":
            # Licensed / patent-expired — any house may use it
            is_available = True
            penalty = 0.0
            note = "Licensed/patent-expired; available to all houses."
        elif employer in _OPEN_EMPLOYERS or employer == "unknown":
            # Independent / brand in-house perfumer — conservative: treat captive access
            # as unlikely but not impossible (penalty 0.5).
            if captive_house == employer:
                is_available = True
                penalty = 0.0
                note = f"Same house ({captive_house}); available."
            else:
                is_available = False
                penalty = 0.5
                note = (
                    f"{raw_name} is a {captive_house} captive; "
                    f"perfumer employer '{employer}' unlikely to have access."
                )
        elif captive_house == employer:
            is_available = True
            penalty = 0.0
            note = f"Perfumer at {employer}; {raw_name} is a house captive — available."
        else:
            # Rival-house captive — impossible
            is_available = False
            penalty = 1.0
            note = (
                f"{raw_name} is a {captive_house} captive; "
                f"perfumer employed at {employer} — rival-house material."
            )

        is_plausible = is_available and launch_year <= year

        constraint = CaptiveConstraint(
            material=raw_name,
            captive_house=captive_house,
            perfumer_employer=employer,
            launch_year=launch_year,
            fragrance_year=year,
            is_available=is_available,
            is_plausible=is_plausible,
            penalty=penalty,
            note=note,
        )
        result.constraints.append(constraint)

        if penalty == 1.0 and not is_available:
            result.impossible_materials.append(raw_name)
        elif is_plausible:
            result.plausible_materials.append(raw_name)

        total_penalty += penalty * multiplier

    # ── Score calculation ──────────────────────────────────────────────────────
    # Cap maximum deduction at 80 points so score never reaches absolute zero
    # from this module alone unless there are truly severe violations.
    deduction = min(total_penalty * 10.0, 80.0)
    base_score = 100.0 - deduction

    # Bonus for identified employer
    if employer_known:
        base_score = min(100.0, base_score + 10.0)

    result.score = max(20.0, base_score)
    return result


# ── Format function ────────────────────────────────────────────────────────────

def format_captive_result(result: CaptiveAnalysisResult) -> str:
    """Return a human-readable summary of the CaptiveAnalysisResult."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("SUPPLY CHAIN PLAUSIBILITY — Captive Availability Analysis")
    lines.append("=" * 60)
    lines.append(f"Fragrance  : {result.target_name}")
    lines.append(f"Perfumer   : {result.perfumer}")
    lines.append(f"Employer   : {result.employer_at_launch}")
    lines.append(f"Launch year: {result.fragrance_year}")
    lines.append(f"Score      : {result.score:.1f} / 100")
    lines.append("")

    if result.impossible_materials:
        lines.append("IMPOSSIBLE (rival-house captives):")
        for m in result.impossible_materials:
            lines.append(f"  ✗ {m}")
        lines.append("")

    if result.anachronistic_materials:
        lines.append("ANACHRONISTIC (not yet commercialised at launch):")
        for m in result.anachronistic_materials:
            lines.append(f"  ✗ {m}")
        lines.append("")

    if result.plausible_materials:
        lines.append("PLAUSIBLE materials:")
        for m in result.plausible_materials:
            lines.append(f"  ✓ {m}")
        lines.append("")

    lines.append("Constraint detail:")
    for c in result.constraints:
        flag = "OK " if c.is_plausible else "!  "
        lines.append(
            f"  [{flag}] {c.material:<28}  house={c.captive_house:<12}  "
            f"penalty={c.penalty:.1f}  | {c.note}"
        )

    lines.append("=" * 60)
    return "\n".join(lines)
