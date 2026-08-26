# A3 plan: canonical serialization, quantities, provenance, and hashes

## Goal

Close A3 with one typed, versioned boundary for canonical payloads while
preserving existing `lab-export-v1` through `v4` compatibility and the reviewed
artifact-binding workflow.

## Verified gaps

- Canonical JSON hashing handles ordinary JSON deterministically but does not
  explicitly encode decimals, UUIDs, enums, dates, aware datetimes, sets, or
  algorithm metadata.
- Existing scalar quantity classes do not represent the full raw/active/carrier
  and solvent balance or return the required structured incomparability
  reasons.
- No single provenance model represents entity/activity/agent/derivation,
  transformation, software/model versions, uncertainty, and human review.
- Typed round-trip restoration is not centralized for nested canonical runtime
  types.
- Export revisions are supported for reading, but sequential migration into the
  current write revision is not an explicit public operation.

## TDD sequence

1. Add RED tests for nested typed serialization and strict future-version
   rejection.
2. Add RED tests for decimals, UUIDs, dates, aware datetimes, enums, tuples,
   sets, discriminated canonical records, extension namespaces, and quantity
   types.
3. Add RED tests for mass/volume and raw/active conversions, solvent balance,
   uncertainty, and every required incomparability reason.
4. Add RED tests for deterministic hash metadata and cross-platform golden
   bytes.
5. Add RED tests for W3C-PROV-shaped derivation and AI proposal review
   provenance.
6. Add RED tests for explicit export migration from every supported read
   revision to `lab-export-v4`.
7. Implement the minimal canonical boundary modules and sequential export
   migrator.
8. Run focused tests, root/backend suites, Ruff, mypy, artifact validation, and
   the full canonical verifier.

## Design boundaries

- Use tagged canonical JSON values; do not reconstruct arbitrary import paths or
  execute constructors named by untrusted payloads.
- Register allowed record types explicitly.
- Reject naive datetimes and unknown future schema majors.
- Preserve unknown fields only under a declared `extensions` object.
- Represent exact decimals as decimal strings.
- Keep legacy export writers stable; `lab-export-v4` remains the current write
  version.
- Keep the existing artifact re-read, hash, stale, tampered, and quarantine
  checks as the artifact-binding authority.

## Exit evidence

- Typed runtime round trips pass for all required types.
- Every supported export migrates to v4; future revisions fail closed.
- Quantity conversions either return a canonical value or a stable structured
  incomparability reason.
- Hash bytes and digests match reviewed golden fixtures.
- Provenance reconstructs derivation and review state.
- Artifact verifier has zero blocking unquarantined stale/tampered artifacts.
- Full verifier passes.
