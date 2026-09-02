from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from engine.bridge.canary import run_canary, verify_inventory
from engine.bridge.config import BridgeSettings
from engine.bridge.errors import BridgeBlocked
from engine.bridge.packet_intake import CONFIRMATION, stage_review_packet
from engine.bridge.receipts import canonical_json_bytes, seal_receipt
from engine.bridge.repository import fetch_repository_file, search_repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REPO = "geminipro529-cloud/perfume-chem"
CONVERSATION_ID = "6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf"


def _run(*args: str, cwd: Path) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


@pytest.fixture()
def disposable_repo(tmp_path: Path) -> Path:
    root = tmp_path / "perfume-chem"
    root.mkdir()
    _run("git", "init", "-b", "main", cwd=root)
    _run("git", "config", "user.email", "bridge-tests@example.invalid", cwd=root)
    _run("git", "config", "user.name", "Bridge Tests", cwd=root)
    _run(
        "git",
        "remote",
        "add",
        "origin",
        "git@github.com:geminipro529-cloud/perfume-chem.git",
        cwd=root,
    )

    (root / "engine").mkdir()
    (root / "engine" / "workbench.py").write_text(
        "class PerfumeWorkbench:\n    pass\n", encoding="utf-8"
    )
    (root / "scripts").mkdir()
    (root / "scripts" / "pipeline_audit.py").write_text(
        "import json, sys\n"
        "assert sys.argv[1] == 'project-verify'\n"
        "print(json.dumps({'completion_gate': 'PASS', 'failed': []}))\n",
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    (root / "docs" / "bridge_note.md").write_text(
        "Perfume bridge sentinel\nsecond line\n", encoding="utf-8"
    )
    protocol_dir = root / "chat_bridge" / "complex_perfumery"
    protocol_dir.mkdir(parents=True)
    (protocol_dir / "PROTOCOL.md").write_text(
        "# Chat Bridge Protocol v2.1\n", encoding="utf-8"
    )
    _run("git", "add", ".", cwd=root)
    _run("git", "commit", "-m", "test fixture", cwd=root)
    return root


@pytest.fixture()
def settings(disposable_repo: Path, tmp_path: Path) -> BridgeSettings:
    inventory = tmp_path / "Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5(1).xlsx"
    inventory.write_bytes(b"inventory-v5-test-bytes")
    protocol = disposable_repo / "chat_bridge" / "complex_perfumery" / "PROTOCOL.md"
    return BridgeSettings(
        repo_root=disposable_repo,
        expected_repository=EXPECTED_REPO,
        inventory_path=inventory,
        inventory_sha256=__import__("hashlib").sha256(inventory.read_bytes()).hexdigest(),
        inventory_bytes=inventory.stat().st_size,
        protocol_relative_path=Path("chat_bridge/complex_perfumery/PROTOCOL.md"),
        protocol_sha256=__import__("hashlib").sha256(protocol.read_bytes()).hexdigest(),
        conversation_id=CONVERSATION_ID,
        packet_writes_enabled=True,
        signing_key=b"test-signing-key",
        verify_timeout_seconds=30,
        allowed_read_prefixes=("docs", "engine", "chat_bridge/complex_perfumery"),
        max_read_bytes=64 * 1024,
        forbidden_roots=(tmp_path / "forbidden",),
    )


def test_canonical_json_and_receipt_are_deterministic() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    left = seal_receipt({"b": 2, "a": 1}, b"secret")
    right = seal_receipt({"a": 1, "b": 2}, b"secret")
    assert left["receipt_sha256"] == right["receipt_sha256"]
    assert left["signature"]["algorithm"] == "HMAC-SHA256"
    assert left["signature"]["state"] == "SIGNED"
    assert "secret" not in json.dumps(left)


def test_unsigned_receipt_is_explicit() -> None:
    result = seal_receipt({"state": "BRIDGE_BLOCKED"}, None)
    assert result["signature"] == {"algorithm": "HMAC-SHA256", "state": "UNSIGNED"}


def test_settings_environment_does_not_default_packet_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERFUME_CHEM_PACKET_WRITES", raising=False)
    monkeypatch.delenv("PERFUME_CHEM_BRIDGE_SIGNING_KEY", raising=False)
    resolved = BridgeSettings.from_env()
    assert resolved.packet_writes_enabled is False
    assert resolved.signing_key is None
    assert resolved.inventory_sha256 == "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
    assert resolved.inventory_bytes == 199635


def test_inventory_authority_matches_exact_bytes_and_hash(settings: BridgeSettings) -> None:
    result = verify_inventory(settings)
    assert result["status"] == "PASS"
    assert result["sha256"] == settings.inventory_sha256
    assert result["bytes"] == settings.inventory_bytes


def test_inventory_authority_fails_on_modified_bytes(settings: BridgeSettings) -> None:
    settings.inventory_path.write_bytes(b"changed")
    result = verify_inventory(settings)
    assert result["status"] == "FAIL"
    assert "sha256" in result["failures"]
    assert "bytes" in result["failures"]


def test_metadata_canary_never_claims_pass(settings: BridgeSettings) -> None:
    result = run_canary(settings, mode="metadata")
    assert result["state"] == "READY_FOR_VERIFICATION"
    assert result["repository"]["head"]
    assert result["repository"]["origin_normalized"] == EXPECTED_REPO
    assert result["verification"]["status"] == "NOT_RUN"
    assert result["security"]["secrets_exposed"] is False


def test_full_canary_passes_disposable_repository(settings: BridgeSettings) -> None:
    result = run_canary(settings, mode="full")
    assert result["state"] == "PASS"
    assert result["verification"]["status"] == "PASS"
    assert result["runtime"]["workbench_import"]["status"] == "PASS"
    assert result["protocol"]["status"] == "PASS"


def test_quick_canary_passes_disposable_repository(settings: BridgeSettings) -> None:
    result = run_canary(settings, mode="quick")
    assert result["state"] == "PASS"
    assert "--quick" in result["verification"]["command"]


def test_canary_blocks_wrong_origin(settings: BridgeSettings) -> None:
    _run("git", "remote", "set-url", "origin", "https://github.com/other/repo.git", cwd=settings.repo_root)
    result = run_canary(settings, mode="metadata")
    assert result["state"] == "BRIDGE_BLOCKED"
    assert result["repository"]["origin_status"] == "FAIL"


def test_canary_blocks_dirty_repository(settings: BridgeSettings) -> None:
    (settings.repo_root / "docs" / "bridge_note.md").write_text("dirty", encoding="utf-8")
    result = run_canary(settings, mode="full")
    assert result["state"] == "BRIDGE_BLOCKED"
    assert result["repository"]["dirty"] is True


def test_canary_blocks_missing_protocol_hash(settings: BridgeSettings) -> None:
    blocked = settings.with_overrides(protocol_sha256=None)
    result = run_canary(blocked, mode="full")
    assert result["state"] == "BRIDGE_BLOCKED"
    assert result["protocol"]["status"] == "FAIL"


def test_canary_blocks_forbidden_root(settings: BridgeSettings) -> None:
    blocked = settings.with_overrides(forbidden_roots=(settings.repo_root.parent,))
    result = run_canary(blocked, mode="metadata")
    assert result["state"] == "BRIDGE_BLOCKED"
    assert result["repository"]["root_status"] == "FAIL"


def test_fetch_and_search_are_confined(settings: BridgeSettings) -> None:
    fetched = fetch_repository_file(settings, "docs/bridge_note.md", max_chars=100)
    assert fetched["content"].startswith("Perfume bridge sentinel")
    results = search_repository(settings, "sentinel", limit=5)
    assert results["matches"][0]["path"] == "docs/bridge_note.md"
    assert results["matches"][0]["line"] == 1


def test_fetch_rejects_path_traversal_and_disallowed_extensions(settings: BridgeSettings) -> None:
    with pytest.raises(BridgeBlocked):
        fetch_repository_file(settings, "../outside.txt")
    binary = settings.repo_root / "docs" / "secret.xlsx"
    binary.write_bytes(b"not allowed")
    with pytest.raises(BridgeBlocked):
        fetch_repository_file(settings, "docs/secret.xlsx")


def test_fetch_rejects_symlink_escape(settings: BridgeSettings, tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink unavailable")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = settings.repo_root / "docs" / "escape.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(BridgeBlocked):
        fetch_repository_file(settings, "docs/escape.md")


def _packet() -> dict[str, object]:
    nonce = str(uuid4())
    return {
        "protocol": "Chat Bridge Protocol v2.1",
        "packet_type": "COMPLEX_PERFUMERY_INCOMING_REVIEW_HANDOFF",
        "packet_id": f"CB-{CONVERSATION_ID}-{nonce}",
        "nonce": nonce,
        "conversation_id": CONVERSATION_ID,
        "authority": "INCOMING_REVIEW_ONLY",
        "canonical_mutation_authorized": False,
        "formula_mutation_authorized": False,
        "claims": [],
    }


def test_stage_packet_requires_full_passing_receipt(settings: BridgeSettings) -> None:
    packet = _packet()
    metadata = run_canary(settings, mode="metadata")
    with pytest.raises(BridgeBlocked, match="full PASS"):
        stage_review_packet(settings, packet, metadata, CONFIRMATION)


def test_stage_packet_is_atomic_and_refuses_overwrite(settings: BridgeSettings) -> None:
    packet = _packet()
    full = run_canary(settings, mode="full")
    first = stage_review_packet(settings, packet, full, CONFIRMATION)
    packet_path = Path(first["packet_path"])
    assert packet_path.exists()
    written = json.loads(packet_path.read_text(encoding="utf-8"))
    assert written["authority"] == "INCOMING_REVIEW_ONLY"
    assert written["canonical_mutation_authorized"] is False
    with pytest.raises(BridgeBlocked, match="already exists"):
        stage_review_packet(settings, packet, full, CONFIRMATION)


def test_stage_packet_rejects_mutation_flags_and_wrong_confirmation(settings: BridgeSettings) -> None:
    full = run_canary(settings, mode="full")
    packet = _packet()
    packet["formula_mutation_authorized"] = True
    with pytest.raises(BridgeBlocked, match="mutation"):
        stage_review_packet(settings, packet, full, CONFIRMATION)
    with pytest.raises(BridgeBlocked, match="confirmation"):
        stage_review_packet(settings, _packet(), full, "yes")


def test_stage_packet_requires_write_arm_and_signing_key(settings: BridgeSettings) -> None:
    full = run_canary(settings, mode="full")
    with pytest.raises(BridgeBlocked, match="disabled"):
        stage_review_packet(
            settings.with_overrides(packet_writes_enabled=False),
            _packet(),
            full,
            CONFIRMATION,
        )
    with pytest.raises(BridgeBlocked, match="signing key"):
        stage_review_packet(
            settings.with_overrides(signing_key=None),
            _packet(),
            full,
            CONFIRMATION,
        )


def test_server_declares_expected_tool_contracts() -> None:
    server_source = (PROJECT_ROOT / "engine" / "bridge" / "server.py").read_text(encoding="utf-8")
    expected_tools = {
        "perfume_chem_bridge_status",
        "perfume_chem_inventory_authority",
        "perfume_chem_search",
        "perfume_chem_fetch",
        "perfume_chem_stage_review_packet",
    }
    for tool_name in expected_tools:
        assert f'name="{tool_name}"' in server_source
    assert server_source.count("read_only_hint=True") >= 4
    assert "destructive_hint=False" in server_source
    assert "open_world_hint=False" in server_source


def test_full_canary_parses_large_verifier_json(settings: BridgeSettings) -> None:
    script = settings.repo_root / "scripts" / "pipeline_audit.py"
    script.write_text(
        "import json\nprint(json.dumps({'completion_gate': 'PASS', 'failed': [], 'padding': 'x' * 5000}))\n",
        encoding="utf-8",
    )
    _run("git", "add", "scripts/pipeline_audit.py", cwd=settings.repo_root)
    _run("git", "commit", "-m", "large verifier fixture", cwd=settings.repo_root)
    result = run_canary(settings, mode="full")
    assert result["state"] == "PASS"
    assert result["verification"]["status"] == "PASS"


def test_canary_redacts_credentials_embedded_in_origin(settings: BridgeSettings) -> None:
    credential = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    _run(
        "git",
        "remote",
        "set-url",
        "origin",
        f"https://x-access-token:{credential}@github.com/geminipro529-cloud/perfume-chem.git",
        cwd=settings.repo_root,
    )
    result = run_canary(settings, mode="metadata")
    assert result["state"] == "READY_FOR_VERIFICATION"
    assert credential not in json.dumps(result)
    assert "x-access-token" not in json.dumps(result)


def test_from_env_cannot_rewrite_fixed_authorities(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERFUME_CHEM_EXPECTED_REPOSITORY", "attacker/other")
    monkeypatch.setenv("PERFUME_CHEM_INVENTORY_SHA256", "0" * 64)
    monkeypatch.setenv("PERFUME_CHEM_INVENTORY_BYTES", "1")
    monkeypatch.setenv("PERFUME_CHEM_CONVERSATION_ID", str(uuid4()))
    monkeypatch.setenv("PERFUME_CHEM_PROTOCOL_PATH", "elsewhere/PROTOCOL.md")
    monkeypatch.setenv("PERFUME_CHEM_READ_PREFIXES", "../,.git,docs")
    monkeypatch.setenv("PERFUME_CHEM_FORBIDDEN_ROOTS", str(Path("D:/only-extra")))
    resolved = BridgeSettings.from_env()
    assert resolved.expected_repository == EXPECTED_REPO
    assert resolved.inventory_sha256 == "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
    assert resolved.inventory_bytes == 199635
    assert resolved.conversation_id == CONVERSATION_ID
    assert resolved.protocol_relative_path == Path("chat_bridge/complex_perfumery/PROTOCOL.md")
    assert ".." not in resolved.allowed_read_prefixes
    assert ".git" not in resolved.allowed_read_prefixes
    assert Path(r"D:\3_way_nano_drug_project") in resolved.forbidden_roots


def test_protocol_hash_without_identity_marker_still_blocks(settings: BridgeSettings) -> None:
    protocol = settings.repo_root / settings.protocol_relative_path
    protocol.write_text("# Unrelated protocol\n", encoding="utf-8")
    _run("git", "add", protocol.relative_to(settings.repo_root).as_posix(), cwd=settings.repo_root)
    _run("git", "commit", "-m", "wrong protocol identity", cwd=settings.repo_root)
    changed = settings.with_overrides(
        protocol_sha256=__import__("hashlib").sha256(protocol.read_bytes()).hexdigest()
    )
    result = run_canary(changed, mode="full")
    assert result["state"] == "BRIDGE_BLOCKED"
    assert "identity_marker" in result["protocol"]["failures"]


def test_module_help_does_not_require_optional_mcp_dependency() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "engine.bridge", "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert completed.returncode == 0
    assert "canary" in completed.stdout
    assert "stage" in completed.stdout
    assert "serve" in completed.stdout


def test_metadata_then_full_canary_keeps_repository_clean(settings: BridgeSettings) -> None:
    metadata = run_canary(settings, mode="metadata")
    assert metadata["state"] == "READY_FOR_VERIFICATION"
    full = run_canary(settings, mode="full")
    assert full["state"] == "PASS"
    assert full["repository"]["dirty"] is False
    assert full["repository"]["head_unchanged"] is True


def test_full_canary_blocks_verifier_that_mutates_repository(settings: BridgeSettings) -> None:
    script = settings.repo_root / "scripts" / "pipeline_audit.py"
    script.write_text(
        "from pathlib import Path\n"
        "import json\n"
        "Path('verifier-side-effect.txt').write_text('mutation', encoding='utf-8')\n"
        "print(json.dumps({'completion_gate': 'PASS', 'failed': []}))\n",
        encoding="utf-8",
    )
    _run("git", "add", "scripts/pipeline_audit.py", cwd=settings.repo_root)
    _run("git", "commit", "-m", "mutating verifier fixture", cwd=settings.repo_root)
    result = run_canary(settings, mode="full")
    assert result["state"] == "BRIDGE_BLOCKED"
    assert result["repository"]["dirty"] is True
    assert "dirty_worktree" in result["repository"]["failures"]


def test_write_tool_exposure_defaults_off_and_can_be_armed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PERFUME_CHEM_EXPOSE_WRITE_TOOL", raising=False)
    assert BridgeSettings.from_env().expose_write_tool is False
    monkeypatch.setenv("PERFUME_CHEM_EXPOSE_WRITE_TOOL", "1")
    assert BridgeSettings.from_env().expose_write_tool is True


def test_server_write_tool_registration_is_explicitly_conditional() -> None:
    server_source = (PROJECT_ROOT / "engine" / "bridge" / "server.py").read_text(
        encoding="utf-8"
    )
    assert "if _settings().expose_write_tool:" in server_source
