# Build A Phase A4 authoritative reverification plan

Date: 2026-08-02

## Goal

Reproduce the A4 mode, transition, claim-authority, family, concentration, and
regulatory gates from the authoritative tree. Historical reports are leads
only; production changes require a reproduced contract failure.

## Constraints

- Preserve the dirty tree and archive every tracked file before editing it.
- Do not change migrations, databases, generated release artifacts, or
  unrelated work.
- Use supported Python 3.11 verification environments, non-PTY commands,
  disabled ANSI output, captured machine evidence, and explicit timeouts.
- Delegate only a bounded read-only audit through a fresh exact-project
  DeepLuna Fast lifecycle. Sol retains architecture and final acceptance.

## Execution

1. Read the complete A4 handoff contract and inventory the live implementation,
   tests, pipeline integration, service enforcement, database state, branch,
   and commit.
2. Run the authority and pipeline tests plus the complete science-service test
   module under supported environments.
3. Run focused Ruff and MyPy checks over the A4 production and test surfaces.
4. Use a bounded Fast audit to map every A4 requirement and negative-test axis
   to the live implementation and identify any hidden blocking gap.
5. If a gap exists, archive affected files and repair it test-first. Otherwise,
   update evidence documentation only.
6. Re-run focused tests after documentation finalization, check the exact diff,
   and checkpoint only A4-owned documentation after Sol accepts the gate.

## Exit decision

A4 passes only when actor/state transitions and all eleven modes fail closed,
all nine claim axes are evaluated independently, family/concentration/safety
gates preserve unknowns, overclaims cannot be persisted, and unsupported
identity, quantity, family, safety, sensory, analytical, and release claims
return stable withholding or blocking reasons.
