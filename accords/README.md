# Accords — Construction & Recipes

> **⚠️ RULE 0: Read [`inventory.txt`](/inventory.txt) before constructing ANY accord.** Materials, dilutions, and stock levels change. Never assume availability.

> **⚠️ RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
> Concentrations are in **ppm** (parts per million w/w in concentrate). Odor detection thresholds are **ODT** (in ppm for ethanol solution, or ppb for air). Odor Activity Value is **OAV = concentration_ppm / ODT_ppm**. Every formula dose must be convertible to ppm, every threshold check must reference ODT, and every perceptibility claim must be backed by OAV. No exceptions.

Standalone accord builds and sub-accord components. Each file is a self-contained accord recipe that can be pulled into a full formula as a unit.

---

## File naming convention

```
[accord-type]_[character-descriptor]_v[N].md
```

Examples:
- `iris_orris-butter_v1.md`
- `muguet_cosmetic-transparent_v1.md`
- `musk_lactonic-skin_v1.md`
- `wood_cedar-amber-warm_v1.md`
- `citrus_bitter-hesperidic_v1.md`

---

## Format standard

Each accord file must include:

1. **Brief** — what olfactive effect the accord creates (1–3 sentences, perfumer vocabulary)
2. **Ingredient table** — ppm active in final EDP context OR % of accord by weight, with dilution noted
3. **Function of each material** — why THIS material and not another (per copilot-instructions.md Rule 3)
4. **Usage notes** — typical dose range when dropping into a full formula, synergies, clashes
5. **Version log** — date, changes from previous version

---

## Rules (from copilot-instructions.md)

- Only single-molecule aroma chemicals and natural EOs (no FTECs, FOs, Accords, Fleuressences, Bases)
- No batch-volume (µL/mL) amounts as the primary unit — express as ppm or % of accord
- Every material must have a specific functional reason stated
- No defaults: justify every material choice against alternatives
