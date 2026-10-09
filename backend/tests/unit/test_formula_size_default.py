"""The composer's default material ceiling is 15 (Kenny's choice, 2026-10-09).

A larger formula stays available as an explicit choice in the Lab form and the API.
"""

from pathlib import Path

from app.schemas.lab_lifecycle import FormulaDesignChatCreate
from app.services.engine_job_registry import FormulaDesignPayloadV2

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"


def test_fast_sketch_request_defaults_to_fifteen_materials() -> None:
    assert FormulaDesignChatCreate(message="a dry lavender amber").max_materials == 15


def test_deep_compose_payload_defaults_to_fifteen_materials() -> None:
    assert FormulaDesignPayloadV2(message="a dry lavender amber").max_materials == 15


def test_lab_form_preselects_fifteen_and_keeps_larger_ceilings() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert '<option value="15" selected>' in html
    assert '<option value="30">' in html
    assert '<option value="30" selected>' not in html
    lab_js = (STATIC / "lab.js").read_text(encoding="utf-8")
    assert '$(\'[name="max_materials"]\', form).value = "15";' in lab_js
    assert "Number(data.max_materials || 15)" in lab_js
