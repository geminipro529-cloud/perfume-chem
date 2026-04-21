# Opus V — Data Acquisition Plan

**Date:** 2025-07-25  
**Status:** All 5 parallel research agents returned — NO hard compositional data found online  
**Conclusion:** Physical product access is the only reliable path to confirmed molecular data  

---

## Research Summary

| Research Vector | Result |
|----------------|--------|
| EU allergen box data (online) | Not published by any retailer or cosmetics database |
| Clone house formulas/SDS | No Opus V clones found; all clone sites blocked automated search |
| Cavallier cross-reference allergens | Brand sites (Zegna, Dior, LV) all returned 403/500 errors |
| Best-documented iris reference | Après l'Ondée ranked #1 but no complete verified GC-MS exists online |
| Perfumer palette (Firmenich captives) | Confirmed: Hedione, Habanolide, Alpha Irone, Clearwood, Ambrox Super |

---

## 4 Actionable Steps (Ranked by Value)

### 1. Buy Opus V Sample + Photograph Box Allergen List (~$15–25)
- EU 1223/2009 mandates 26-allergen disclosure on packaging
- This is what cracked DHI open (8 confirmed allergens → Bayesian RE → 83.5 score)
- Sources: Amouage.com official samples, Luckyscent, r/fragranceswap decants
- **NEED THE OUTER CARTON**, not just juice

### 2. Buy Zegna Florentine Iris Sample (~$10–15)
- Cavallier's iris soliflore, made 2012 (one year after Opus V)
- Same perfumer, same Firmenich captive access, same iris philosophy
- NO oud layer obscuring the iris → allergen list exposes his iris palette directly
- Compare allergen overlap with Opus V = the iris molecules
- Sources: eBay, FragranceNet, discounters (discontinued, findable cheap)

### 3. Google Scholar: Orris Butter GC-MS (Free)
- Search: `"Iris pallida" OR "orris butter" OR "orris concrete" GC-MS composition`
- Target: irone isomer ratios (cis-α vs cis-γ vs trans-α), myristic acid %, carotol content
- This gives the RAW MATERIAL fingerprint Cavallier was reconstructing synthetically

### 4. Contact Amouage Customer Service (Free)
- Email: customerservice@amouage.com
- Request: "Full allergen list per EU 1223/2009 Annex III for Opus V EDP"
- EU consumer right to know — they are legally required to provide this

---

## What Allergen Data Enables

With 8–12 allergen presence/absence confirmations, feed into `engine/reverse_engineer.py`:

| Allergen | What It Confirms |
|----------|-----------------|
| AIMI | Powdery dimension real vs pure irone |
| Coumarin | Tonka-powdery base layer |
| Linalool | Hedione presence + floral layer |
| Benzyl Salicylate | Diffusion architecture |
| Eugenol | Clove/spice in oud layer |
| Hydroxycitronellal | Muguet-cosmetic layer (would suggest more cosmetic iris) |
| Geraniol | Rose character confirmation |
| Citronellol | Rose/geranium layer |
| Limonene | Citrus top or EO presence |
| Benzyl Benzoate | Balsamic fixative |

**Expected accuracy jump:** 40–55% → 65–80% (same method that worked for DHI)

---

## Current State

- **24-material accord** in `Opus_V_Grand_Iris_Orris_Accord.md` — best guess-forward reconstruction
- **Alpha Irone (10%)** — pending restock; mix 23 materials first
- **Myristic Acid** — purchasable; included in accord
- **Hexyl Salicylate** — substituting for OOS Benzyl Salicylate

## Key Cross-Reference: Zegna Florentine Iris (2012)

Cavallier's ONLY iris soliflore. Made at Firmenich with same captive access as Opus V.
Allergen list from this bottle + Opus V allergen list = triangulated iris palette.
The molecules that appear in BOTH = Cavallier's iris core.
The molecules in Opus V but NOT Florentine Iris = the oud/leather/dark layers.
