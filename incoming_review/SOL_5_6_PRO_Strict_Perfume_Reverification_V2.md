# SOL 5.6 Pro Strict Perfume Reverification V2

**Date:** 2026-08-02  
**Scope:** the recent from-scratch reconstruction suite plus the live YSL L’Homme, YSL La Nuit de L’Homme, Prada L’Homme, Bleu de Chanel Parfum, Amouage Reflection Man, and Dior Homme Intense builds.

## Executive decision

The previous permissive desk gates are revoked.

```text
Mass / bottle accounting:        mixed, formula-dependent
Strict OAV:                      WITHHELD
Reference headspace match:       NOT ESTABLISHED
Target-specific public GC-MS:    NOT ESTABLISHED
Coded reference sensory test:    FAILED / NOT RUN
User sensory registration:       FAIL
FINAL SOL 5.6 PRO GATE:          FAIL : REBUILD
```

A formula cannot receive a brand-likeness pass merely because its ingredients resemble a public note pyramid, its arithmetic balances, or a volatility proxy produces a plausible top-heart-base curve.

## Why the old verification was not sufficient

### 1. OAV was being asked to do a job it cannot do

A strict odor activity value is the concentration of an odorant divided by a detection threshold measured in a compatible medium and method. For fragrance-on-skin verification, the relevant quantity is preferably a time-resolved air/headspace concentration divided by a compatible air threshold:

\[
OAV_i(t)=\frac{C_{air,i}(t)}{T_{air,i}}
\]

The existing ledgers do not contain measured \(C_{air,i}(t)\), and many rows lack compatible threshold data. Liquid concentration divided by an unrelated air threshold is rejected. OAV is also not interpreted as percentage odor contribution or mixture intensity.

### 2. Formula percentage is not headspace percentage

A first-principles headspace estimate would require, at minimum:

\[
y_i(t) \approx \frac{\gamma_i(t)x_i(t)P_i^{sat}(T)}{P}
\]

followed by a time-dependent depletion and substrate-partition model. The current formulas do not provide reliable activity coefficients, exact mole fractions for every supplier base and natural, complete vapor-pressure data, or a reference-product time series. Therefore no numerical headspace similarity score is released.

### 3. Patents prove functions, not branded formulas

Patent examples can support the use of irones for orris character, diffusion/bloom strategies, evaporation-profile modelling, and particular accord-building approaches. They do not establish that a named retail perfume uses the patented example or its proportions. Patent evidence is therefore architectural evidence only.

## Formula-level final gates

| Target / build | OAV | Headspace | Sensory | Final gate | Main reason |
|---|---|---|---|---|---|
| Entire recent 30-formula scratch suite | WITHHELD | NO REFERENCE MATCH | MIXED BUILDS: FAIL; UNBUILT: NOT TESTED | **REDRAFT BEFORE FURTHER BENCHING** | Public notes and generic material-role logic cannot establish commercial formula identity. Any version already judged wrong fails; unbuilt versions remain on hold rather than receiving a desk pass. |
| YSL L’Homme parent reconstruction | WITHHELD | NOT ESTABLISHED | FAIL | **REBUILD** | The live basis mixed an 88 µL socket with a 148-150 µL overlay, had stock-strength conflicts, and drifted from the official ginger-violet leaf-basil-white pepper-woody architecture. |
| YSL L’Homme coriander-juniper version | WITHHELD | NOT ESTABLISHED | custom target only | **CUSTOM FLANKER, NOT PARENT PASS** | Coriander-juniper can be a deliberate flanker identity, but it cannot pass an exact-parent gate by design. |
| YSL La Nuit de L’Homme | WITHHELD | NOT ESTABLISHED | FAIL | **REBUILD** | The cardamom-led opening and lavender/pepper/cedar transition were not locked against a reference; alternate spices or blue-chamomile emphasis change the target class. |
| Prada L’Homme | WITHHELD | NOT ESTABLISHED | FAIL | **REBUILD** | Previous mapping included unresolved stock identities and an invalid Hydroxycitronellal/Hydroxycitronellol substitution path; the result became a generic clean musk-ionone chassis rather than the precise neroli-iris-pepper-geranium-patchouli balance. |
| Bleu de Chanel Parfum | WITHHELD | NOT ESTABLISHED | FAIL | **REBUILD** | The existing reconstruction contains an unnecessary 155.024 µL spice block and an over-compressed wood/sandalwood mass. The official target is an aromatic, intensely woody perfume with powerful freshness and a New Caledonian sandalwood trail. |
| Amouage Reflection Man | WITHHELD | NOT ESTABLISHED | FAIL | **REBUILD** | Large irone, ionone, Javanol, cedar, patchouli, rosemary and ylang overages cannot be removed add-only. Exact additive convergence would require an absurd dilution, so the current bottle is structurally unrecoverable as a close reference match. |
| Dior Homme Intense | WITHHELD | NOT ESTABLISHED | FAIL if Wave 2 matured without correction | **REBUILD; NO WAVE 3** | The target requires an integrated iris-ambrette-pear-liquor-silk-talc-amber-cedar object. More traces cannot repair a compressed base after a matured correction fails to register. |

## Official recognizer locks used in the gate

- **YSL L’Homme:** ozone/ginger/cedrat opening; violet leaf, basil and white pepper heart; cedar, sandalwood, vetiver and tonka base.
- **YSL La Nuit de L’Homme:** bergamot and cardamom opening; lavender, black pepper and cedar heart; vetiver and tonka base.
- **Prada L’Homme:** neroli, violet, geranium, iris, pepper, amber, cedar and patchouli, with Prada Beauty specifically foregrounding black pepper, geranium and patchouli.
- **Bleu de Chanel Parfum:** powerful freshness into an intense aromatic-woody body and New Caledonian sandalwood trail.
- **Reflection Man:** rosemary, red pepper berries and bitter-orange leaves; neroli, orris, jasmine and ylang; vetiver, patchouli, sandalwood and cedar.
- **Dior Homme Intense:** iris, amber and precious woods, with ambrette facets described as musky/fruity between pear liqueur and silk talc, plus Virginia cedar.

## Replacement verification protocol

### Gate A: exact target lock

Record product name, concentration, bottle code, region, purchase date, reformulation era, storage history and reference-bottle fill level. A reconstruction cannot target “the perfume” without identifying which version of the perfume.

### Gate B: exact stock lock

For every material record supplier, product name, lot, dilution, diluent, weight/volume basis, density, assay or GC range, and date opened. Opaque bases and naturals remain product-basis rows unless their composition is analytically known.

### Gate C: 5 mL pilot, not 30 mL

All clean rebuilds begin as 5.000 mL pilots. No full bottle is made until the candidate passes two successive blinded comparisons.

### Gate D: matched analytical headspace

Candidate and authenticated reference are sampled by the same method, substrate, loading, temperature, equilibration time, SPME fibre, extraction time, desorption conditions and instrument method. Minimum sampling windows:

```text
0-5 min
30 min
2 h
8 h
24 h
```

Report normalized peak areas, internal-standard-corrected response where standards exist, and confidence intervals across replicates. A formula-to-reference temporal distance is calculated only from compounds detected by the same method in both samples.

### Gate E: strict OAV

OAV is calculated only where both the measured concentration and a method/matrix-compatible threshold exist. Missing values remain `NA`, not guessed. OAV is used as a detectability screen, never as a percentage-contribution model.

### Gate F: coded sensory comparison

Use randomized labels and fresh blotters. Evaluate at 5 min, 30 min, 2 h, 8 h and 24 h. Score:

1. immediate identity recognition;
2. recognizer hierarchy;
3. top-to-heart transition;
4. texture and density;
5. negative space / transparency;
6. drydown identity;
7. off-target facets;
8. overall similarity.

A final brand-likeness pass requires the candidate to beat the prior candidate in blinded comparison and remain within a predeclared similarity tolerance to the authenticated reference. User observation overrides a desk prediction.

### Gate G: SOL 5.6 Pro final decision

```text
PASS      all critical evidence, analytical, temporal and sensory gates pass
HOLD      evidence or measurement is missing, but no hard contradiction exists
FAIL      sensory mismatch, wrong recognizer hierarchy, structural overage, or invalid stock mapping
REBUILD   FAIL caused by unremovable architecture rather than a small local deficit
```

No more than two controlled revisions are permitted after the clean pilot. A third failure triggers a new formula architecture rather than another add-only patch.

## Immediate operating rule

Stop adding materials to the existing failed scratch bottles. They remain useful as negative controls and omission-study references. Future work starts from clean 5 mL pilots, one authenticated target and one locked batch at a time.

## Literature and patent basis

### Peer-reviewed literature

1. Audouin V, Bonnet F, Vickers ZM, Reineccius GA. *Limitations in the Use of Odor Activity Values to Determine Important Odorants in Foods.* ACS Symposium Series 782, 156-171 (2001). DOI: 10.1021/bk-2001-0782.ch014.
2. Ferreira V. *Revisiting psychophysical work on the quantitative and qualitative odour properties of simple odour mixtures. Part 1: intensity and detectability.* Flavour and Fragrance Journal 27, 124-140 (2012). DOI: 10.1002/ffj.2090.
3. Ferreira V. *Part 2: qualitative aspects.* Flavour and Fragrance Journal 27, 201-215 (2012). DOI: 10.1002/ffj.2091.
4. Vuilleumier C, Flament I, Sauvegrain P. *Headspace analysis study of evaporation rate of perfume ingredients applied onto skin.* International Journal of Cosmetic Science 17, 61-76 (1995). DOI: 10.1111/j.1467-2494.1995.tb00110.x.
5. Goh A et al. *Assessing residual fragrances on skin after body washing: optimization of HS-SPME-GC-MS.* International Journal of Cosmetic Science 46, 1004-1016 (2024). DOI: 10.1111/ics.13001.

### Patent evidence used only for technical architecture

- EP0211954A1 / B1: cis-γ-irone use in perfumery and orris/violet character.
- WO2018071897A1 / US20190367837A1: high-impact bloom accords and experimental diffusion metrics.
- EP3307231A1: fragrance-profile fidelity and time-resolved headspace examples.
- EP4205058A1: temporal evaporation-profile generation using vapour pressure and time-dependent interaction coefficients.

## Final statement

The strict result is intentionally unforgiving: the current scratch formulas are not verified replicas. They are hypotheses that failed the sensory gate or never reached a defensible analytical gate. The path forward is not more tiny additions. It is clean, small-scale, reference-locked reconstruction with matched headspace and blinded sensory comparison.
