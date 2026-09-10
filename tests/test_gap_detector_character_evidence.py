"""Gap filler suggestions must treat unavailable character evidence as unknown."""

from __future__ import annotations

from engine import gap_detector
from engine.ingredient_intelligence import MaterialProfile


def _profiles() -> dict[str, MaterialProfile]:
    return {
        # Existing formula material; only used as a synergy partner.
        "Hedione": MaterialProfile(name="Hedione", character={"floral": 7.0}, note="heart"),
        # PROSE_ONLY character evidence, no dimension/note match for "floral".
        "Prose Candidate": MaterialProfile(
            name="Prose Candidate",
            character="soft floral prose",
            note="heart",
            synergies=["Hedione"],
        ),
        # AVAILABLE character evidence that genuinely lacks the family.
        "Numeric Candidate": MaterialProfile(
            name="Numeric Candidate",
            character={"freshness": 6.0},
            note="heart",
            synergies=["Hedione"],
        ),
        # AVAILABLE character evidence that matches the family.
        "Floral Candidate": MaterialProfile(
            name="Floral Candidate",
            character={"floral": 5.0},
            note="heart",
            synergies=["Hedione"],
        ),
        # PROSE_ONLY character evidence with an independent note match.
        "Note Candidate": MaterialProfile(
            name="Note Candidate",
            character="ambery prose",
            note="base",
            synergies=["Hedione"],
        ),
    }


def _suggest(monkeypatch, gap_families: list[str]) -> dict[str, dict]:
    monkeypatch.setattr(gap_detector, "get_all_profiles", _profiles)
    rows = gap_detector.GapDetector().suggest_synergistic_fillers(
        ["Hedione"], gap_families=gap_families
    )
    return {row["material"]: row for row in rows}


def test_unavailable_character_is_reported_unknown_not_dropped(monkeypatch):
    by_name = _suggest(monkeypatch, ["floral"])
    assert "Prose Candidate" in by_name
    assert by_name["Prose Candidate"]["gap_family_basis"] == "character_evidence_unavailable"
    assert by_name["Prose Candidate"]["character_evidence_status"] == "PROSE_ONLY"


def test_available_character_without_family_match_stays_negative(monkeypatch):
    by_name = _suggest(monkeypatch, ["floral"])
    assert "Numeric Candidate" not in by_name
    assert "Floral Candidate" in by_name
    assert by_name["Floral Candidate"]["gap_family_basis"] == "character"


def test_independent_note_evidence_reports_note_basis(monkeypatch):
    by_name = _suggest(monkeypatch, ["base"])
    assert by_name["Note Candidate"]["gap_family_basis"] == "note"
