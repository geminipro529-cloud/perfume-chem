# Scientific constraints

> Moved out of `AGENTS.md` unchanged on 2026-10-08 so every session loads less; `AGENTS.md` links here. These are working notes and historical diagnostics, not universal policy: where they disagree with the rules in `AGENTS.md` (Rules 0-7 and the reviewed knowledge boundary), those rules win.

## Scientific Constraints (codified from system reference docs)

### Headspace OAV calculation
```
p_i = γ_i × x_i × P_i*   (Modified Raoult)
OAV = p_i / P_atm × 1e6 / ODT_ppb
```
- `x_i` = mole fraction (must convert from weight via `n_i = w_i / MW_i`)
- `P_i*` = pure-component VP (Pa at 25°C)
- `γ_i` = activity coefficient in ethanol matrix (NEVER silently 1.0)

### Activity coefficient ranges (ethanol matrix, ~20°C)
| Class | γ |
|---|---|
| Non-polar hydrocarbons (limonene, pinenes, terpenes) | 3.0–3.2 |
| Polar esters (benzyl acetate, linalyl acetate) | 1.5–2.0 |
| Mid-polarity sesquiterpenes/alcohols | 1.2–1.8 |
| H-bond donors/acceptors (vanillin, coumarin, musks) | 0.5–0.7 |
| Macrocyclic musks | 0.4–0.6 |

### Note tier from VP
| Tier | VP range |
|---|---|
| Top | > 2 Pa (bergamot 40, petitgrain 6, linalool 20, limonene 200) |
| Heart | 0.1–2 Pa (geraniol 4*, hedione 0.09*) |
| Base | < 0.1 Pa (vetiver 0.04, iso e super 0.15*, musks ≤ 0.02) |
*Note: pipeline uses ingredient_intelligence profiles for tier, not these thresholds. These are reference ranges for formulation thinking.

### Psychophysics
- Weber-Fechner: `I = k × log(C / ODT)`
- Stevens Power Law: `I = k × C^n` (n typically 0.2–0.6)
- OAV > 1 = perceptible. OAV < 0.1 = dormant filler.
- Humans can discriminate at most 3–4 components in a mixture (Livermore & Laing)
- Adaptation: citrus adapts ~5 min, florals ~15–20 min, musks ~45–60 min

### Clausius-Clapeyron temperature correction
`ln(P2/P1) = (ΔHvap/R) × (1/T1 - 1/T2)` where ΔHvap ≈ 60 kJ/mol (working approximation). 10°C rise → VP × ~1.9. Bangkok (35°C) vs Paris (22°C): VP × ~2.8.

### EU Allergen labeling (Reg 1223/2009 Annex III)
26 mandatory allergens must be declared if exceeding 0.001% in leave-on or 0.010% in rinse-off products. SCCS Opinion SCCS/1525/21 proposes expansion to 82+ allergens as of 2026–2027.
