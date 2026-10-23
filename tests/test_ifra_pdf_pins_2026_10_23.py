"""Pins IFRA table values re-read from the standard PDFs on 2026-10-23.

IFRA_STD_036.pdf prints five CAS numbers for farnesol; IFRA_STD_089.pdf prints
"Category 4 0.0015 % (5-MOP)", a bergapten limit in the finished product.
"""

from engine.ifra_standards import load_ifra_table, load_undisclosed_bases


def test_farnesol_standard_lists_every_cas_on_its_pdf():
    table = load_ifra_table()
    assert table.standards["IFRA_STD_036"].cas == (
        "4602-84-0", "106-28-5", "3790-71-4", "16106-95-9", "3879-60-5",
    )


def test_furocoumarin_standard_category_4_is_the_5mop_limit():
    std = load_ifra_table().standards["IFRA_STD_089"]
    assert std.cat4_limit_pct == 0.0015
    assert std.cat4_quote == "Category 4 0.0015 % (5-MOP)"


def test_furocoumarin_limit_is_not_applied_to_an_fcf_oils_own_dose():
    table = load_ifra_table()
    fcf = table.lookup("Bergamot FCF Oil Sicilian")
    assert fcf is not None
    assert fcf.status == "specification"
    assert fcf.cat4_limit_pct is None


def test_owned_suffixed_names_resolve():
    table = load_ifra_table()
    expected = {
        "Turkish Storax Liquidambar orientalis resin ethanol tincture "
        "(20% starting resin charge w/w)": "Turkish Storax Tincture",
        "Vietnamese Benzoin Styrax tonkinensis resin ethanol tincture "
        "(40% starting resin charge w/w)": "Vietnamese Benzoin Tincture",
        "Kenyan Myrrh resin ethanol tincture (20% starting resin charge w/w)":
            "Kenyan Myrrh Ethanol Tincture",
        "Oman Frankincense resin ethanol tincture (33% starting resin charge w/w)":
            "Oman Frankincense Ethanol Tincture",
        "Caraway Seed Oil (10% w/w in DPG)": "Caraway Seed EO",
        "Nerolin Bromelia (10% in DPG)": "Nerolin Bromelia",
        "p-Cresyl Methyl Ether (PCME) (10%)": "p-Cresyl Methyl Ether",
        "Champignol (10% in DPG)": "Champignol",
    }
    for stock, name in expected.items():
        hit = table.lookup(stock)
        assert hit is not None and hit.name == name, stock


def test_new_undisclosed_bases_are_flagged():
    names = {b.name for b in load_undisclosed_bases()}
    assert {"Cassis Base 345B", "Sandalwood Base X3", "Tuberlia Base"} <= names
