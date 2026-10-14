"""Speed budget for the Edit a formula page: a 40-material formula stays quick to edit.

The plan's budget: the IFRA, allergen, cost and stock checks answer well under a
second. The server's check is timed here; the page's own work (redrawing the rows
with cost and stock, and an edit until the checks show) is timed in the browser
in test_formula_editor_browser.py.
"""

import time

from app.services.formula_checks import FormulaChecksRequest, _identity, compute_formula_checks

FORTY = [
    "Hedione", "Iso E Super", "Ambroxan", "Linalool", "Limonene", "Citronellol", "Geraniol", "Coumarin", "Vanillin",
    "Ethyl Vanillin", "Galaxolide", "Habanolide", "Ambrettolide", "Cashmeran", "Javanol", "Sandalore", "Ebanol",
    "Polysantol", "Vertofix", "Cedramber", "Bergamot Oil", "Lemon Oil", "Orange Oil", "Rose Oxide", "Phenylethyl Alcohol",
    "Benzyl Salicylate", "Hexyl Salicylate", "Helional", "Calone", "Dihydromyrcenol", "Aldehyde C-12 MNA", "Eugenol",
    "Isoeugenol", "Cinnamic Aldehyde", "Patchouli Oil", "Vetiver Oil", "Labdanum", "Benzoin", "Cis-3-Hexenol", "Damascone Beta",
]

# Seconds for one check once the material list is read (the app reads it at start).
CHECK_BUDGET_S = 0.25


def forty_rows():
    return [
        {"material": name, "amount_ul": str(40 + index * 7), "stock_fraction": "0.1" if index % 3 == 0 else "1",
         "fraction_basis": "w/w" if index % 3 == 0 else "neat"}
        for index, name in enumerate(FORTY)
    ]


def test_the_check_of_a_40_material_formula_answers_inside_its_budget():
    request = FormulaChecksRequest.model_validate({"rows": forty_rows(), "bottle_ml": "30"})
    compute_formula_checks(request)
    timings = []
    for _ in range(5):
        # Each name is looked up again, as for rows typed since the last check.
        _identity.cache_clear()
        start = time.perf_counter()
        answer = compute_formula_checks(request)
        timings.append(time.perf_counter() - start)

    assert len(answer["ifra"]["rows"]) == 40
    assert max(timings) < CHECK_BUDGET_S, [round(seconds, 3) for seconds in timings]
