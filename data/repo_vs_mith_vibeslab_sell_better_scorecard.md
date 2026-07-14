# Repo Product vs MITH / Vibeslab Sell-Better Scorecard

**Date:** 2026-05-25  
**Scope screened:** `formulas/`, `formulas/collections/`, `formulas/mass-market/`, `formulas/complete/`, competitor interpretation files, Thailand market docs, and the saved competitor-analysis stack.  
**Meaning of "sell better":** stronger likely Thai **retail product pull** in a matched lane, not total company revenue. For Vibeslab specifically, this does **not** include their B2B scent-branding moat.

---

## 1. What I screened across the project

I looked across the whole formula tree, but I did **not** treat every file as a launch candidate. I filtered the repo into:

- **Commercially framed collections with explicit market intent**
  - `formulas/collections/Thai_True_Mass_Market_Eighteen_2026-05-02.md`
  - `formulas/collections/Mass_Market_Thailand_Eighteen_2026-05-02.md`
  - `formulas/collections/Premium_Mass_4000_THB_Universal_Eighteen_2026-05-02.md`
- **Mass-market single-file tiers**
  - `formulas/mass-market/*.md`
- **Standalone prestige / complete builds**
  - `formulas/complete/*.md`
- **Bench, prep, refill, top-up, and reverse-engineering files**
  - screened for context, excluded from final shortlist unless they already behave like a marketable hero SKU

Practical result: the most defensible sell-better candidates come from the three scored collections above. The repo contains many high-craft niche and bench files, but most are not as commercially aligned with current MITH/Vibeslab retail competition as the market-shaped collections are.

---

## 2. Evidence and scoring basis

### Repo-backed scoring inputs
- Formula engine scores from:
  - `_thai_true_mass_market_18_scored.json`
  - `_mass_market_thailand_18_scored.json`
  - `_premium_mass_4000_universal_18_scored.json`
- Thailand retail demand and family-volume logic from:
  - `data/thai_market_sales_2500_15000_thb.md`
  - `docs/thailand_mass_market_perfumes_2000_20000.md`
- Competitor asymmetry and whitespace from:
  - `data/competitor_analysis_mith_vs_vibeslab.md`
  - `data/competitor_brief.md`
  - `scripts/competitor_analysis.py`

### Literature-backed interpretation layer

The scores are interpreted through the literature frames already established in the repo:

- **Masstige / accessible luxury**
  - premium-but-attainable products can scale, but breadth without distinction erodes symbolic value
- **Choice overload**
  - tighter hero SKU logic can outperform sprawling assortments when shoppers face too much choice
- **Sensory marketing / servicescape**
  - scent concepts can command premium power, especially in service environments; this favors Vibeslab structurally
- **Premiumness / rarity**
  - coherent codes and credible distinctiveness outperform empty exclusivity theater

### How to read the scores

- **90-100** = strong sell-better candidate in a matched Thai lane
- **80-89** = likely to outsell if launched with competent packaging/channel execution
- **70-79** = competitive, but needs cleaner launch discipline or lane selection
- **<70** = not a first-wave commercial attack candidate

---

## 3. Scoring method

Each candidate was judged on five dimensions:

1. **Thai demand fit**
   - based on family/sub-family strength in `data/thai_market_sales_2500_15000_thb.md`
2. **Repo formula strength**
   - anchored to `geometric_total`, plus performance/sillage/longevity logic from the scorer
3. **Launch readiness**
   - penalized for IFRA violations, unknown materials, and obvious readiness issues
4. **Competitor gap exploit**
   - whether the product hits a lane where MITH or Vibeslab are weak, absent, or over-positioned
5. **Literature alignment**
   - whether the product fits accessible-premium logic, focused hero-SKU logic, or scarcity/coherence logic

---

## 4. Shortlist — products from this repo that may sell better than theirs

| Candidate | Source | Family / lane | Closest competitor targets | Engine geo | Readiness note | Sell-better vs MITH | Sell-better vs Vibeslab | Why it may sell better |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | --- |
| **Bangkok Compass** | `Mass_Market_Thailand_Eighteen` | Aromatic woody / blue masculine | MITH `Legend`, `Blue Wood`; Vibeslab `Money` shelf-spend | 66.4 | Cleanest top-tier candidate, no scorer unknowns or IFRA violations | **91** | **88** | Thai male blue-woody is Tier-1 volume; focused hero logic beats MITH sprawl and Vibeslab's niche-male framing |
| **Makrut Tropic** | `Mass_Market_Thailand_Eighteen` | Citrus / Thai fresh | MITH `Thai Pomelo`, `Lemon Ice Tea`; Vibeslab `Grand Hotel Ginza`, `Swim` | 64.1 (aug) | Clean candidate, no scorer unknowns or IFRA violations | **89** | **86** | Strong climate fit + Thai cultural clarity + easier instant understanding than Vibeslab's more abstract freshness |
| **Mango Mademoiselle** | `Mass_Market_Thailand_Eighteen` | Fruity chypre feminine | MITH women's easy florals; Vibeslab lacks a mainstream-feminine hero | 61.7 (aug) | One IFRA violation to resolve before launch | **81** | **87** | Fruity chypre is a Thai women's powerhouse category and Vibeslab leaves this lane mostly open |
| **Thai Oud** | `Thai_True_Mass_Market_Eighteen` | Mid-mass oud amber masculine | MITH `Heritage Oud`, `Royal Oud`; Vibeslab `Oud Elevator` | 61.5 (aug) | No scorer unknowns, no IFRA violation in scored output | **82** | **78** | Thai-accessible oud has direct male volume logic and can outpull higher-concept oud if priced correctly |
| **Royal Tonka** | `Thai_True_Mass_Market_Eighteen` | Sweet fougere masculine | MITH weak in clear sweet-fougere hero lane; Vibeslab lacks this lane | 61.7 (aug) | One IFRA violation to clean up | **80** | **84** | Sweet fougere is a strong male-commercial family and Vibeslab leaves it structurally open |
| **Bai Toey** | `Mass_Market_Thailand_Eighteen` | Green / Thai pandan fresh | MITH OFD-style Thai concepts; Vibeslab `Afternoon Tea`, `Grand Hotel Ginza` | 63.2 | Clean candidate, no scorer unknowns or IFRA violations | **79** | **83** | Strong local identity plus freshness; more legible and culturally anchored than many premium-green concepts |
| **Aromatic Barbershop Blue** | `Premium_Mass_4000_THB_Universal_Eighteen` | Premium aromatic fougere masculine | MITH `Legend` cluster; Vibeslab has no dominant barbershop-blue offer | 60.4 | Clean candidate, no scorer unknowns or IFRA violations | **82** | **78** | A focused masculine hero in a proven family can sell harder than a concept-first niche bottle |
| **Cobalt Cedar Air** | `Premium_Mass_4000_THB_Universal_Eighteen` | Premium aromatic woody masculine | MITH `Legend`, `Blue Wood`; Vibeslab `Money`, `New Car` attention share | 59.7 | Clean candidate, no scorer unknowns or IFRA violations | **83** | **79** | Upper-mass blue woody remains a larger unit lane than Vibeslab's concept woods |
| **Dark Tonka Tobacco** | `Premium_Mass_4000_THB_Universal_Eighteen` | Tobacco tonka amber | MITH oud/amber evening cluster; Vibeslab `Burning Jazz Bar` | 60.1 | Clean candidate, no scorer unknowns or IFRA violations | **77** | **81** | Can challenge Vibeslab's concept tobacco with a more wearable, higher-repeat masculine amber |
| **Green Patchouli Cologne** | `Premium_Mass_4000_THB_Universal_Eighteen` | Citrus patchouli chypre | MITH tea/woody premium edge; Vibeslab `Aged Oakmoss`, `Pencil` | 60.2 | Clean candidate, no scorer unknowns or IFRA violations | **76** | **74** | Strong prestige-office lane, but narrower volume than blue woody, citrus, or fruity-chypre leaders |
| **Rose Cassis Chypre** | `Premium_Mass_4000_THB_Universal_Eighteen` | Fruity rose chypre feminine | MITH female floral/gourmand line; Vibeslab no strong mainstream feminine bestseller | 58.7 | Clean candidate, no scorer unknowns or IFRA violations | **78** | **84** | A high-probability Thai female seller family that Vibeslab currently under-serves |
| **Lemongrass Cool** | `Mass_Market_Thailand_Eighteen` | Aromatic fougere with Thai lemongrass | MITH male aromatic line; Vibeslab lacks this mass-readable lane | 60.9 | One IFRA violation to resolve | **78** | **80** | Strong local freshness story, but slightly less universal than Bangkok Compass |

---

## 5. Highest-conviction winners by competitor

### Best products to beat MITH on retail pull

1. **Bangkok Compass** — `91`
   - Best direct attack on MITH's male woody/aromatic business
   - Strongest whole-project commercial score in the screened set
2. **Makrut Tropic** — `89`
   - Better climate/cultural freshness story than MITH's lighter Thai concept products
3. **Cobalt Cedar Air** — `83`
   - Cleaner premium-mass masculine hero than much of MITH's broad woody spread
4. **Thai Oud** — `82`
   - Better chance to win male Thai-accessible oud volume if price-disciplined
5. **Aromatic Barbershop Blue** — `82`
   - Strong blue/fougere crossover with better hero concentration than MITH's assortment logic

### Best products to beat Vibeslab on retail pull

1. **Bangkok Compass** — `88`
   - Likely higher unit velocity than Vibeslab's concept-led masculine scents
2. **Mango Mademoiselle** — `87`
   - Vibeslab leaves mainstream-feminine Thai bestseller territory under-defended
3. **Makrut Tropic** — `86`
   - Easier immediate understanding, better heat fit, stronger local anchor than abstract hotel freshness
4. **Royal Tonka** — `84`
   - Vibeslab has no clear sweet-fougere hero
5. **Rose Cassis Chypre** — `84`
   - Another women's lane Vibeslab does not own

---

## 6. What the whole-project screen says about gaps

### Gaps in MITH's current product logic

- Too much breadth relative to hero-SKU sharpness
- Weak clear B2B / scent-system moat
- No dominant repo-evident claim over Thai male blue-woody or disciplined premium-fougere hero architecture
- Thai concept products exist, but some are lighter novelty cues rather than strong category-killers

**Repo products that exploit this best**
- `Bangkok Compass`
- `Makrut Tropic`
- `Cobalt Cedar Air`
- `Aromatic Barbershop Blue`

### Gaps in Vibeslab's current product logic

- Weak mainstream-feminine bestseller coverage
- Narrow masculine mass-appeal blue/fougere coverage
- Strong concept power, but less immediate everyday-wear conversion in some lanes
- Retail DTC assortment is curated, but leaves bigger Thai-volume families partially open

**Repo products that exploit this best**
- `Mango Mademoiselle`
- `Rose Cassis Chypre`
- `Bangkok Compass`
- `Royal Tonka`
- `Makrut Tropic`

---

## 7. First-wave productization recommendation

If the goal is to launch the minimum set of products from this repo that has the best chance to sell harder than current MITH/Vibeslab retail offers, the first wave should be:

1. **Bangkok Compass**
2. **Makrut Tropic**
3. **Mango Mademoiselle** after IFRA cleanup
4. **Thai Oud**
5. **Cobalt Cedar Air**
6. **Royal Tonka** after IFRA cleanup

This gives:

- 2 masculine high-volume blue/fresh anchors
- 1 culturally sharp Thai-fresh hero
- 1 female top-volume fruity-chypre
- 1 male oud-access hero
- 1 sweet-fougere male closer

That basket is stronger commercially than leading with the repo's more niche iris, luxury, or reverse-engineering work.

---

## 8. Important caveat

This is a **product-level retail outperformance score**, not a complete business-model score.

- A formula with a high `sell-better vs Vibeslab` score can still lose against Vibeslab's **B2B service moat**
- A formula with a high `sell-better vs MITH` score can still lose if MITH overwhelms the lane through **distribution and mall reach**

So the correct reading is:

- **Can this product pull harder than theirs in Thai retail if launched well?**
  - That is what these scores answer.
- **Can this product alone beat their whole business?**
  - That is a different question.

