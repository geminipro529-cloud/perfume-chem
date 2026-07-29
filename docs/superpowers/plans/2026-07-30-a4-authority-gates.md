# A4 Authority Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking. Repository policy forbids Codex
> subagents here, so Sol executes inline.

**Goal:** Implement typed operating-mode, action-transition, claim, family,
concentration, and regulatory gates with stable fail-closed reasons.

**Architecture:** Add one pure policy module and two narrow adapters: the
existing formula mode gate and the versioned claim-persistence service. Keep
legacy A2 claim behavior compatible while making `a4-claim-v1` computed rather
than caller-authoritative.

**Tech Stack:** Python 3.11 dataclasses/enums, pytest, existing FastAPI and
SQLAlchemy service layer, repository-owned verifier.

---

### Task 1: RED domain policy tests

**Files:**
- Create: `tests/test_authority_gates.py`

- [ ] Write tests importing the desired actor, state, mode, claim, family, and
  regulatory APIs.
- [ ] Assert AI confirmation and release are denied, unsupported transitions
  are denied, and evidence/safety/confirmation failures have stable reasons.
- [ ] Parameterize all eleven modes with one allowed and one blocked action.
- [ ] Parameterize all nine claim types with the missing dimension that must
  block or withhold that claim.
- [ ] Run:
  `python -m pytest -q tests/test_authority_gates.py`
  and confirm collection fails because `engine.authority_gates` does not exist.

### Task 2: GREEN domain module

**Files:**
- Create: `engine/authority_gates.py`

- [ ] Define `ActorType`, `ActionState`, `OperatingMode`, `ModeAction`,
  `ClaimType`, `ClaimDecision`, `RegulatoryDecision`, and `GateReason`.
- [ ] Define immutable `GateEvaluation`, `PermissionContext`,
  `ClaimAuthorityInput`, `FamilyEvaluationInput`, and `RegulatorySnapshot`.
- [ ] Implement closed transition and mode-action allowlists.
- [ ] Implement claim-specific boolean requirement maps; never aggregate to a
  score.
- [ ] Implement family and regulatory evaluators with exact A4 reason codes.
- [ ] Run the focused test and confirm all cases pass.

### Task 3: RED/GREEN pipeline mode adapter

**Files:**
- Modify: `engine/pipeline/gates.py`
- Modify: `tests/test_pipeline_gates.py`

- [ ] Add failing tests showing an explicit blocked mode/action pair fails and
  an allowed pair passes.
- [ ] Add `action: str = "reports"` to `ReleaseGateConfig`.
- [ ] Replace `_gate_mode_protection` string tables with
  `evaluate_mode_action`; unknown strings fail closed.
- [ ] Run the two mode tests and the complete pipeline-gate test file.

### Task 4: RED/GREEN versioned claim adapter

**Files:**
- Modify: `backend/app/services/lab_science.py`
- Modify: `backend/tests/unit/test_a2_science_service.py`

- [ ] Add a failing service test where `a4-claim-v1` requests
  `ALLOW_EXACT` with no source independence, sensory support, or safety
  completeness.
- [ ] Add a passing scoped identity fixture with all dimensions required for
  that claim.
- [ ] Parse `authority_json` through `ClaimAuthorityInput.from_mapping`.
- [ ] Compute the maximum decision and reject overclaims with
  `CLAIM_DECISION_EXCEEDS_AUTHORITY`.
- [ ] Preserve existing `a2-claim-v1` behavior and rerun all science-service
  tests.

### Task 5: Canonical verification integration

**Files:**
- Modify: `engine/project_verification.py`
- Create: `docs/verification/a4_exit_gate.md`

- [ ] Register the new module in Ruff/MyPy and the test once in the truth-core
  shard.
- [ ] Run focused tests, full root/backend suites, artifact verification, and
  the full project verifier with explicit timeouts and ANSI disabled.
- [ ] Restore and integrity-check `data/perfumery_kb.db`; verify the protected
  canonical database hash.
- [ ] Record exact test counts, report hash, stable negative reasons, and the
  continuing scientific-release blocker.
- [ ] Commit only A4 paths.
