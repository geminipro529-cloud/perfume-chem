"""Fast unit tests for the benchmark's pure logic (no composing)."""
from types import SimpleNamespace

from tests.benchmarks.test_brief_benchmark import _compare, _ifra_status, _note_eval


def _m(name, oav, odt=1.0, missing=()):
    return SimpleNamespace(name=name, screening_oav=oav, odt_air_ppm=odt, missing_fields=tuple(missing))


def _status(mats, subs=("rose",)):
    return _note_eval(mats, {m.name for m in mats}, list(subs))["status"]


def test_note_absent():
    assert _status([_m("Lilial", 5.0)]) == "absent"


def test_note_unknown_physics():
    assert _status([_m("Rose Oxide", None), _m("Rose Ketone", 3.0, odt=None)]) == "unknown_physics"
    assert _status([_m("Rose Oxide", 3.0, missing=("odt_air_ppm",))]) == "unknown_physics"


def test_note_detectable_and_below():
    assert _status([_m("Rose Oxide", 2.0), _m("Rose Ketone", 0.1)]) == "detectable"
    assert _status([_m("Rose Oxide", 0.5)]) == "below_threshold"


def test_note_share_reported():
    ev = _note_eval([_m("Rose Oxide", 3.0), _m("Lilial", 1.0)], {"Rose Oxide", "Lilial"}, ["rose"])
    assert ev["share"] == 0.75


def _chk(status):
    return {"check": "ifra", "status": status}


def test_ifra_status():
    assert _ifra_status([_chk("PASS"), _chk("FAIL")]) == "FAIL"
    assert _ifra_status([_chk("PASS"), _chk("WARN")]) == "WARN"
    assert _ifra_status([_chk("PASS")]) == "PASS"
    missing = _ifra_status([{"check": "other", "status": "PASS"}])
    assert missing == "MISSING" and missing not in ("PASS", "WARN")
    assert _ifra_status([]) == "MISSING"


def _rep(status="detectable", ifra=True):
    return {"material_count": 10, "ifra_pass": ifra, "ifra_status": "PASS" if ifra else "FAIL",
            "named_notes": [{"name": "rose", "window": "heart", "status": status, "share": 0.1}]}


def test_compare_unchanged_and_regressions():
    base = {"b": _rep()}
    assert _compare(base, {"b": _rep()}) == []
    probs = _compare(base, {"b": _rep(status="absent")})
    assert len(probs) == 1 and "b" in probs[0] and "rose" in probs[0] and "absent" in probs[0]
    assert any("ifra_pass" in p for p in _compare(base, {"b": _rep(ifra=False)}))
    assert _compare({"b": _rep("below_threshold")}, {"b": _rep("absent")}) == []
