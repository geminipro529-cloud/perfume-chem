"""Lemon and bergamot notes are judged through one cited marker (fault hunt, 6 Nov 2026, fix 4).

The citrus named note held in 3 of 34 test formulas (citrus-cologne failed
the duel benchmark on it): lemon and bergamot oils had no marker.  Lemon is
judged by citral (Chida et al. 2006), bergamot by linalyl acetate (Sawamura
et al. 2006).  Vetiver, pink pepper, lavender and orange stay held.
"""

from __future__ import annotations

import pytest

from engine.formulation_intelligence import note_markers as nm
from engine.formulation_intelligence import yardstick as ys
from engine.pipeline.natural_absolute_decomposition import get_constituents


class _Natural:
    def __init__(self, name: str, profile_key: str, vapour: dict[str, float]) -> None:
        self.name = name
        self.screening_oav = 1e6
        self.odt_air_ppm = None
        self.missing_fields: tuple = ()
        self.has_constituent_resolved_oav = True
        self.natural_composite_metadata = {"profile_key": profile_key, "characterized_fraction": 0.84}
        self.constituent_vapor_ppm = tuple(vapour.items())


def test_the_lemon_profile_carries_its_citral() -> None:
    rows = {row[0]: row[1] for row in get_constituents("Lemon FCF Oil Sicilian")}
    assert rows["citral"] == pytest.approx(0.025)


@pytest.mark.parametrize(
    ("name", "key", "marker", "threshold_ppb"),
    [
        ("Lemon FCF Oil Sicilian", "lemon fcf oil sicilian", "citral", 4.337),
        ("Bergamot FCF Oil Sicilian", "citrus bergamia calabrian type iso 3520 midpoint profile",
         "linalyl acetate", 2.7),
    ],
)
def test_a_citrus_oil_is_judged_by_its_marker(name: str, key: str, marker: str, threshold_ppb: float) -> None:
    at = _Natural(name, key, {"limonene": 50.0, marker: threshold_ppb / 1000.0})
    (reading,) = nm.marker_readings(at)
    assert reading["constituent"] == marker and reading["air_odt_ppb"] == threshold_ppb
    assert nm.detects(at)
    assert ys._note_status([at], {at.name}, ["lemon", "bergamot"]) == "detectable"
    # Under its threshold the note still holds: the remainder may carry it.
    under = _Natural(name, key, {"limonene": 50.0, marker: threshold_ppb / 2000.0})
    assert not nm.detects(under)
    assert ys._note_status([under], {under.name}, ["lemon", "bergamot"]) == "unknown_physics"
