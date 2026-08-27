from pathlib import Path

import yaml

from engine.data_spine.loader import (
    clear_data_spine_cache,
    load_materials,
    load_registry,
    write_materials,
)
from engine.data_spine.material import Material


def test_loader_accepts_legacy_name_field(tmp_path: Path):
    payload = [
        {
            "name": "Legacy Material",
            "aliases": ["legacy material"],
            "odt_air_ppb": 1.0,
            "odt_eth_ppm": 0.1,
        },
        {
            "canonical_name": "Modern Material",
            "aliases": ["modern material"],
            "odt_air_ppb": 2.0,
            "odt_eth_ppm": 0.2,
        },
    ]
    (tmp_path / "L.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    materials = load_materials(tmp_path)

    names = {material.canonical_name for material in materials}
    assert names == {"Legacy Material", "Modern Material"}


def test_loader_reuses_yaml_parse_for_equivalent_directory_paths(tmp_path: Path, monkeypatch):
    payload = [{"canonical_name": "Cached Material", "odt_air_ppb": 1.0}]
    (tmp_path / "C.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    clear_data_spine_cache()
    safe_load_calls = 0
    real_load = yaml.load

    def counted_safe_load(stream, *, loader):
        nonlocal safe_load_calls
        safe_load_calls += 1
        return real_load(stream, Loader=loader)

    monkeypatch.setattr(yaml, "load", counted_safe_load)

    first = load_materials(tmp_path)
    second = load_materials(tmp_path / ".")
    registry = load_registry(tmp_path)

    assert [material.canonical_name for material in first] == ["Cached Material"]
    assert [material.canonical_name for material in second] == ["Cached Material"]
    assert registry.get("Cached Material") is first[0]
    assert safe_load_calls == 1


def test_write_materials_invalidates_cached_directory(tmp_path: Path):
    clear_data_spine_cache()
    write_materials([Material(canonical_name="Before")], tmp_path)
    assert [material.canonical_name for material in load_materials(tmp_path)] == ["Before"]

    write_materials([Material(canonical_name="Better")], tmp_path)

    assert [material.canonical_name for material in load_materials(tmp_path)] == ["Better"]
