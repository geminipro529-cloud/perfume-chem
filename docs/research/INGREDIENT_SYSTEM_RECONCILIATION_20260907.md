# Whole ingredient-system reconciliation — 2026-09-07

Status: IN PROGRESS. This is a software/data consistency update, not a claim that
all chemical properties are measured, or that any formula is safe or released.

## Plan and ownership

1. Preserve starting bytes and Git state. Parent is sole writer and final acceptor.
   Native review lanes: stock/parser; ODT/provenance; identity/physics; generator.
   No other worktree is integrated and historical formulas remain unchanged.
2. Apply confirmed current stocks in a dated successor: Coumarin 10% w/w DPG;
   Hydroxycitronellal bottle identity (not an alias to Hydroxycitronellol);
   Geranium EO supplier Bontoux only; Vetiveryl Acetate 10% w/w DEP;
   Methyl Laitone 20% with unspecified basis/carrier. Reconcile depleted/planned
   stocks without erasing their records or inferring new stock properties.
3. Reconcile all inventory identities across registry, public ingredient profiles,
   threshold data and generated material data. Preserve source fields and explicit
   conflicts; use null/unknown where chemical or product authority is missing.
4. Remove false threshold provenance, make regeneration local/deterministic and
   import-safe, and retain all pre-existing generated records and unrelated data.
5. Add focused regression tests, compare complete coverage and preserved historical
   bytes, then run relevant integration verification. Record exact remaining gaps.

## Authority boundaries

- Entity identity and molecular mass do not establish supplied-product purity.
- Unknown carrier, basis, density, VP, ODT, lot composition and safety stay unknown.
- Supplier prose describes candidate roles; heuristic hedonic/OAV values are not
  measured liking, smell, performance, similarity, stability or release evidence.
- No formula revision, physical addition, purchase, merge, commit or push is in scope.
- Earlier receipts/overlays stay byte-identical and loadable as historical evidence.
