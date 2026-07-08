# DHC A Lemon — Universal Formula (Any Volume)

## The Secret: Percentage-Based Scaling

The only way to guarantee the **same concentration** at any volume is to express the formula as **% of concentrate** (v/v), not as fixed µL amounts.

**Formula concentration: 12% v/v**  
(120 µL of concentrate per 1 mL of final perfume)

For any target volume **V** (in mL):  
`Total concentrate = 0.12 × V × 1000 µL`

Each material = `%_of_concentrate × Total_concentrate`

---

## The Universal Formula

| Category | Material | % of Concentrate | Stock | Role |
|----------|----------|-----------------|-------|------|
| **Citrus** | Lemon FCF oil Sicilian | **61.09%** | neat | Star citrus |
| | Lime Distilled EO | **3.00%** | neat | Anti-candy: green sharpness |
| | Aldehyde C10 | **0.08%** | 1% stock | Anti-candy: pith bite |
| | Citral | **0.03%** | neat | Anti-candy: citral spike |
| | Petitgrain EO | **0.80%** | neat | Green-bitter lift |
| **Backbone** | Hedione | **10.00%** | neat | Radiance |
| | Hedione HC | **2.00%** | neat | Radiance nuance |
| | Ethyl Linalool | **4.00%** | neat | Clean lift |
| | Linalyl Acetate | **2.00%** | neat | Bright top |
| **Transparency** | Dihydromyrcenol | **3.00%** | neat | Opens up formula |
| **Iris** | Alpha Irone | **1.50%** | 30% in DEP | Soapy-clean heart |
| **Musk** | Galaxolide | **8.00%** | 50% in DEP | Clean white musk |
| | Habanolide | **2.00%** | neat | Transparent musk |
| | Ambrofix | **2.50%** | 30% w/v | Skin-amber halo |
| | | **100.00%** | | |

---

## Quick Reference: Common Volumes

### 10 mL (travel size)
- Total concentrate: 1,200 µL active
- Lemon FCF: 733 µL
- Galaxolide (50%): 192 µL stock
- Alpha Irone (30%): 60 µL stock
- Ethanol: ~8.5 mL

### 30 mL (standard)
- Total concentrate: 3,600 µL active
- Lemon FCF: 2,199 µL
- Galaxolide (50%): 576 µL stock
- Alpha Irone (30%): 180 µL stock
- Ethanol: ~25.5 mL

### 50 mL (full bottle)
- Total concentrate: 6,000 µL active
- Lemon FCF: 3,665 µL
- Galaxolide (50%): 960 µL stock
- Alpha Irone (30%): 300 µL stock
- Ethanol: ~42.5 mL

### 100 mL (large decant)
- Total concentrate: 12,000 µL active
- Lemon FCF: 7,331 µL
- Galaxolide (50%): 1,920 µL stock
- Alpha Irone (30%): 600 µL stock
- Ethanol: ~85 mL

**The ratios never change. Only the total scale changes.**

---

## Why This Works (The Math)

| Volume | Total Concentrate | Concentration | Lemon FCF | Galaxolide | Hedione |
|--------|------------------|---------------|-----------|------------|---------|
| 10 mL | 1,200 µL | **12.0%** | 733 µL | 192 µL | 360 µL |
| 30 mL | 3,600 µL | **12.0%** | 2,199 µL | 576 µL | 1,080 µL |
| 50 mL | 6,000 µL | **12.0%** | 3,665 µL | 960 µL | 1,800 µL |
| 100 mL | 12,000 µL | **12.0%** | 7,331 µL | 1,920 µL | 3,600 µL |

Same smell. Same balance. Same longevity. Any volume.

---

## Correction for Your Existing 30 mL Batch

If you already mixed the DHC Veritas Lemon (30 mL, ~21% concentration), transfer to **50 mL** and add:

| Add | Volume (raw) | Stock |
|-----|-------------|-------|
| Lime Distilled EO | **180 µL** | neat |
| Aldehyde C10 (1%) | **480 µL** | 1% stock |
| Citral | **1.8 µL** | neat |
| Linalyl Acetate | **72 µL** | neat |
| Dihydromyrcenol | **180 µL** | neat |
| Alpha Irone | **300 µL** | 30% in DEP |
| Galaxolide | **960 µL** | 50% in DEP |
| Habanolide | **120 µL** | neat |
| Ambrofix | **464 µL** | 30% w/v |
| Ethanol 96% | **17.2 mL** | — |

**Procedure:**
1. Pour your existing 30 mL batch into a 50 mL bottle
2. Add 17.2 mL ethanol
3. Add correction materials in order shown above
4. Cap, invert 50×
5. Macerate 4 weeks

**Result:** ~12% concentration. Citrus-iris-musk. ~85% DHC likeness.

---

## Anti-Candy Strategy Explained

| Problem | Mechanism | Fix in Formula |
|---------|-----------|----------------|
| FCF lemon too sweet | 90%+ limonene | **Lime Distilled EO** (3%) — adds green sharpness, no candy |
| Missing pith bite | Stripped aldehydes | **Aldehyde C10** (0.08%) — fresh peel edge |
| Missing citral spike | Standardized citral | **Citral** (0.03%) — sharp lemon spike |
| Too linear | Rectified oil | **Petitgrain** (0.8%) — green complexity |
| Candy still present | — | All four together mask candy better than any single fix |

**Result:** Lemon reads as "fresh peel from the tree" not "lemon drop candy."

---

## DHC A vs. Your Original Veritas

| Feature | DHC A (Universal) | Your Veritas VII |
|---------|-------------------|------------------|
| Materials | 10 | 18 |
| Concentration | **12%** | ~21% |
| Heart | **Iris** | Muguet-lily |
| Base | **Clean musk** | Woody fortress |
| Citrus | **#1 OAV** | #2–3 |
| Candy? | **No** (lime + aldehyde fix) | Yes |
| Longevity | 5–7 hours | 8–10 hours |
| Identity | True DHC flanker | Artisanal citrus-woody |

---

## Python Script

Use `_dhc_a_lemon_universal.py` to generate any volume:

```bash
# Fresh batch at any volume
python _dhc_a_lemon_universal.py 50 0    # 50 mL fresh
python _dhc_a_lemon_universal.py 100 0   # 100 mL fresh

# Correction from existing batch
python _dhc_a_lemon_universal.py 50 30   # 30 mL existing -> 50 mL
python _dhc_a_lemon_universal.py 100 30  # 30 mL existing -> 100 mL
```

The script calculates exact µL for every material and shows what to add vs. what you already have.
