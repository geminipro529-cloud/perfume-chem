"""Natural constituent profiles in the temporal screening simulator (model v6).

Before v6 a natural with a constituent profile left as one pseudo-component at
the rate its lightest rows set, and every step rebuilt its starting composition
from what was left. A labdanum resinoid with some pinene in its profile was gone
in two hours, and bergamot took its linalyl acetate and linalool with its
limonene. Each constituent row now leaves at its own rate, and the unresolved
remainder at the natural's own bulk vapour pressure. These tests pin that
bookkeeping, not any absolute evaporation claim.
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from engine.pipeline import simulator
from engine.pipeline.formula_state import build_formula_state, natural_composite_volatility
from engine.pipeline.natural_absolute_decomposition import (
    composite_headspace,
    composite_replacement_moles,
    get_constituents,
)

LABDANUM = "Labdanum Resinoid"
BERGAMOT = "Bergamot FCF Oil Sicilian"
LAVENDER = "Lavender EO (BONTAUX SAS)"
FORMULA = {LABDANUM: 150.0, BERGAMOT: 600.0, LAVENDER: 200.0, "Iso E Super": 1500.0}
DILUTIONS = {LABDANUM: 0.10, BERGAMOT: 1.0, LAVENDER: 1.0, "Iso E Super": 1.0}


def _row(frame, name):
    return next(m for m in frame.state.materials if m.name == name)


def _row_index(natural: str, constituent: str) -> int:
    names = [row[0] for row in get_constituents(natural)]
    return names.index(constituent)


@pytest.fixture(scope="module")
def frames():
    return simulator.simulate_formula(FORMULA, DILUTIONS)


def test_frames_carry_the_v6_model():
    assert simulator.TEMPORAL_MODEL == "dynamic_headspace_mass_balanced_loss_v6"


def test_labdanum_keeps_its_heavy_part_through_the_drydown(frames):
    opening, drydown = _row(frames[0], LABDANUM), _row(frames[-1], LABDANUM)
    volatility = natural_composite_volatility(drydown, frames[-1].state.temperature_K)
    assert volatility is not None
    left = drydown.natural_composite_remaining
    assert len(left) == len(volatility.fractions) + 1

    # The light rows (pinene, camphene) are gone; the resinous rows barely move.
    rates = [
        escaping / math.sqrt(mw)
        for escaping, mw in zip(volatility.escaping_tendency_pa, volatility.mw_g_mol)
    ]
    assert left[rates.index(max(rates))] < 0.01
    heavy = [i for i, escaping in enumerate(volatility.escaping_tendency_pa) if escaping < 0.1]
    assert heavy
    assert all(left[i] > 0.99 for i in heavy)
    # The unresolved remainder leaves at the resinoid's own bulk VP (about 3e-5 Pa).
    assert left[-1] > 0.99

    # Most of the resinoid is still there at 4 h (before v6: nothing was), but
    # its headspace no longer counts the pinene that has left.
    assert drydown.raw_ul > 0.5 * opening.raw_ul
    assert drydown.partial_pressure_pa < 0.01 * opening.partial_pressure_pa
    # The row's stock is exactly what its constituents and remainder add up to.
    assert drydown.raw_ul / opening.raw_ul == pytest.approx(volatility.mass_share(left), rel=1e-9)


def test_bergamot_keeps_its_linalyl_acetate_after_its_limonene_is_gone(frames):
    late_heart = next(frame for frame in frames if frame.label == "late_heart")
    start, row = _row(frames[0], BERGAMOT), _row(late_heart, BERGAMOT)
    left = row.natural_composite_remaining
    assert left[_row_index(BERGAMOT, "limonene")] < 0.01
    assert left[_row_index(BERGAMOT, "linalyl acetate")] > 0.5
    assert left[_row_index(BERGAMOT, "linalool")] > 0.4
    # Before v6 the whole oil was down to 0.2% of its stock at 2 h.
    assert row.raw_ul > 0.2 * start.raw_ul
    assert _row(frames[-1], BERGAMOT).raw_ul > 0.1 * start.raw_ul


def test_a_constituent_leaves_at_the_same_rate_whichever_natural_carries_it(frames):
    bergamot_rows = get_constituents(BERGAMOT)
    lavender_rows = get_constituents(LAVENDER)
    for constituent in ("linalyl acetate", "linalool"):
        b = _row_index(BERGAMOT, constituent)
        v = _row_index(LAVENDER, constituent)
        # Same MW, VP and gamma in both profiles, so the same loss law applies.
        assert bergamot_rows[b][2:] == lavender_rows[v][2:], constituent
        for frame in frames[1:]:
            in_bergamot = _row(frame, BERGAMOT).natural_composite_remaining[b]
            in_lavender = _row(frame, LAVENDER).natural_composite_remaining[v]
            assert in_bergamot == pytest.approx(in_lavender, rel=1e-12)
            assert in_bergamot < 1.0


def test_each_constituent_and_the_remainder_follow_the_loss_law():
    state = build_formula_state(FORMULA, DILUTIONS, temperature_K=305.0)
    start, _assumption = simulator._with_default_ethanol_fill(state)
    n0 = simulator._loss_scale_moles(start)
    ratio = n0 / simulator._pool_total_moles(start)
    dt = simulator.MAX_INTEGRATION_STEP_SECONDS
    after = simulator._advance_state(start, dt, initial_pool_moles=n0)

    checked = 0
    for before_row, after_row in zip(start.materials, after.materials, strict=True):
        volatility = natural_composite_volatility(before_row, start.temperature_K)
        if volatility is None:
            assert after_row.natural_composite_remaining == ()
            continue
        assert before_row.natural_composite_remaining == ()
        left = after_row.natural_composite_remaining
        for i, (escaping, mw) in enumerate(
            zip(volatility.escaping_tendency_pa, volatility.mw_g_mol, strict=True)
        ):
            expected_k = min(
                simulator.MAX_LOSS_RATE_PER_S,
                escaping / math.sqrt(mw) * simulator.LOSS_RATE_SCALE * ratio,
            )
            assert left[i] == pytest.approx(math.exp(-expected_k * dt), rel=1e-12)
        bulk = before_row.gamma * before_row.vp_pure_pa
        expected_rest = min(
            simulator.MAX_LOSS_RATE_PER_S,
            bulk / math.sqrt(before_row.mw_g_mol) * simulator.LOSS_RATE_SCALE * ratio,
        )
        assert left[-1] == pytest.approx(math.exp(-expected_rest * dt), rel=1e-12)
        assert after_row.active_ul / before_row.active_ul == pytest.approx(
            volatility.mass_share(left), rel=1e-12
        )
        checked += 1
    assert checked == 3


def test_a_natural_without_a_bulk_vp_keeps_its_unresolved_remainder():
    state = build_formula_state(FORMULA, DILUTIONS, temperature_K=305.0)
    row = next(m for m in state.materials if m.name == BERGAMOT)
    no_bulk_vp = dataclasses.replace(row, vp_pure_pa=None)
    kept, left = simulator._natural_composite_step(no_bulk_vp, 3600.0, 1.0, 305.0)
    assert left[-1] == 1.0
    assert left[_row_index(BERGAMOT, "limonene")] < 1.0
    assert 0.0 < kept < 1.0


def test_unevaporated_composition_gives_the_same_headspace_and_moles():
    rows = get_constituents(BERGAMOT)
    full = (1.0,) * (len(rows) + 1)
    plain = composite_headspace(BERGAMOT, 0.5, 10.0, parent_moles=0.003, temperature_K=305.0)
    explicit = composite_headspace(
        BERGAMOT, 0.5, 10.0, parent_moles=0.003, temperature_K=305.0, remaining=full
    )
    assert explicit == plain
    assert composite_replacement_moles(BERGAMOT, 0.5, 0.003, remaining=full) == (
        composite_replacement_moles(BERGAMOT, 0.5, 0.003)
    )


def test_an_evaporated_row_leaves_the_other_rows_masses_unchanged():
    rows = get_constituents(BERGAMOT)
    limonene = _row_index(BERGAMOT, "limonene")
    left = [1.0] * (len(rows) + 1)
    left[limonene] = 0.0
    start_g = 0.5
    # What is left of the oil once all of its limonene has gone.
    left_g = start_g * (1.0 - float(rows[limonene][1]))

    full = composite_headspace(BERGAMOT, start_g, 10.0, temperature_K=305.0)
    without = composite_headspace(
        BERGAMOT, left_g, 10.0, temperature_K=305.0, remaining=tuple(left)
    )
    limonene_only = composite_headspace(
        BERGAMOT,
        start_g,
        10.0,
        temperature_K=305.0,
        remaining=tuple(1.0 if i == limonene else 0.0 for i in range(len(rows) + 1)),
    )
    # The headspace mole pool is fixed here, so each row's partial pressure
    # depends on its own remaining mass only.
    limonene_alone = limonene_only.partial_pressure_pa * float(rows[limonene][1])
    assert without.partial_pressure_pa == pytest.approx(
        full.partial_pressure_pa - limonene_alone, rel=1e-9
    )
    assert composite_replacement_moles(BERGAMOT, left_g, 0.0, remaining=tuple(left)) == (
        pytest.approx(
            composite_replacement_moles(BERGAMOT, start_g, 0.0)
            - start_g * float(rows[limonene][1]) / float(rows[limonene][2]),
            rel=1e-12,
        )
    )


def test_remaining_must_name_every_row_and_the_remainder():
    rows = get_constituents(BERGAMOT)
    with pytest.raises(ValueError, match="remaining needs"):
        composite_headspace(BERGAMOT, 0.5, 10.0, remaining=(1.0,) * len(rows))
