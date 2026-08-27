from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.api.v1.endpoints.solforge_workbench import get_solforge_workbench_service
from app.main import app
from app.schemas.solforge_workbench import (
    AUTHORITY_FLAGS_FALSE,
    SolForgeWorkbenchDesignResponseV1,
    SolForgeWorkbenchStatusV1,
)
from app.services.solforge_workbench import WorkbenchFailure


def _request() -> dict:
    case = {
        "schema_version": "solforge_case_v1",
        "inventory_path": "D:/inventory.xlsx",
        "inventory_sha256": "a" * 64,
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    hypotheses = {
        "schema_version": "sol_hypothesis_set_v1",
        "case_sha256": "b" * 64,
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    return {
        "schema_version": "solforge_workbench_design_request_v1",
        "case": case,
        "hypotheses": hypotheses,
    }


def _status() -> SolForgeWorkbenchStatusV1:
    return SolForgeWorkbenchStatusV1(
        schema_version="solforge_workbench_status_v1",
        ready=True,
        blockers=(),
        completed_run_count=0,
        artifact_bytes=0,
        max_runs=50,
        max_artifact_bytes=104_857_600,
        max_concurrent_runs=1,
        artifact_download_available=False,
        authority_flags=dict(AUTHORITY_FLAGS_FALSE),
    )


def _response() -> SolForgeWorkbenchDesignResponseV1:
    return SolForgeWorkbenchDesignResponseV1(
        schema_version="solforge_workbench_design_response_v1",
        run_id="sf-" + "1" * 32,
        stage="DECIDED",
        history=("INTAKE", "DECIDED"),
        decision="NO_CHANGE",
        blockers=(),
        evidence_limitations=("No nonredundant delta was justified.",),
        next_action="Retain the current target architecture.",
        registry_sha256="c" * 64,
        admitted_module_ids=("architectural-delta-engine",),
        compiled_experiment_sha256="d" * 64,
        selected_hypothesis_id=None,
        delta_kind=None,
        arms=(),
        inventory_statuses=(),
        manifest_sha256="e" * 64,
        records=(),
        artifact_download_available=False,
        authority_flags=dict(AUTHORITY_FLAGS_FALSE),
    )


class _FakeService:
    def __init__(self, *, failure: WorkbenchFailure | None = None) -> None:
        self.failure = failure
        self.requests = []

    async def status(self):
        if self.failure is not None:
            raise self.failure
        return _status()

    async def run_design(self, request):
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        return _response()


@pytest.mark.asyncio
async def test_status_returns_configuration_only(client: AsyncClient) -> None:
    fake = _FakeService()
    app.dependency_overrides[get_solforge_workbench_service] = lambda: fake

    response = await client.get("/api/v1/solforge/workbench/status")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["artifact_download_available"] is False
    assert not any(response.json()["authority_flags"].values())


@pytest.mark.asyncio
async def test_design_returns_verified_service_result(client: AsyncClient) -> None:
    fake = _FakeService()
    app.dependency_overrides[get_solforge_workbench_service] = lambda: fake

    response = await client.post(
        "/api/v1/solforge/workbench/design", json=_request()
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "NO_CHANGE"
    assert response.json()["artifact_download_available"] is False
    assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_design_rejects_non_json(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/solforge/workbench/design",
        content=b"not json",
        headers={"content-type": "text/plain"},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "JSON_REQUIRED"


@pytest.mark.asyncio
async def test_design_rejects_malformed_json(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/solforge/workbench/design",
        content=b"{bad",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MALFORMED_JSON"


@pytest.mark.asyncio
async def test_design_rejects_oversized_body(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/solforge/workbench/design",
        content=b"x" * 524_289,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "REQUEST_TOO_LARGE"


@pytest.mark.asyncio
async def test_design_rejects_invalid_closed_packet(client: AsyncClient) -> None:
    payload = _request()
    payload["case"]["authority_flags"]["sensory"] = True

    response = await client.post(
        "/api/v1/solforge/workbench/design", json=payload
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PACKET_INVALID"


@pytest.mark.asyncio
async def test_service_failure_code_and_status_are_preserved(client: AsyncClient) -> None:
    fake = _FakeService(
        failure=WorkbenchFailure(
            "INVENTORY_BINDING_MISMATCH", 409, "inventory hash changed"
        )
    )
    app.dependency_overrides[get_solforge_workbench_service] = lambda: fake

    response = await client.post(
        "/api/v1/solforge/workbench/design", json=_request()
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "INVENTORY_BINDING_MISMATCH",
        "message": "inventory hash changed",
    }
