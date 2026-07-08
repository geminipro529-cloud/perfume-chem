"""Golden-set verification harness.

Each entry is a known input → expected qualitative output. Used to detect
regressions when any layer is touched.

Run:
    python -m verification_runs.run_golden
"""
from __future__ import annotations

GOLDEN_CASES = [
    {
        "name": "water_vp_25c",
        "module": "engine.thermo.antoine",
        "fn": "vp_pa",
        "kwargs": {"T_K": 298.15, "A": 8.07131, "B": 1730.63, "C": 233.426},
        "expect_range": (3000.0, 3300.0),
    },
    {
        "name": "limonene_in_ethanol_gamma",
        "module": "engine.thermo.activity",
        "fn": "gamma",
        "args": ["Limonene"],
        "kwargs": {
            "composition": {"Ethanol": 0.95, "Limonene": 0.05},
            "T_K": 298.15,
            "hsp_table": {"Ethanol": (15.8, 8.8, 19.4), "Limonene": (16.5, 1.1, 4.2)},
        },
        "expect_range": (3.0, 8.0),
    },
    {
        "name": "potts_guy_ethanol",
        "module": "engine.skin_compartments",
        "fn": "kp_cm_per_h",
        "args": [-0.31, 46.07],
        "expect_range": (1e-4, 5e-3),
    },
]
