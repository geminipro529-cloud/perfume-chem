"""The composer's default material ceiling is 60 (Kenny's choice, 2026-10-09 08:01 UTC).

It is a ceiling, not a target: the composer stops when its notes, accords and
layers are placed. Smaller ceilings stay available in the Lab form and the API.
"""

from pathlib import Path

from app.schemas.lab_lifecycle import FormulaDesignChatCreate
from app.services.engine_job_registry import FormulaDesignPayloadV2

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"


def test_fast_sketch_request_defaults_to_sixty_materials() -> None:
    assert FormulaDesignChatCreate(message="a dry lavender amber").max_materials == 60


def test_deep_compose_payload_defaults_to_sixty_materials() -> None:
    assert FormulaDesignPayloadV2(message="a dry lavender amber").max_materials == 60


def test_lab_form_preselects_sixty_and_keeps_smaller_ceilings() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert '<option value="60" selected>' in html
    assert '<option value="15">' in html
    assert '<option value="15" selected>' not in html
    lab_js = (STATIC / "lab.js").read_text(encoding="utf-8")
    assert '$(\'[name="max_materials"]\', form).value = "60";' in lab_js
    assert "Number(data.max_materials || 60)" in lab_js
