# Build A Phase A3 authoritative reverification plan

Date: 2026-08-02

## Goal

Re-evaluate the existing A3 implementation against the authoritative working
tree and the master A3 exit conditions. Historical reports are evidence
leads only. No production change is permitted unless a reproduced failure or
contract gap requires one.

## Constraints

- Preserve the dirty working tree and archive every tracked file before an
  edit.
- Do not modify either SQLite database, add a migration, regenerate release
  artifacts, clean unrelated files, or transmit secrets.
- Use the repository Python environment, non-PTY commands, captured stdout and
  stderr, disabled ANSI output, and explicit timeouts.
- Keep the generic app DeepLuna connector fail-closed because it is bound to
  the wrapper workspace. Use only a fresh exact-project Fast lifecycle.
- Sol owns scope, architecture, provenance, and final acceptance.

## Execution

1. Re-run the focused typed-serialization, quantity, canonical-hashing,
   provenance, artifact-rebind, run-evidence, and export-migration tests.
2. Re-run the artifact verifier and count blocking and non-blocking states.
3. Hash both SQLite files, run read-only SQLite checks, and record their live
   schema state without reading application rows.
4. Reconcile those results with the latest full canonical verifier produced
   from the same source state.
5. If all contracts pass, change documentation only. If a reproducible gap is
   found, archive the affected files and repair it test-first.
6. Run a fresh exact-project readiness check and one bounded DeepLuna Fast
   audit over the A3 contract and concise current evidence.
7. Re-run focused local verification after the report update, inspect the
   exact diff, and checkpoint only A3-owned documentation after Sol accepts
   the gate.

## Exit decision

A3 passes only when typed round-trips preserve runtime meaning, every
supported export migrates explicitly, unsafe quantity comparisons fail with
structured reasons, hashes are deterministic and versioned, provenance and AI
review metadata reconstruct the derivation, artifact binding has no blocking
unquarantined stale or tampered item, and the canonical verifier remains
passing. Scientific release authority is outside this software gate.
