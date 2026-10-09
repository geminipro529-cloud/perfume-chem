# Reconstruction pipeline

> Moved out of `AGENTS.md` unchanged on 2026-10-08 so every session loads less; `AGENTS.md` links here. These are working notes and historical diagnostics, not universal policy: where they disagree with the rules in `AGENTS.md` (Rules 0-7 and the reviewed knowledge boundary), those rules win.

## Reconstruction Pipeline

> **New: `scripts/reconstruct.py`** — Evidence-driven formula reconstruction CLI.
> **New: `engine/reconstruction/`** — Purpose-built reconstruction engine (10 modules).
> **New: `engine/identity/`, `engine/units/`, `engine/versioning/`, `engine/inventory/`, `engine/evidence/`, `engine/target/`, `engine/bottle/`** — Foundation service modules.
> **New: `engine/graphs/`, `engine/reports/`** — Accord graph and report generation.

### Architecture

The reconstruction system uses a **layered ledger architecture** — nothing jumps across layers:

```
Evidence → Target hypothesis → Accepted target → Accord/DNA graph →
Chassis derivation → Inventory mapping → Build formula →
Bottle events → Analytical/sensory results → Updated target
```

- **Evidence ledger**: What sources claim (notes, labels, GC-MS, rosters)
- **Target ledger**: Best current hypothesis, independent of inventory
- **Inventory ledger**: What is physically available (stock, lot, concentration)
- **Build ledger**: Inventory-mapped formula with explicit substitutions
- **Bottle ledger**: Event-sourced physical bottle state (immutable events)
- **Analysis ledger**: Model runs and analytical instrument outputs
- **Sensory ledger**: Coded sample evaluations with time-resolved ratings

**Critical rule**: Missed inventory must NEVER alter the target. Substitutions are in the build layer only.

### Operating Modes

All engine operations require an explicit mode:

| Mode | Purpose |
|------|---------|
| `RECONSTRUCTION` | Evidence gathering, identity inference, dose distributions |
| `CREATIVE_FORMULATION` | New materials, hedonic optimization, cost constraints |
| `STRUCTURAL_CHASSIS` | Partition target into core + module, derive flankers |
| `FLANKER_MODULE` | Design alternative socket modules |
| `INVENTORY_MAPPING` | Map target to available stock with substitution reports |
| `LIVE_BATCH` | Propose/confirm/commit physical bottle additions |
| `BATCH_RESCUE` | Corrective additions to already-mixed bottles |
| `SENSORY_EXPERIMENT` | Design/evaluate coded blind trials |
| `ANALYTICAL_INTERPRETATION` | Import instrument data (GC-MS, HS-SPME, GC-O) |
| `COMPLIANCE_BUILD` | Generate jurisdiction-specific compliant formulas |
| `RELEASE_REVIEW` | Full gate evaluation for release |

### CLI Usage

```bash
# Reconstruct from evidence
python scripts/reconstruct.py --mode RECONSTRUCTION build \
    --evidence evidence.json --brief prada_clean_iris \
    --output target.json

# Derive chassis partition
python scripts/reconstruct.py --mode STRUCTURAL_CHASSIS chassis \
    --target target.json \
    --envelope configs/reconstruction/prada_lhomme_envelope.json \
    --output chassis.md

# Generate alternative module
python scripts/reconstruct.py --mode FLANKER_MODULE module \
    --chassis chassis.json --direction "soft_amber_tonka" \
    --output module.json

# Validate chassis integrity
python scripts/reconstruct.py validate --chassis chassis.json
```

### New Pipeline Gates

Three new gates added to `engine/pipeline/gates.py`:
- **`mode_protection`**: Blocks actions inappropriate for current operating mode
- **`chassis_integrity`**: Validates core+module=target row-by-row arithmetic (SKIP if no chassis)
- **`authority_vector`**: Reports per-dimension authority (identity, quantity, grade, sensory, safety, etc.) — NEVER averaged into one score

### Material Identity Model

Materials are tracked through an identity chain, NOT silently collapsed:

- **Synthetic**: `chemical_entity → stereoisomer → trade_grade → supplier_product → supplier_lot → stock_solution`
- **Natural**: `botanical_species → plant_part → chemotype → origin → extraction_method → supplier_lot → analytical_composition → stock_solution`

Non-equivalent materials that must NOT be collapsed: Habanolide↔Galaxolide, Muscenone Delta↔Exaltolide, Alpha Isomethyl Ionone↔Methyl Ionone Gamma Coeur, Bacdanol↔Sandalore, Haitian↔Indian vetiver, Lavender↔Lavandin.

### Concentration Basis Enforcement

All concentrations must declare basis: `10% w/w`, `50% in DPG`, `30% v/v`. Naked `10%` fails validation. Use `engine/units/concentration.parse_concentration()`.

### Active Accounting Fix

DPG and carriers are NOT odorant-active. `engine/units/concentration.compute_active_accounting()` separates `odorant_active_ul`, `technical_active_ul`, `carrier_ul`, `solvent_ul`. The formula L'Homme chassis previously reported 3,692 µL active — the corrected odorant-active is 3,592 µL.

### Module Envelopes

Config files in `configs/reconstruction/` define chassis partition constraints:
- `protected_anchor_floors_in_core_uL`: Minimum core retention per recognizer
- `required_module_roles`: Functional roles the module MUST cover
- `forbidden_drift`: Character directions the module MUST NOT take
- Module volume alone is insufficient — envelopes track active mass, carrier mass, volatility centroid, T/H/B distribution, odor-family vector, polarity, and color risk.

### Event-Sourced Bottles

Bottle state is reconstructed from immutable events. Never delete — CORRECT_ENTRY for fixes. AI can only PROPOSE; user CONFIRMS → MEASURES → COMMITS. One irreversible action at a time.

### Known Limitations

- OAV from the pipeline is heuristic, matrix-omitted, and not a sensory-equivalence claim
- Naturals need lot-specific composition profiles for accurate modeling
- Unknown/captive materials remain as UNKNOWN_* nodes; do not force into catalog names
- Markdown formula files are GENERATED VIEWS; structured JSON is canonical source of truth
- A hash verifies content — it does not store or reconstruct content
