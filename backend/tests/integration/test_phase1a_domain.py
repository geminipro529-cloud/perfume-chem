"""Integration tests for Phase 1A domain foundation (materials, stocks, formulas)."""

import pytest
from httpx import AsyncClient

PREFIX = "/api/v1/lab"


class TestMaterialLifecycle:
    """Full material CRUD via API."""

    async def test_create_material(self, client: AsyncClient):
        resp = await client.post(f"{PREFIX}/materials", json={"canonical_name": "T1 Test Mat"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["canonical_name"] == "T1 Test Mat"
        assert "id" in data

    async def test_list_materials(self, client: AsyncClient):
        await client.post(f"{PREFIX}/materials", json={"canonical_name": "T2 Mat A"})
        resp = await client.get(f"{PREFIX}/materials")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_material_by_id(self, client: AsyncClient):
        create = await client.post(f"{PREFIX}/materials", json={"canonical_name": "T3 ByID"})
        mid = create.json()["id"]
        resp = await client.get(f"{PREFIX}/materials/{mid}")
        assert resp.status_code == 200
        assert resp.json()["canonical_name"] == "T3 ByID"

    async def test_resolve_material_by_name(self, client: AsyncClient):
        await client.post(f"{PREFIX}/materials", json={"canonical_name": "T4 Resolve"})
        resp = await client.get(f"{PREFIX}/materials/resolve/T4 Resolve")
        assert resp.status_code == 200
        assert resp.json()["canonical_name"] == "T4 Resolve"

    async def test_resolve_material_not_found(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/materials/resolve/Nonexistent999")
        assert resp.status_code == 404

    async def test_add_alias_and_resolve(self, client: AsyncClient):
        create = await client.post(f"{PREFIX}/materials", json={"canonical_name": "T5 Main"})
        mid = create.json()["id"]
        alias_resp = await client.post(
            f"{PREFIX}/materials/{mid}/aliases", json={"alias": "t5_alias"}
        )
        assert alias_resp.status_code == 201
        assert alias_resp.json()["alias"] == "t5_alias"
        resolve = await client.get(f"{PREFIX}/materials/resolve/t5_alias")
        assert resolve.status_code == 200
        assert resolve.json()["canonical_name"] == "T5 Main"


class TestStockLifecycle:
    """Full stock solution CRUD via API."""

    async def test_create_stock(self, client: AsyncClient):
        mat = await client.post(f"{PREFIX}/materials", json={"canonical_name": "T6 StockMat"})
        mid = mat.json()["id"]
        resp = await client.post(
            f"{PREFIX}/stocks",
            json={
                "material_id": mid,
                "active_fraction": 0.1,
                "fraction_basis": "mass_fraction",
                "initial_mass_g": 10.0,
                "density_g_ml": 1.0,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["initial_mass_g"] == 10.0

    async def test_get_stock_by_id(self, client: AsyncClient):
        mat = await client.post(f"{PREFIX}/materials", json={"canonical_name": "T6b StockMat"})
        mid = mat.json()["id"]
        create = await client.post(
            f"{PREFIX}/stocks",
            json={
                "material_id": mid,
                "active_fraction": 0.5,
                "fraction_basis": "mass_fraction",
                "initial_mass_g": 20.0,
            },
        )
        sid = create.json()["id"]
        resp = await client.get(f"{PREFIX}/stocks/{sid}")
        assert resp.status_code == 200
        assert resp.json()["active_fraction"] == 0.5

    async def test_update_stock_remaining(self, client: AsyncClient):
        mat = await client.post(f"{PREFIX}/materials", json={"canonical_name": "T6c StockMat"})
        mid = mat.json()["id"]
        create = await client.post(
            f"{PREFIX}/stocks",
            json={
                "material_id": mid,
                "active_fraction": 1.0,
                "fraction_basis": "mass_fraction",
                "initial_mass_g": 100.0,
            },
        )
        sid = create.json()["id"]
        resp = await client.patch(
            f"{PREFIX}/stocks/{sid}/remaining", json={"remaining_mass_g": 75.0}
        )
        assert resp.status_code == 200
        assert resp.json()["remaining_mass_g"] == 75.0

        bottle = await client.post(
            f"{PREFIX}/bottles", json={"label": "T6c Bottle", "initial_mass_g": 0.0}
        )
        addition = await client.post(
            f"{PREFIX}/bottles/{bottle.json()['id']}/additions",
            json={
                "stock_solution_id": sid,
                "mass_g": 80.0,
                "expected_sequence": 1,
                "command_id": "t6c-overdraw",
            },
        )
        assert addition.status_code == 409
        assert "only 75" in addition.json()["detail"]

    async def test_create_stock_unknown_material(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/stocks",
            json={
                "material_id": "bad-id-12345",
                "active_fraction": 1.0,
                "fraction_basis": "mass_fraction",
                "initial_mass_g": 10.0,
            },
        )
        assert resp.status_code == 404


class TestFormulaLifecycle:
    """Full formula and version CRUD via API."""

    async def test_create_formula(self, client: AsyncClient):
        resp = await client.post(f"{PREFIX}/formulas", json={"name": "T7 Test Formula"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "T7 Test Formula"

    async def test_get_formula_by_id(self, client: AsyncClient):
        create = await client.post(f"{PREFIX}/formulas", json={"name": "T8 Get Formula"})
        fid = create.json()["id"]
        resp = await client.get(f"{PREFIX}/formulas/{fid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "T8 Get Formula"

    async def test_create_formula_version(self, client: AsyncClient):
        create = await client.post(f"{PREFIX}/formulas", json={"name": "T9 Versioned"})
        fid = create.json()["id"]
        resp = await client.post(
            f"{PREFIX}/formulas/{fid}/versions",
            json={
                "brief": {"family": "floral"},
                "constraints": {"max": 20},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["version_number"] == 1

    async def test_version_auto_increment(self, client: AsyncClient):
        create = await client.post(f"{PREFIX}/formulas", json={"name": "T10 MultiVer"})
        fid = create.json()["id"]
        v1 = await client.post(
            f"{PREFIX}/formulas/{fid}/versions", json={"brief": {}, "constraints": {}}
        )
        v2 = await client.post(
            f"{PREFIX}/formulas/{fid}/versions", json={"brief": {}, "constraints": {}}
        )
        assert v1.json()["version_number"] == 1
        assert v2.json()["version_number"] == 2

    async def test_list_versions(self, client: AsyncClient):
        create = await client.post(f"{PREFIX}/formulas", json={"name": "T11 ListVers"})
        fid = create.json()["id"]
        await client.post(
            f"{PREFIX}/formulas/{fid}/versions", json={"brief": {}, "constraints": {}}
        )
        await client.post(
            f"{PREFIX}/formulas/{fid}/versions", json={"brief": {}, "constraints": {}}
        )
        resp = await client.get(f"{PREFIX}/formulas/{fid}/versions")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_get_specific_version(self, client: AsyncClient):
        create = await client.post(f"{PREFIX}/formulas", json={"name": "T12 SpecVer"})
        fid = create.json()["id"]
        await client.post(
            f"{PREFIX}/formulas/{fid}/versions",
            json={
                "brief": {"note": "v1"},
                "constraints": {},
            },
        )
        resp = await client.get(f"{PREFIX}/formulas/{fid}/versions/1")
        assert resp.status_code == 200
        assert resp.json()["version_number"] == 1


class TestLegacyAdapterRoundTrip:
    """Verify legacy adapter round-trip."""

    async def test_round_trip_preserves_percentages(self):
        from app.adapters.legacy_formula import LegacyFormulaAdapter

        ingredients = [
            {"name": "Hedione", "percentage": 60.0, "role": "heart"},
            {"name": "Iso E Super", "percentage": 40.0, "role": "base"},
        ]
        result = LegacyFormulaAdapter.round_trip(ingredients)
        assert len(result) == 2
        by_name = {r["name"]: r for r in result}
        assert by_name["Hedione"]["percentage"] == pytest.approx(60.0, abs=0.1)

    async def test_round_trip_with_grams(self):
        from app.adapters.legacy_formula import LegacyFormulaAdapter

        ingredients = [
            {"name": "Vanillin", "percentage": 10.0, "grams": 0.1, "role": "base"},
            {"name": "Ethanol", "percentage": 90.0, "grams": 0.9, "role": "solvent"},
        ]
        result = LegacyFormulaAdapter.round_trip(ingredients)
        by_name = {r["name"]: r for r in result}
        assert by_name["Vanillin"]["percentage"] == pytest.approx(10.0, abs=0.1)
