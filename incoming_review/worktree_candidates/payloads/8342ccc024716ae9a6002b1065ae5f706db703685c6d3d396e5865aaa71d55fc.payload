# Perfume-Chem Worktree Registry and Semantic Leases

**Snapshot:** 2026-08-31, Asia/Bangkok  
**Purpose:** operational coordination for the Perfume Intelligence Plane Synthesis program  
**Rule:** worktree/task presence is not authority. Every integration claim requires
fresh path, Git, byte, hash, test, provenance, and authority verification.

## Verified Git/worktree census

The parent coordinator independently reran `git worktree list --porcelain`,
`git status --porcelain=v1 -uall`, branch/HEAD resolution, and SHA-256 hashing of
each live `inventory.txt` after the native read-only census.

| Worktree | Branch/state | HEAD | Dirty tracked/untracked | Inventory SHA-256 | Coordination state |
|---|---|---|---:|---|---|
| `D:\chatbots\perfume-chem` | `codex/add-inventory-materials` | `d99ecdca8b0a4bf741bd4dda7bd564649cf05982` | 147 / 1834 | `2cd7c6e6fbbc097132d0e76ece0cb481d56bd116358e63ec2debd4d2db10d3e5` | canonical but heavily dirty; preserve all overlaps |
| `C:\Users\ASUS\.codex\worktrees\3289\perfume-chem` | `codex/all-floral-depth-candidate` | `b5d0213ddf335a1eb48c4946a6661ffbcec20d0a` | 77 / 98 | `eb33c04236a4640413ba5289125f04cfa278bd0614eb9bd12ea1cc4d88379967` | unique floral/reference candidates; integration HOLD |
| `C:\Users\ASUS\.codex\worktrees\4046\perfume-chem` | detached | `c89e6a87ae5c9912ff988c758eab2cf8cc7e6582` | 23 / 4 | `06d5785656ea4eb644dfe9a355d5e98c8b0d8932d76caa24b997a68b4726ad13` | active Cypress successor; state changed during census; sole writer below |
| `C:\Users\ASUS\.codex\worktrees\6992\perfume-chem` | detached | `398800c5da43038f3159956362681a2ed92091f0` | 124 / 60 | `6745156000796fa3abe7072acb0629c0c63f56b5ad7ab94714b086a941234079` | active reference studio; sole writer below; integration HOLD |
| `C:\Users\ASUS\.codex\worktrees\a7e6\perfume-chem` | `codex/complex-perfumery-integration` | `482022c77bb81b1b65494666728e5c38fa77898f` | 4 / 5424 | `eb33c04236a4640413ba5289125f04cfa278bd0614eb9bd12ea1cc4d88379967` | historical/integration lineage; no current write lease |
| `C:\Users\ASUS\.codex\worktrees\b577\perfume-chem` | detached | `9f4c9f0f93756cecc20be02bda550a71f381bff4` | 25 / 191 | `eb33c04236a4640413ba5289125f04cfa278bd0614eb9bd12ea1cc4d88379967` | structural-studio theory/protocols; no current write lease |
| `C:\Users\ASUS\.codex\worktrees\edd7\perfume-chem` | `codex/luxe-target-native-finish` | `7f0f3119dae2ddf31979c7aa6360f5751b22db1c` | 1 / 1 | `eb33c04236a4640413ba5289125f04cfa278bd0614eb9bd12ea1cc4d88379967` | cleanest rejoinable factorial protocol branch; no current write lease |
| `C:\Users\ASUS\.codex\worktrees\perceptual-architecture-v1\perfume-chem` | `codex/perceptual-architecture-v1` | `af0d126ecf6c0ff84ea928b7b1dfe03b0d8d9e5b` | 4 / 2 | `eb33c04236a4640413ba5289125f04cfa278bd0614eb9bd12ea1cc4d88379967` | candidate/benchmark lineage; no current write lease |
| `C:\Users\ASUS\.codex\worktrees\publish-perfume-chem` | `codex/complex-perfumery-publish` | `6be61989ea9c395ead5a69a3a070fc2a7914c6a2` | 1 / 1661 | `eb33c04236a4640413ba5289125f04cfa278bd0614eb9bd12ea1cc4d88379967` | publish lineage plus test-temp artifacts; no current write lease |
| `D:\chatbots\perfume-chem\.worktrees\cypress-harmonic-synthesis-v1` | `codex/cypress-harmonic-synthesis-v1` | `c89e6a87ae5c9912ff988c758eab2cf8cc7e6582` | 4 / 0 | `eb33c04236a4640413ba5289125f04cfa278bd0614eb9bd12ea1cc4d88379967` | strongest committed Harmonic candidate; policy-only dirt; do not edit |
| `D:\chatbots\perfume-chem\.worktrees\cypress-mineral-traverse-v1` | `codex/cypress-mineral-traverse-v1` | `2290fa3a687f9b24d011072cd50089bb192aaf86` | 4 / 0 | `eb33c04236a4640413ba5289125f04cfa278bd0614eb9bd12ea1cc4d88379967` | bounded Cypress formula/protocol lineage; do not edit |

Counts and hashes are a point-in-time snapshot. The Cypress successor changed
while the first native audit was running, so its owning task must re-fingerprint
immediately before any readiness declaration.

## Explicit semantic leases

Only the named owner may write a leased path or contract. Everyone else is
read-only until the owner returns an exact manifest or the lease is explicitly
reassigned.

| Owner | Exact leased paths/contracts | Exclusions |
|---|---|---|
| Master coordinator `/root` | overall architecture; this registry; `docs/superpowers/specs/2026-08-31-perfume-intelligence-plane-synthesis-design.md`; cross-family hedonic contract; final scientific judgment; integration/admission | no direct edits to dirty Cypress, 6992, 3289, b577, edd7, or historical formulas |
| Master coordinator `/root` (lease returned by completed native child `/root/plane_foundation_ultra`) | `engine/formulation_intelligence/__init__.py`; `contracts.py`; `plane_synthesis.py`; `tests/test_formulation_intelligence_plane_synthesis.py` | structural foundation only; no formula, inventory, runtime, scorer, pipeline, or benchmark integration |
| User-owned task `Finish Cypress Inventory and Integration Gates` in detached `4046` | its existing 2026-08-31 inventory successor overlay, historical artifact registry, ledger type fix, stale inventory/KB/audit tests, CYP-02 rerun/analysis, and project-verification receipts | no named Cypress-branch edits, generic plane architecture, merge, push, physical/release claim without complete acceptance |
| User-owned task `Perfume-Chem Formulation Studio` in detached `6992` | `engine/families/registry.py`; `engine/pipeline/gates.py`; `engine/pipeline/oav_intelligence.py`; corresponding focused existing tests; Aventus/Explorer design; `future_modules/family_hedonic_optimizer.py`; new `tests/test_family_hedonic_optimizer.py` | no `engine/hedonic_model.py`; no `engine/family_scorer.py`; no global hedonic scalar; no inventory, ledger, CLI, formula, simulator, historical, or Cypress edit |
| Native child `/root/primary_research_ultra` | no files; primary-source evidence packet only | read-only |
| Native child `/root/architecture_critic_ultra` | no files; capability/omission/admission review only | read-only |
| Native child `/root/floral_lattice_ultra` | new `engine/formulation_intelligence/floral_lattice.py`; new `tests/test_formulation_intelligence_floral_lattice.py` | no edits to foundation, inventory, formulas, OAV runtime, Cypress, pipeline, or hedonic scoring |
| User-owned peer task `Perfume Intelligence Floral Evidence` (`01a0574f-8748-7130-80eb-a474ec40a4e8`) | no repository files; primary floral/configural evidence packet | read-only peer, not a subagent; shell-network failure is not evidence and may not widen authority |
| User-owned peer task `Perfume Intelligence Hedonic Evidence` (`01a0574f-cbde-7bd0-a71e-5fe1f42a34c4`) | no repository files; primary hedonic/temporal evidence packet | read-only peer, not a subagent; failed transport leaves claims UNKNOWN |
| User-owned peer task `Perfume Intelligence Benchmark Corpus` (`01a05750-1cb6-7010-ab29-084f6442aeb9`) | no repository files; adversarial frozen-benchmark design packet | read-only peer, not a subagent; cannot admit modules or select winners |

## High-risk overlap boundaries

- Root, 3289, 6992, b577, and 4046 all have divergent dirty inventory,
  material-data, formula-state, gate, or test surfaces. No direct copy or
  automatic semantic conflict resolution is authorized.
- Detached 4046 and the named Harmonic branch share committed HEAD but do not
  share working bytes.
- 3289 duplicates several committed Harmonic generic floral/depth modules; its
  unique value lies in later reference-evidence and adapters, not permission to
  import the whole dirty tree.
- `engine/hedonic_model.py`, `engine/family_scorer.py`, hard-coded accord ratios,
  and soliflore recipes remain unleased legacy semantics pending quarantine
  adjudication.
- The user-authoritative stock overlay is globally required before quantitative
  design, but live inventory hashes currently diverge. The new architecture may
  model inventory state but must not generate a quantitative build until an exact
  authority snapshot is chosen.

## Rejoin/readiness status

- **Rejoinable with low Git conflict:** committed Harmonic branch, mineral branch,
  and edd7. Rejoinable does not mean empirically validated.
- **Active but blocked:** 4046 and 6992.
- **Valuable but not integration-ready:** 3289 and b577.
- **Historical/intermediate:** a7e6, perceptual-architecture, publish.
- **Canonical:** authoritative workspace for final acceptance, but currently too
  dirty for broad integration.

No worktree or branch is authorized for deletion, pruning, merging, or pushing
by this registry.

## Structural foundation acceptance receipt

The parent independently inspected the completed native child's four-file
manifest, found and corrected one contract mismatch, and reran focused
verification. The child had implemented eleven plane IDs while the governing
design specifies twelve; the parent added the structural-only
`biological_sensitivity` plane ID and explicit regression coverage. This enum
addition grants no biological, sensory, formula, runtime, safety, or release
authority.

| Path | Bytes | Physical lines | SHA-256 after parent correction |
|---|---:|---:|---|
| `engine/formulation_intelligence/__init__.py` | 1,215 | 57 | `23e5ef2e9b28a03802e23cc8f2098fc0ffccb871b642db71e3e845c26172184f` |
| `engine/formulation_intelligence/contracts.py` | 32,375 | 945 | `d0e8f7ec67f91113c6d3a48edd2ee963f0ccde20e1c0278878a60749c0860386` |
| `engine/formulation_intelligence/plane_synthesis.py` | 25,922 | 680 | `97cf10588b98fe3a9fbff36b7e701a63ce18c9cd0da50fe3f38074223890ad0e` |
| `tests/test_formulation_intelligence_plane_synthesis.py` | 13,452 | 412 | `ce7bdb198311494e15f6a329f73cc83e8b94c87df52ad87c3c13335382ec7ead` |

Fresh parent checks in the canonical worktree:

- `.venv\Scripts\python.exe -m pytest tests\test_formulation_intelligence_plane_synthesis.py -q` — `9 passed`, with 360 pre-existing `pytest_asyncio` deprecation warnings.
- `.venv\Scripts\python.exe -m ruff check ...` limited to the four paths — clean.
- `.venv\Scripts\python.exe -m mypy ...` limited to the three package files — clean.

Acceptance is limited to the structural foundation contract. Runtime admission,
performance admission, full-project compatibility, module completeness, and
benchmark superiority remain unproven and therefore `HOLD`.
