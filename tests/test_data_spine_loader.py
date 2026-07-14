from pathlib import Path

import yaml

from engine.data_spine.loader import load_materials


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
