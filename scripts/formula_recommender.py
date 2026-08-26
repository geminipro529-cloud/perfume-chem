"""Formula Recommendations — material swap suggestions from diagnosis + OAV table.
Reads the pipeline output and suggests specific swaps."""
from __future__ import annotations

VP_SCALE = {
    "extreme": (100, 500),    # aldehydes, citrus EOs
    "high": (5, 100),         # linalool, DHM, monoterpenes
    "moderate": (0.5, 5),     # hedione, ISO E, ionones
    "low": (0.05, 0.5),       # ambrox, musks, base
    "very_low": (0.001, 0.05),# clearwood, norlimbanol
    "dormant": (0, 0.001),    # some macrolides, very heavy
}

SAME_FAMILY = {
    "musk": ["Romandolide", "Habanolide", "Ethylene Brassylate", "Exaltolide",
             "Ambrettolide", "Galaxolide", "Zenolide", "Macrolide", "Tonalide"],
    "amber": ["Ambrox Super", "Ambrofix", "Ambermax", "Amber Core", "Amberwood F",
              "Cedramber", "Azarbre"],
    "woody": ["Iso E Super", "Cedarwood EO", "Timberol", "Kephalis", "Vertofix",
              "Norlimbanol Dextro", "Clearwood"],
    "citrus": ["Bergamot FCF", "Grapefruit FCF", "Lemon FCF", "Lime Distilled EO",
               "Blood Orange", "Red Mandarin", "Cedrat FCF", "D-Limonene"],
    "floral": ["Hedione HC", "Jasmine FO", "Rose Oxide", "Geraniol", "Citronellol",
               "Phenethyl Alcohol", "Linalool"],
}


def _get_family(material: str) -> str | None:
    ml = material.lower()
    for fam, mats in SAME_FAMILY.items():
        for m in mats:
            if m.lower() in ml or ml in m.lower():
                return fam
    return None


def suggest_swap(oav_table: list[dict], material_name: str) -> dict | None:
    """Suggest a replacement for a dormant material."""
    for m in oav_table:
        if m.get("name") == material_name:
            oav = m.get("oav", 0) or 0
            vp = m.get("vp_pa", 0) or 0
            m.get("note", "")
            if oav >= 1.0:
                return None  # already perceptible

            fam = _get_family(material_name)
            if not fam:
                return None

            # Find higher-VP alternative in same family
            candidates = []
            for alt in SAME_FAMILY[fam]:
                alt_l = alt.lower()
                if alt_l == material_name.lower():
                    continue
                for row in oav_table:
                    if alt_l in row.get("name", "").lower():
                        alt_oav = row.get("oav", 0) or 0
                        if alt_oav >= 1.0:
                            candidates.append((alt_oav, alt, row.get("active_ul", 0)))
                        break

            if candidates:
                candidates.sort(key=lambda x: -x[0])
                return {
                    "swap_from": material_name,
                    "swap_to": candidates[0][1],
                    "reason": f"{material_name} is dormant (OAV={oav:.2f}, VP={vp:.3f} Pa)",
                    "expected_gain": f"Alt OAV={candidates[0][0]:.1f} vs current {oav:.2f}",
                    "current_uL": m.get("active_ul", 0),
                }
    return None


def generate_recommendations(report: dict) -> list[dict]:
    """Generate prioritized material swap recommendations."""
    oav_table = report.get("oav_table", [])
    report.get("diagnosis", [])
    suggestions = []

    # Find dormant character materials
    for m in oav_table:
        oav = m.get("oav", 0) or 0
        role = m.get("role", "")
        if oav < 1.0 and role in ("character", "radiance", "volume", "fixative"):
            swap = suggest_swap(oav_table, m.get("name", ""))
            if swap:
                suggestions.append(swap)

    return suggestions
