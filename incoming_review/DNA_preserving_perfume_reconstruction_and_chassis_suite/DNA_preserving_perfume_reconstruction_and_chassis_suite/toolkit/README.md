# Universal Non-Compressed Perfume Reconstruction Toolkit

This starter kit accompanies `PROTOCOL.md`.

## What it does

- Generates a softened power-law quantity prior from a ranked identity roster.
- Applies explicit manual multipliers and active-amount bounds.
- Separates active amount, stock fraction, raw stock amount, and embedded carrier.
- Produces deterministic SHA-256 target hashes.
- Diffs a target formula against a confirmed physical bottle ledger.
- Audits substitution maps for one-stock-to-many-target compression.

## What it does not do

- Identify GC peaks.
- Infer exact proprietary percentages.
- Predict sensory similarity.
- Approve skin safety.
- Replace a trained perfumer, analytical chemist, or sensory panel.

## Run the tests

```bash
python -m pytest -q tests/test_recon.py
```

## Build a target prior

```bash
python src/recon.py build \
  --roster templates/roster.csv \
  --output target_formula.csv \
  --total-active 780 \
  --exponent 0.70
```

## Hash a ledger

```bash
python src/recon.py hash --csv target_formula.csv
```

## Diff target against bottle

```bash
python src/recon.py diff \
  --target target_formula.csv \
  --bottle templates/bottle.csv
```

## Audit compression in substitution mappings

```bash
python src/recon.py compression \
  --mapping templates/substitution_mapping.csv
```

## Important

The core CLI uses the Python standard library. The advanced workflow described in `PROTOCOL.md` can additionally use NumPy, pandas, SciPy, scikit-learn, NetworkX, Pydantic, RDKit, chromatography software, and laboratory instrumentation.
