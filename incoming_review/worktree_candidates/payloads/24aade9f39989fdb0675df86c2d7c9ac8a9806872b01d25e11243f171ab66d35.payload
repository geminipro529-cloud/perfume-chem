from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

import pytest
import yaml

import app.core.security as security_module
from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_round_trip_returns_typed_values():
    password_hash = get_password_hash("correct horse battery staple")

    assert isinstance(password_hash, str)
    assert verify_password("correct horse battery staple", password_hash) is True
    assert verify_password("wrong password", password_hash) is False


def test_long_passwords_are_not_silently_truncated_to_bcrypt_limit():
    password = "x" * 80 + "-correct"
    colliding_prefix = "x" * 80 + "-wrong"
    password_hash = get_password_hash(password)

    assert password_hash.startswith("$bcrypt-sha256$")
    assert verify_password(password, password_hash) is True
    assert verify_password(colliding_prefix, password_hash) is False


def test_existing_legacy_bcrypt_hash_remains_verifiable():
    legacy_hash = "$2b$04$ar/EPsJaJo8.8UUGuNiA.eU3Lx3s.VvpSChwRBsxtled50NMWc5Oy"

    assert verify_password("legacy-password", legacy_hash) is True
    assert verify_password("wrong-password", legacy_hash) is False


def test_access_token_round_trip_returns_claim_mapping(monkeypatch):
    monkeypatch.setattr(
        security_module.settings,
        "SECRET_KEY",
        "test-only-secret-key-with-at-least-32-bytes",
    )
    token = create_access_token(
        {"sub": "researcher@example.com"},
        expires_delta=timedelta(minutes=5),
    )
    payload = decode_access_token(token)

    assert isinstance(token, str)
    assert payload is not None
    assert payload["sub"] == "researcher@example.com"


def test_invalid_access_token_returns_none():
    assert decode_access_token("not-a-jwt") is None


def test_security_module_uses_pyjwt_without_python_jose():
    repo_root = Path(__file__).resolve().parents[3]
    source = (repo_root / "backend" / "app" / "core" / "security.py").read_text(
        encoding="utf-8"
    )

    assert "import jwt" in source
    assert "from jose" not in source


def test_settings_accept_the_canonical_external_v5_inventory_variable(monkeypatch):
    inventory_path = r"C:\external\Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx"
    monkeypatch.setenv("PERFUME_CHEM_V5_INVENTORY", inventory_path)
    monkeypatch.delenv("SOLFORGE_INVENTORY_PATH", raising=False)

    configured = Settings(_env_file=None)

    assert configured.SOLFORGE_INVENTORY_PATH == inventory_path


def test_root_launcher_is_loopback_only_without_reload(monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    launcher_path = repo_root / "run_api_server.py"
    spec = importlib.util.spec_from_file_location("perfume_chem_root_launcher", launcher_path)
    assert spec is not None and spec.loader is not None
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)

    captured: dict[str, object] = {}

    def fake_run(app: str, **kwargs: object) -> None:
        captured["app"] = app
        captured.update(kwargs)

    inventory_path = str(repo_root / "external-v5.xlsx")
    monkeypatch.setenv("PERFUME_CHEM_V5_INVENTORY", inventory_path)
    monkeypatch.delenv("SOLFORGE_INVENTORY_PATH", raising=False)
    monkeypatch.delenv("PERFUME_COMPLEXITY_INVENTORY_WORKBOOK", raising=False)
    monkeypatch.setattr(launcher.uvicorn, "run", fake_run)
    launcher.main()

    assert captured["host"] == "127.0.0.1"
    assert captured["reload"] is False
    assert os.environ["SOLFORGE_INVENTORY_PATH"] == inventory_path
    assert os.environ["PERFUME_COMPLEXITY_INVENTORY_WORKBOOK"] == inventory_path


def test_compose_publishes_host_ports_on_loopback_only():
    repo_root = Path(__file__).resolve().parents[3]
    compose = yaml.safe_load((repo_root / "docker-compose.yml").read_text(encoding="utf-8"))

    published_ports = [
        str(port)
        for service in compose["services"].values()
        for port in service.get("ports", [])
    ]

    assert published_ports
    assert all(port.startswith("127.0.0.1:") for port in published_ports)


def test_app_server_uses_real_path_containment_and_minimal_public_health():
    repo_root = Path(__file__).resolve().parents[3]
    source = (repo_root / "tools" / "app-server" / "server.mjs").read_text(
        encoding="utf-8"
    )

    assert "realpathSync.native" in source
    health_block = source.split('url.pathname === "/api/health"', maxsplit=1)[1].split(
        "if (!authorize", maxsplit=1
    )[0]
    assert "workspace:" not in health_block
    assert "head:" not in health_block


def test_app_server_rejects_a_file_reached_through_a_linked_parent(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("outside-workspace", encoding="utf-8")
    try:
        (workspace / "linked").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env.update(
        {
            "APP_SERVER_ROOT": str(workspace),
            "APP_SERVER_PORT": str(port),
            "APP_SERVER_TOKEN": "test-token",
        }
    )
    process = subprocess.Popen(
        [node, str(repo_root / "tools" / "app-server" / "server.mjs")],
        cwd=workspace,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        health_url = f"http://127.0.0.1:{port}/api/health"
        deadline = time.monotonic() + 10
        while True:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(f"app server stopped during startup: {stdout}\n{stderr}")
            try:
                with urllib.request.urlopen(health_url, timeout=1) as response:
                    health = json.load(response)
                break
            except (OSError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    pytest.fail("app server did not become ready")
                time.sleep(0.05)

        assert "workspace" not in health
        assert "head" not in health

        linked_path = urllib.parse.quote("linked/secret.txt")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/read?path={linked_path}",
            headers={"Authorization": "Bearer test-token"},
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=2)
        assert caught.value.code == 400
        body = json.loads(caught.value.read().decode("utf-8"))
        assert body["error"] == "real path escapes workspace"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
