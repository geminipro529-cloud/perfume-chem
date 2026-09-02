# Perfume-Chem Fail-Closed MCP Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a locally hosted, tool-only MCP bridge that exposes bounded Perfume-Chem repository reads and a guarded, nonce-scoped incoming-review write.

**Architecture:** Standard-library bridge core under `engine/bridge`, with an optional MCP v2 adapter in `engine/bridge/server.py`. Every operation is fail-closed, receipt-bearing, path-confined, and separate from canonical LabService, formula, inventory, bottle, migration, and release writes.

**Tech Stack:** Python 3.11, Git CLI, pytest, MCP Python SDK v2, Starlette/Uvicorn supplied by the MCP dependency.

**Spec:** `docs/superpowers/specs/2026-09-03-perfume-chem-mcp-bridge-design.md`

## Global Constraints

- Inventory V5 must equal 199,635 bytes and SHA-256 `e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`.
- The expected repository is `geminipro529-cloud/perfume-chem` at local root `D:\chatbots\perfume-chem` unless explicitly overridden for a test.
- Packet staging requires the exact Chat Bridge Protocol v2.1 file and configured hash.
- No formula, inventory, bottle, database, migration, release, Git, or canonical-state mutation is permitted.
- No arbitrary command execution or unrestricted file access is permitted.
- Metadata probes cannot return `PASS`; only repository-native quick/full verification may do so.
- Packet staging requires a full `PASS`, write arm, signing key, exact confirmation, and a new nonce directory.
- DeepLuna Fast remains disabled.

---

### Task 1: Canonical receipts and bridge configuration

**Files:**
- Create: `engine/bridge/__init__.py`
- Create: `engine/bridge/config.py`
- Create: `engine/bridge/receipts.py`
- Test: `tests/test_perfume_chem_bridge.py`

**Interfaces:**
- Produces: `BridgeSettings.from_env()`, `canonical_json_bytes(value)`, and `seal_receipt(payload, signing_key)`.

- [ ] **Step 1: Write failing receipt and configuration tests**

```python
def test_seal_receipt_is_deterministic_and_does_not_expose_key():
    left = seal_receipt({"b": 2, "a": 1}, b"secret")
    right = seal_receipt({"a": 1, "b": 2}, b"secret")
    assert left["receipt_sha256"] == right["receipt_sha256"]
    assert left["signature"]["algorithm"] == "HMAC-SHA256"
    assert "secret" not in json.dumps(left)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pytest tests/test_perfume_chem_bridge.py -q`

Expected: import failure because `engine.bridge` does not yet exist.

- [ ] **Step 3: Implement immutable settings and canonical receipt sealing**

Use sorted compact JSON, UTF-8, SHA-256, and optional HMAC-SHA256. Environment booleans accept only `1`, `true`, `yes`, or `on`.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `pytest tests/test_perfume_chem_bridge.py -q`

Expected: receipt and configuration tests pass.

### Task 2: Repository and authority canary

**Files:**
- Create: `engine/bridge/canary.py`
- Modify: `tests/test_perfume_chem_bridge.py`

**Interfaces:**
- Consumes: `BridgeSettings`, `seal_receipt`.
- Produces: `run_canary(settings, mode)` and `verify_inventory(settings)`.

- [ ] **Step 1: Write failing disposable-repository canary tests**

```python
def test_metadata_canary_never_claims_pass(disposable_repo, settings):
    receipt = run_canary(settings, mode="metadata")
    assert receipt["state"] == "READY_FOR_VERIFICATION"
    assert receipt["repository"]["head"]
    assert receipt["verification"]["status"] == "NOT_RUN"
```

Include negative tests for wrong origin, dirty repository, wrong inventory bytes, absent protocol hash, and forbidden root.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pytest tests/test_perfume_chem_bridge.py -q`

Expected: missing canary symbols.

- [ ] **Step 3: Implement fixed-command probes**

Probe Git root, origin, branch, HEAD, dirty status, worktrees, Python, workbench import, migration heads, Inventory V5, protocol bytes, and repository-native verifier. Hash stdout/stderr rather than returning unbounded output.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `pytest tests/test_perfume_chem_bridge.py -q`

Expected: all canary tests pass.

### Task 3: Confined repository reads and atomic packet staging

**Files:**
- Create: `engine/bridge/repository.py`
- Create: `engine/bridge/packet_intake.py`
- Modify: `tests/test_perfume_chem_bridge.py`

**Interfaces:**
- Produces: `search_repository`, `fetch_repository_file`, and `stage_review_packet`.

- [ ] **Step 1: Write failing confinement and packet tests**

```python
def test_fetch_rejects_path_traversal(settings):
    with pytest.raises(BridgeBlocked):
        fetch_repository_file(settings, "../.env")


def test_stage_packet_refuses_overwrite(settings, passing_full_receipt):
    stage_review_packet(settings, packet(), passing_full_receipt, CONFIRMATION)
    with pytest.raises(BridgeBlocked):
        stage_review_packet(settings, packet(), passing_full_receipt, CONFIRMATION)
```

Also test disabled writes, missing signing key, wrong conversation, invalid nonce, true mutation flags, protocol mismatch, and escaped symlink.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pytest tests/test_perfume_chem_bridge.py -q`

Expected: missing repository and packet modules.

- [ ] **Step 3: Implement bounded reads and exclusive packet creation**

Search only allowlisted UTF-8 text files. Use `Path.resolve()` confinement. Create `PACKET.json` with exclusive file creation and include a receipt hash; never create or update any other file.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `pytest tests/test_perfume_chem_bridge.py -q`

Expected: all core bridge tests pass.

### Task 4: MCP adapter, operator documentation, and release checks

**Files:**
- Create: `engine/bridge/server.py`
- Create: `engine/bridge/__main__.py`
- Create: `requirements-bridge.txt`
- Create: `docs/perfume_chem_bridge.md`
- Modify: `tests/test_perfume_chem_bridge.py`

**Interfaces:**
- Produces: ASGI `app`, four default read-only MCP tools, one optional guarded write tool, and a local packet-stage CLI.

- [ ] **Step 1: Write a static adapter-contract test**

Verify four read-only tools are registered by default, the packet-stage tool is registered only behind `PERFUME_CHEM_EXPOSE_WRITE_TOOL=1`, and all annotations match their effects.

- [ ] **Step 2: Run the static contract test and verify RED**

Run: `pytest tests/test_perfume_chem_bridge.py -q`

Expected: missing server module/file.

- [ ] **Step 3: Implement the MCP v2 adapter and operator guide**

Keep `mcp` imports isolated to `server.py`. Document Windows environment configuration, local loopback launch, Inspector testing, Secure MCP Tunnel or an authenticated HTTPS boundary, ChatGPT developer-mode connection, and exact canary commands.

- [ ] **Step 4: Run syntax and unit verification**

Run:

```text
python -m compileall -q engine/bridge
pytest tests/test_perfume_chem_bridge.py -q
```

Expected: exit code 0 for both commands.

- [ ] **Step 5: Run a disposable end-to-end canary**

Create a disposable Git repository with the expected origin, exact synthetic inventory/protocol locks, stub `PerfumeWorkbench`, and a stub repository-native verifier. Run metadata and full modes, then stage one packet and confirm the second write is rejected.

- [ ] **Step 6: Create an isolated GitHub branch and draft pull request**

Branch from the exact reviewed `master` commit. Upload only reviewed bridge files. Do not merge, modify canonical state, or claim local deployment.
