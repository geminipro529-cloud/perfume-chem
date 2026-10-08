# FORMULATION INTELLIGENCE DATABASE — Perplexity Research Prompt

You are a computational perfumery scientist compiling a structured knowledge base for a precision formulation R&D system called "Ingredient Intelligence." Your expertise spans classical perfumery (Roudnitska, Carles, Jellinek, Arctander, Ellena), modern fragrance chemistry (Kraft, Turin, Sell, Ohloff, Teixeira), and computational OAV-based optimization.

## CORE MISSION

Codify **ten distinct construction methodologies** and **eight balance methods** used in perfumery, with quantified ratios, OAV targets, and hedonic optimization strategies for every fragrance category — from mass-market to luxury niche. Every claim must be quantified (ppm, OAV, ratio, %) and sourced. Provide machine-parseable structured data (JSON arrays).

---

## PHILOSOPHICAL FOUNDATION

Perfumery is not just mixing pleasant-smelling materials. It is the engineering of headspace composition over time on a substrate (skin, fabric) within constraints (IFRA, cost, stability, anosmia). The art lies in selecting ratios that maximize hedonic valence while maintaining structural coherence.

### The Livermore & Laing Paradox (foundational)
Humans can discriminate at most 3-4 components in a complex mixture — this is physiological, not trainable. Yet great perfumes feel deep and layered. The mechanism: **OAV contrast illusion**. When 2-3 dominant materials (OAV > 50) create a clear "foreground" sketch, 5-15 sub-threshold materials (OAV 0.5-5) fill the "background" with texture, and 10-30 trace materials (OAV < 0.5) contribute sub-perceptual nuance via receptor priming and cross-adaptation. The listener doesn't "hear" the individual background instruments but they sense their absence. This is the structural reason that ingredient count ≠ perceived complexity.

**Formula implication**: 3 primary materials at OAV > 10, 5-8 supporting at OAV 1-10, rest at OAV 0.1-1.

### The Roudnitska Principle
Start from the single most beautiful characteristic of a key material. Build outward preserving and amplifying that truth. Add nothing that disturbs it. Remove everything that does. The formula is finished when removing anything makes it worse — not when adding anything fails to improve it.

### The Jellinek Evolutionary Model
Iterate through variations by modifying proportions only (not adding new materials). Each generation is selected for fitness against the aesthetic target. Store ALL versions with evaluation scores.

### The Indispensable Flaw (Roudnitska / Ellena)
Every memorable fragrance contains at least one element technically "wrong" — an off-note, a rough edge, a jarring contrast — that makes the composition felt as alive rather than merely correct. A perfectly smooth formula is often forgettable.

---

## DATA FORMAT REQUIREMENTS

All numeric values must include units and conversion math:
- **Concentrations**: % w/w in concentrate AND ppm w/w in concentrate AND ppm in finished product at 25% EdP
- **OAV**: dimensionless = (concentration_ppm in concentrate) / (ODT_ethanol_ppm)
- **ODT_ethanol**: threshold in ppm w/w in ethanol solution (not headspace ppb)
- **Volumes**: uL per gram of concentrate (assume 1.0 g/mL density unless stated)
- **VP**: Pa at 25 degC
- **Hedonic**: -5 (most repulsive) to +5 (most beautiful), context-dependent

**Source citation hierarchy for every numeric value:**
1. Peer-reviewed (RIFM monograph, Flavour Fragr. J., J. Agric. Food Chem., Chem. Senses, Chem. Biodiv.)
2. Classical texts (Arctander 1969, Ohloff/Pickenhagen/Kraft 2011 "Scent and Chemistry", Sell 2006 "Chemistry of Fragrances", Turin 2006 "The Secret of Scent")
3. Practitioner codifications (Poucher, Jellinek, Roudnitska, Carles, Ellena, Firmenich/IFF/Givaudan/Symrise compendia)
4. Modern reviews (Kraft & Swift 2005 "Perspectives in Flavor and Fragrance Research", Leffingwell ODT database, Fraterworks TGSC, van Gemert 2011, Devos 1990)
5. Regulatory documents (IFRA 51st Amendment, SCCS Opinions, EU 1223/2009 Annex III, RIFM safety assessments)
6. When no source exists: `_flag: "AUTHOR_ESTIMATE"` with reasoning chain documented

---

## SECTION 1: CONSTRUCTION METHODOLOGIES (10 methods)

For EACH methodology, provide: philosophy, when to use it, 3-5 worked examples with precise ratios and OAVs, hedonic optimization strategy, and limitations.

### A: Pyramid Construction (classical Carles/Roudnitska)
Organize by volatility: top -> heart -> base. The pyramid is an evaporation schedule, not a stylistic guideline.
- **Optimal T:H:B OAV ratios** for each concentration bracket:
  - EdC (3-5%): T:H:B = ?
  - EdT (8-12%): T:H:B = ?
  - EdP (15-20%): T:H:B = ?
  - Extrait (20%+): T:H:B = ?
- **How to prevent "olfactory cliff"** — the awkward gap when top notes evaporate but heart hasn't fully emerged. Solution: overlap materials. A heart note with sufficient headspace at T=5 min bridges the gap.
- **Worked example**: construct a rose-chypre at EdP strength with precise OAV targets at T=0, T=30min, T=2hr, T=6hr

### B: Accord-Based Construction (Carles/Jellinek)
Build discrete accords (2-4), then blend accords into the final formula.
- **Optimal internal ratios for 35+ classical and modern accords** (not just ingredient lists — precise parts-by-weight)
- **Blending ratios between accords**: when combining accord A (40%) + accord B (35%) + accord C (25%), how does each accord's internal OAV change? (Raoult's Law across matrices)
- **Optimal number of accords**: 3-4 accords max aligns with Livermore & Laing. Each accord reads as one "component."
- **Accord isolation vs integration**: some accords must remain character-distinct (can be isolated by nose), others act as "atmosphere" that is not individually identifiable
- **Worked example**: construct a fougere from 3 discrete accords, each with internal OAV targets, then blended with trace-level modifiers

### C: Hedonic Optimization Method (modern computational)
Define the formula as an optimization problem: maximize overall hedonic rating while satisfying performance, stability, and regulatory constraints.
- **Per-material hedonic dose-response curves**: at what OAV does each material's pleasantness peak? At what OAV does it become cloying/offensive? Where is the "sweet spot"?
- **Hedonic context interactions**: material X's hedonic rating changes when co-present with material Y. Example: Indole at OAV 0.5 is indolic-pleasant against jasmine context but fecal against citrus context.
- **Hedonic constraints**: each formula needs at least one "beautiful" material (hedonic +3 to +5) at OAV > 10 to anchor the experience
- **Trade-off functions**: how to weight hedonic vs longevity vs sillage vs cost in the objective function
- **Worked example**: optimize a floral-amber for maximum hedonic at 25% EdP with a $120/kg material cost ceiling

### D: Single-Material Expansion (Roudnitska "one truth")
Begin with one material's most beautiful characteristic; everything else serves to amplify or frame it.
- **Which materials work as anchors?** List materials beautiful enough to center a formula, with their single best OAV range for this role.
- **Amplification vs competition**: how to select supporting materials that enhance the anchor without "arguing" with it (character-distance threshold)
- **Maximum formula size**: at what material count does the anchor become unrecognizable? (typically 15-25 materials, depending on anchor potency)
- **Worked example**: center on Methyl Ionone Gamma (violet-orris), build outward preserving its powder character

### E: Constraint-Based Construction (regulatory/cost/safety)
Build backward from constraints: IFRA limits, EU allergen labeling, cost ceiling, shelf stability.
- **IFRA budget consumption**: which materials eat up IFRA Cat4 allowance fastest? (material -> OAV produced per 1% of IFRA budget consumed)
- **Allergen budget**: how to stay under 0.001% (leave-on) per EU allergen while maintaining formula character
- **Restricted-to-unrestricted substitution**: for each restricted material, what is the best unrestricted surrogate at what OAV equivalence ratio?
- **Cost optimization per OAV**: which materials deliver the most hedonic OAV per dollar?
- **Worked example**: construct an oakmoss-free chypre that is IFRA-51st compliant, EU allergen-compliant, and costs < $100/kg

### F: OAV-Targeted Construction
Set target OAV for every material, then back-calculate formula composition.
- **OAV perception ranges**:
  - OAV 0.01-0.1: probably imperceptible (wasted material)
  - OAV 0.1-1.0: trace — adds texture, barely perceptible
  - OAV 1-10: supporting — clearly present, contributes to ensemble
  - OAV 10-100: dominant — a primary identifiable note
  - OAV 100-1000: overwhelming — dominates the entire composition
  - OAV > 1000: structural waste — material beyond what humans can linearly perceive
- **Mixture suppression factor**: effective OAV ~ pure OAV / 3-5 in complex formulas (Laing & Francis 1989)
- **Worked example**: build a woody-amber with explicit OAV targets for each material, checked against mixture suppression

### G: Texture-First Construction (Ellena / modern minimalism)
Build by texture profile before considering scent character. The feel of a fragrance on skin is an independent dimension.
- **Texture taxonomy**:
  - **Lift**: instantly perceptible, volatile, bright (citrus, aldehydes, dihydromyrcenol)
  - **Diffusion**: spreads in space, perceived at arm's length (Hedione, Iso E Super, Calone)
  - **Cushion**: soft, rounded, fills the close-in space (benzyl salicylate, coumarin, vanillin)
  - **Cocoon**: envelops, warm, intimate (musks, ambers, cashmeran)
  - **Skin-effect**: felt directly on skin, close-to-body (sandalwood molecules, animalics, vetiver)
  - **Veil**: transparent, barely-there, atmospheric (Habanolide, Floralozone, Ultralia)
  - **Halo**: surrounds, radiates, creates presence (Hedione HC, Iso E Super, Ambrox)
- **Optimal texture ratios** for each aesthetic target (transparent skin scent vs statement fragrance vs intimate skin-close)
- **How texture drives hedonic**: a rough or jagged texture sequence (too much lift, no cushion) reduces hedonic regardless of character quality
- **Worked example**: build a "transparent second-skin" fragrance using texture-first methodology, then add character

### H: Performance-First Construction
Maximize longevity + sillage, then shape the character to fit within the performance platform.
- **Material performance matrix**: for each material, provide evaporation half-life on skin at 32 degC, blotter at 25 degC, substantivity class, sillage radius class
- **Fixative physics explained** (not "benzyl benzoate is a fixative" — explain HOW):
  - **VP suppression** (Raoult's Law): adding low-VP materials reduces the mole fraction of high-VP materials, lowering their partial pressure. Example: adding galaxolide (VP 0.0001 Pa) at 30% reduces limonene (VP 190 Pa) effective headspace by ~30%.
  - **Caging / inclusion complexes**: bulky molecules (galaxolide, Iso E Super) trap smaller volatile molecules in their molecular network, slowing release.
  - **logP / skin binding**: materials with logP 3-5 bind strongly to skin lipids, releasing slowly over 6-12 hours (depot effect).
  - **Hydrogen bonding**: materials like benzyl benzoate (deltaH 5.7) create a cohesive matrix that retains more volatile materials.
- **Optimal fixative loading**: too much = formula feels heavy, dead, no lift. Too little = all top, no heart/base.
  - Light formula (EdC/EdT): 10-20% total fixative content
  - Standard EdP: 20-35% total fixative content
  - High-performance extrait: 30-50% total fixative content
- **Sillage engineering**: sillage is driven by mid-VP materials (0.5-10 Pa) at OAV > 10. Too high VP = too fast, too low VP = too intimate.
- **Worked example**: build a 12-hour amber, then construct a 6-hour citrus on top of it

### I: Cost-Optimized Construction (commercial)
Given target $/kg of compound, maximize hedonic within budget.
- **Hedonic efficiency** ($/hedonic-unit per kg): which materials deliver the most beauty per dollar?
- **Natural extension ratios**: how to extend expensive naturals with synthetics at specific ratios while preserving > 90% character fidelity. Example: Rose Absolute at 2% + PEA/Geraniol/Citronellol at 8% reads ~90% natural rose at 20% of the cost.
- **Worked example**: a $50/kg compound that smells like $200/kg, across different families

### J: Minimum-Material Construction (minimalist / niche)
Create a complete perfume with the fewest possible materials.
- **Multi-functional materials**: which materials provide character + texture + performance simultaneously?
- **Minimum viable formula sizes** for each family:
  - Rose: 4-6 materials
  - Jasmine: 5-8 materials
  - Woody: 3-5 materials
  - Amber: 4-6 materials
  - Musk: 3-4 materials (different classes)
  - Citrus: 3-5 materials (+ fixative)
- **Worked example**: 6-material sandalwood that outperforms 25-material sandalwood

---

## SECTION 2: BALANCE METHODS (8 axes)

### Balance Axis 1: Volatility (Evaporation Schedule)
The temporal architecture — when does each note appear and disappear?
- Optimal top:heart:base OAV ratio profiles for each concentration bracket
- Overlap requirement: heart notes must begin contributing before top notes finish
- Base notes must become perceptible before heart notes fade (otherwise: "dead zone")

### Balance Axis 2: Hedonic Contrast (Beautiful + Interesting + Challenging)
Too much beautiful -> insipid. Too much challenging -> unwearable.
- Optimal hedonic distribution: what % of total formula OAV should come from hedonic +3-5 vs hedonic 0-+2 vs hedonic -2-0?
- **Differs by category**: mainstream 70/20/10, niche 50/30/20, luxury 60/25/15
- **The indispensable flaw**: each formula needs one "rough edge" material at OAV 1-10 that prevents it from being forgettable. Most effective edge materials by family (e.g., indole for floral, IBQ for leather, birch tar for chypre, skatole for animalic, geosmin for green).

### Balance Axis 3: OAV Contrast (Depth Through Dynamic Range)
If all materials have similar OAV, the formula reads as a single flat color — no depth.
- Optimal log(OAV) standard deviation for complex perception
- Dominant:background:trace OAV ratio (recommend: 50% of total OAV from 3 materials, 30% from next 6, 20% from the rest)

### Balance Axis 4: Transparency vs Opacity (Clarity vs Density)
Transparent materials (Hedione, Dihydromyrcenol, Calone, Habanolide) feel airy, clean, modern. Opaque materials (Patchouli, Labdanum, Vanillin, Benzoin) feel dense, warm, classical.
- Optimal transparent:opaque material ratio for contemporary style vs classical style
- How does this change with concentration? (lower concentration needs MORE opaque materials to read as present)

### Balance Axis 5: Diffusion (Intimate <-> Sillage)
How far from the skin should each layer be perceived?
- Intimate layer (0-15 cm from skin): vetiver, sandalwood, animalics, close musks
- Personal layer (15-50 cm): florals, coumarin, most heart notes
- Sillage layer (50-200 cm): Hedione, Iso E Super, Calone, aldehydes
- Ambient layer (> 200 cm): very few materials — Hedione HC, Ambrox, Calone at high dose
- **Optimal OAV distribution across layers**: the intimate layer MUST be present or the fragrance feels "hollow" up close

### Balance Axis 6: Material Class Distribution
Per family, what % of total formula weight should come from each material class?
- Provide this breakdown for ALL 20+ families

### Balance Axis 7: Cross-Family Blending Compatibility
Which families can blend without destroying each other's identity?
- **Compatible family pairs**: e.g., floral + citrus, woody + amber, leather + chypre, gourmand + amber
- **Incompatible family pairs**: e.g., marine + gourmand, citrus + leather (general rules, with exceptions)
- **Blending ratio limits**: at what proportion does Family B start to dissolve Family A's character?
- **Transition families**: families that naturally bridge between others (e.g., fougere bridges aromatic <-> chypre, amber bridges oriental <-> woody)

### Balance Axis 8: Maceration as Active Construction Tool
The formula at T=0 is NOT the formula at T=30 days. The perfumer must anticipate and use this.
- **What changes**: free aldehydes convert to acetals (up to 40% within 3 months), esters hydrolyze, reactive pairs form Schiff bases, top notes diminish.
- **Over-dosing strategy**: which materials need to be dosed above target at T=0 because they diminish? (aldehydes, citrus oils, light esters). Which materials amplify over time? (acetals, Schiff bases if present)
- **Maceration milestones**: what character changes at 1 week vs 4 weeks vs 12 weeks?
- **Accelerated testing correlations**: 1 week at 50 degC ~ 3 months at 21 degC (Arrhenius, Ea ~83 kJ/mol)

---

## SECTION 3: FAMILY-SPECIFIC HEDONIC OPTIMIZATION

For EACH family and subfamily below, provide:

1. **Construction methodology** best suited to this family (from the 10 above) + rationale
2. **Balance method** best suited + specific target ratios
3. **The 3-5 defining materials** and their target OAV range in a complete perfume
4. **The "secret" materials** — the 1-3 trace materials (< 1% of concentrate) that make this family smell expensive/natural/beautiful. These are often counter-intuitive (e.g., a trace of indole makes jasmine more realistic, a trace of calone makes a rose fresher).
5. **Hedonic optimization**: what OAV configuration maximizes pleasure for this family?
6. **Common pitfalls**: the most frequent mistakes that destroy hedonic in this family
7. **Hedonic benchmarks**: famous commercial fragrances in this family + their estimated hedonic ratings + what makes them work
8. **Niche vs mainstream differences**: how does the formulation approach differ for niche vs mass-market within this family?
9. **Performance optimization specific to this family**
10. **Exceptions and edge cases**: materials that behave unusually in this family context
11. **Material class % breakdown**: what % of formula weight should go to florals/woods/musks/etc. in this family

### FAMILIES (each with subfamilies):

1. **Citrus / Hesperidic** — cold-pressed, distilled, fresh, juicy, bitter
2. **Aromatic / Fougere** — lavender-coumarin, herbal, mossy, fresh aromatic
3. **Floral** — rose, jasmine, muguet/lily-of-the-valley, violet/iris, orange blossom, tuberose, ylang, white floral composite, lavender, hyacinth, narcissus
4. **Chypre** — classical chypre, fruity chypre, floral chypre, leather chypre, modern/post-IFRA chypre
5. **Amber / Oriental** — soft amber, spicy oriental, woody oriental, vanillic oriental, animalic oriental, floral oriental
6. **Woody** — cedar, sandalwood, vetiver, patchouli, agarwood/oud, pine/coniferous, dry woods, creamy woods
7. **Leather** — birch/IBQ leather, suede, tobacco leather, castoreum, isobutyl quinoline-based, modern synthetic cuir
8. **Musk** — clean white musk, animalic musk, powdery musk, fruity macrolides, nitro-musk alternative
9. **Gourmand** — vanillic, lactonic/creamy, honey, chocolate/coffee, nutty, fruity, caramel/burnt sugar
10. **Green** — galbanum, violet leaf, cut grass, tomato leaf, ivy, green-floral, bitter green
11. **Marine / Aquatic / Ozonic** — seawater, watermelon/calone, mineral/saline, ozonic floral, rainy/petrichor
12. **Spicy** — warm (cinnamon, clove), fresh (cardamom, coriander), hot (black pepper, pink pepper), aromatic (nutmeg, bay)
13. **Aldehydic / Floral-Aldehydic** — classic Chanel No. 5 style, modern aldehydic, sparkling vs waxy
14. **Animalic** — civet, castoreum, ambergris/ambrox, hyraceum, skatole/indolic, costus/sebaceous
15. **Incense / Resinous** — frankincense, myrrh, opoponax, elemi, benzoin, labdanum, olibanum
16. **Powder / Iris** — orris butter, ionone-based, carrot seed, cosmetic powder, lipstick accord
17. **Fruity / Fruity-Floral** — berry, stone fruit, tropical, apple/pear, rhubarb, fig
18. **Wine / Fermented** — rum, cognac, wine lees, fermented fruit, sake/rice wine
19. **Tobacco** — pipe tobacco, cigar, cigarette, dried leaf, smoky
20. **Modern Niche Categories** — transparent skin scent, lactonic/clean, ambrette seed-based, mineral/saline dry-down, matcha/tea, rice/puffed grain/cereal, suede/cuir synthetique, petrichor/geosmin, saline skin, molecule/minimalist

---

## SECTION 4: QUANTIFIED ACCORD RECIPES (35+)

For each accord, provide: precise ratio (parts by weight), each ingredient's OAV at 25% EdP, hedonic contribution, character radar, and construction notes.

### Classical Accords (12 accords)
1. Grojsman Accord (Tresor backbone: Galaxolide/Hedione/Iso E Super/Methyl Ionone)
2. Mousse de Saxe (Iralia/Vanillin/Oakmoss/Geranium/Sandalwood/Star Anise/IBQ)
3. Amber Accord (Labdanum/Benzoin/Vanillin/Styrax/Tolu)
4. Fougere Backbone (Lavender/Coumarin/Oakmoss/Bergamot/Geranium)
5. Chypre Backbone (Bergamot/Labdanum/Oakmoss/Patchouli/Rose) and post-IFRA variant
6. Cologne Accord (Bergamot/Lemon/Orange/Neroli/Lavender/Rosemary/Petitgrain)
7. Classic Rose Accord (PEA/Citronellol/Geraniol/Rhodinol/Rose Oxide/Rose Absolute/Damascone)
8. Classic Jasmine Accord (Benzyl Acetate/Hedione/Indole/Jasmine Absolute/Benzyl Benzoate/Linalool)
9. Cuir de Russie backbone
10. Mitsouko peach-chypre skeleton
11. Shalimar vanillic-amber skeleton
12. Opium spicy-oriental skeleton

### Modern Accords (24+ accords)
13. Modern Fresh Sandalwood (Javanol/Bacdanol/Polysantol/Sandela/Norlimbanol)
14. Woody Amber Base (Ambrox/Clearwood/Iso E Super/Vertofix Coeur/Ambrocenide)
15. Blue/Marine Accord (Calone/Dihydromyrcenol/Hedione/Iso E Super/Aldehyde C12 MNA/Ambrox)
16. Musk Layering Base (Galaxolide/Habanolide/Exaltolide/Nirvanolide/Helvetolide/Romandolide/Ambrox/Ambrocenide)
17. Modern Iris Accord (Alpha Irone/Orivone/Methyl Ionone/Ultralia/Myristic Acid)
18. Clean Skin Musk Accord
19. Tobacco Accord (Coumarin/Labdanum/Benzoin/Hay Absolute/Tonka/Smoky Guaiacol)
20. Leather Accord (Birch Tar/IBQ/Castoreum/Labdanum/Styrax/Benzyl Benzoate/Cedarwood)
21. Marine Seawater Accord (Calone/Dihydromyrcenol/Hedione/Aldehyde C12 MNA/Ambrox/Seaweed Absolute)
22. Honey Accord (Phenylacetic Acid/Methyl Phenylacetate/Rose/Benzyl Benzoate)
23. Incense Accord (Olibanum/Benzoin/Myrrh/Labdanum/Elemi)
24. Oud Accord (Oud/Cypriol/Guaiacol/Saffron/Rose/Cedarwood)
25. Cherry Fruity Accord
26. Fig Accord (Stemone/Fructone/Cassis/Green)
27. Matcha/Tea Accord
28. Cocoa/Chocolate Accord
29. Suede Accord (Suederal/Safraleine/Vetival)
30. Violet Leaf Accord (Parmavert/Undecavertol/Ionone/Violet Fleuressence)
31. Aquatic Ozone Accord (Calone/Floralozone/Aldehydes/Hedione/Scentenal)
32. Cereal / Rice Accord (Methyl Laitone/Ambrettolide/Coumarin/Vanillin trace)
33. Mineral / Stone / Petrichor Accord (Geosmin/Iso E Super/Ambrox/Ultralia/Vetiver)
34. Dirty Animalic Accord (Civetone/Castoreum/Indole/Skatole/Costus/Musk Ketone)
35. Lactonic Cream Accord (Gamma Octalactone/Gamma Decalactone/Delta Decalactone/Coumarin/Vanillin/Ambrettolide)
36. Photorealistic Jasmine Absolute Reconstruction (Benzyl Acetate 45% + Hedione 25% + Linalool 8% + Benzyl Benzoate 12% + Indole 3% + Methyl Benzoate 3% + Cis-Jasmone 2% + trace materials)

---

## SECTION 5: SYNERGY QUANTIFICATION MATRIX

For each synergistic material pair, provide:
- **Mechanism**: H-bond caging, VP modulation (Raoult), receptor co-activation, perceptual fusion/complementation, masking of off-note
- **Optimal weight ratio** (e.g., Hedione:Bergamot = 2:1 to 3:1)
- **Synergy factor**: how many x more intense is the perceived character vs the arithmetic sum of individual OAVs
- **Active OAV range**: at what OAV does synergy appear and at what OAV does it saturate?
- **Hedonic impact**: does the synergy increase or decrease hedonic rating? By how much?
- **Cross-class vs within-class**: does synergy mostly happen within the same chemical class or across classes?

### Priority synergy pairs to cover (200+ pairs):
- Hedione with every major partner (Bergamot, Iso E Super, Jasmine, Rose, Aldehydes, Calone, Neroli, Linalool, Florals)
- Iso E Super with musks, ambers, woods, patchouli, vetiver
- Calone with everything
- Ambrox/Ambrocenide with woody materials
- Coumarin-Vanillin-Ethyl Maltol triangle
- Damascones with rose materials
- Indole with florals (jasmine, tuberose, orange blossom)
- Citrus oils with each other
- Musk cross-class (macrolide + polycyclic + alicyclic)

### Antagonistic pairs (materials that suppress each other):
- Which pairs should NOT be used together?
- At what ratio does antagonism appear?

---

## SECTION 6: HEDONIC INTELLIGENCE DATABASE

For each of 200+ materials:

1. **Intrinsic hedonic rating** (-5 to +5): neat material on blotter at 10% dilution
2. **Context-dependent hedonic adjustments** for each family context — a material's hedonic contribution changes depending on what it's surrounded by:
   - Floral context adjustment (-3 to +3)
   - Chypre context
   - Fougere context
   - Amber/oriental context
   - Gourmand context
   - Aquatic/marine context
   - Leather/animalic context
   - Citrus/fresh context
   - Woody context
   - Green context
3. **Hedonic dose-response**: at what OAV is the material most pleasant? At what OAV does it flip from pleasant to unpleasant? Where is the "sweet spot"?
4. **Hedonic contrast pairs**: materials X + Y that make each other MORE pleasant when combined (e.g., Indole + Jasmine Absolute = more beautiful jasmine than Jasmine Absolute alone)
5. **Hedonic suppression pairs**: materials that reduce each other's unpleasant facets (e.g., Coumarin masks the medicinal facet of Lavender)
6. **Panel hedonic data**: any published consumer panel pleasantness ratings

---

## SECTION 7: CHARACTER SHIFT ZONES + HILL PARAMETERS

For each material, define at least 3 concentration zones where character qualitatively changes:

- **Zone 1** (trace): sub-perceptual to barely perceptible — character, hedonic, texture
- **Zone 2** (moderate): clearly present, character is recognizable
- **Zone 3** (dominant): primary driver, character is strong and potentially shifts
- **Zone 4** (overdose): character has flipped — may be unpleasant, aggressive, or transformed into something else
- **Zone 5** (danger): unusable, character is offensive or unstable

Plus: **Hill equation parameters**:
- **EC50** = % in concentrate for half-maximal perceptual shift
- **n** = Hill coefficient for shift steepness (n > 1 = sharp transition, n < 1 = gradual)
- **Rmax** = maximum response plateau

### Priority character-flip materials (well-documented):
- Indole: floral (0.001-0.1%) -> indolic-jasmine (0.1-0.5%) -> fecal (0.5%+)
- IBQ: leather-fine (0.001-0.05%) -> leather-strong (0.05-0.1%) -> medicinal-tar (0.5%+)
- Calone: marine-watermelon (0.001-0.02%) -> metallic-ozonic off-note (0.02%+)
- Skatole: floral-animalic (0.0001-0.001%) -> nauseating (0.01%+)
- Birch Tar: smoky-leather (0.01-0.1%) -> creosote-barbecue (0.5%+)
- Vanillin: sweet-creamy (0.1-2%) -> cloying-plasticky (5%+)
- Aldehydes C10/C11: sparkling-fresh (0.01-0.5%) -> fatty-rancid (1%+)
- Coumarin: hay-tonka (0.1-2%) -> bitter-almond (5%+)
- Galaxolide: clean-powdery (1-15%) -> overwhelming-suffocating (30%+)
- Damascones: rose-plum (0.001-0.05%) -> metallic-harsh (0.1%+)
- Ethyl Maltol: cotton-candy (0.01-0.3%) -> burnt-sugar artificial (1%+)
- Geosmin: rain-on-earth (0.00001-0.0001%) -> dirt-beetroot (0.001%+)
- Safranal: saffron-leather (0.0001-0.001%) -> medicinal (0.01%+)
- Rose Oxide: rosy-metallic-fresh (0.0001-0.001%) -> geranium-harsh (0.01%+)

---

## SECTION 8: CHEMICAL COMPATIBILITY MATRIX

### Reaction Matrix (pairs that react in-bottle):

| Reaction Type | Material Classes Involved | Mechanism | Rate (25 degC) | Products | Smell? | Color? | Mitigation |
|---|---|---|---|---|---|---|---|
| Schiff base | Aldehydes + primary amines | Carbonyl-amine condensation | Days-weeks | Imine (higher MW, lower VP) | Different (brown floral) | Yellow-brown | Separate, add amine at end |
| Acetal formation | Aldehydes + ethanol | Aldehyde + 2 ROH -> acetal + H2O | Weeks-months | Acetal (less volatile, less intense) | Softer, longer-lasting | None | Use aldehyde in solvent other than ethanol |
| Hydrolysis | Esters + water (pH < 5 or > 8) | Ester + H2O -> acid + alcohol | Months | Free acid + alcohol | Loss of fruity ester | None | pH buffer (pH 5.5-7), minimize water |
| Autoxidation | Terpenes (limonene, pinenes) + O2 | Radical chain, light-catalyzed | Weeks | Hydroperoxides, epoxides | Off-notes, rancid | None | BHT/tocopherol, UV protection, headspace gas |
| Phenol oxidation | Eugenol, vanillin, guaiacol + O2 | Phenol -> quinone | Weeks-months | Quinones (colored) | Different | Dark brown | Antioxidant, pH < 7 |
| Transesterification | Multiple esters + ethanol | Ester exchange | Months | Mixed esters | Subtle shift | None | Minimize ester diversity or accept |
| Photo-oxidation | Expressed citrus oils + UV | Singlet oxygen attack on limonene | Days (sunlight) | Hydroperoxides, phototoxic products | Rancid, off | Yellow | UV absorber (octocrylene), amber glass |
| Polymerization | Conjugated dienes (farnesol, geraniol) | Radical or thermal | Months | Dimers, oligomers | Heavier, less volatile | Possible | Antioxidant, cool storage |

---

## SECTION 9: PERFORMANCE PROFILES (TEMPORAL + EVAPORATION)

For each of 200+ materials:

1. **Evaporation half-life on skin** at 32 degC (minutes/hours)
2. **Evaporation half-life on blotter** at 25 degC (minutes/hours)
3. **Substantivity class**: fleeting (< 30 min) / short (30 min-2 hr) / moderate (2-6 hr) / long (6-12 hr) / very long (> 12 hr)
4. **Sillage radius class**: intimate (< 15 cm) / personal (15-50 cm) / arm's length (50-150 cm) / room-filling (> 150 cm)
5. **Note tier by VP**: top (> 50 Pa) / heart (0.5-50 Pa) / base (< 0.5 Pa)
6. **Clausius-Clapeyron temperature sensitivity**: VP ratio at 35 degC vs 22 degC (Bangkok vs Paris)
7. **Skin vs fabric performance**: materials that bind strongly to fabric (cotton, polyester) vs skin
8. **logP and partitioning**: which materials are headspace-dominant vs skin-depot vs fabric-depot?

---

## SECTION 10: uL DOSING TABLES

For all 200+ materials at their common stock dilutions (neat, 50%, 10%, 1%, 0.1%), provide a lookup table:

| Material | Stock % | Target % in 10g concentrate | uL needed | Equivalent ppm in conc | Estimated OAV at 25% EdP |

Include special handling instructions:
- **Solids** (Coumarin, Vanillin, Oranger Crystals, Ethyl Maltol, Musk Ketone): recommended solvent for stock solution, max solubility at 20 degC and 5 degC
- **Viscous** (Labdanum Absolute, Benzoin Resinoid, Benzoin Sumatra): pre-warm to 40 degC, measure by weight not volume, recommended stock dilution for handling
- **Crystalline at low temperature** (Coumarin, Vanillin): minimum stock concentration that stays liquid at 5 degC, recommended co-solvent ratios (benzyl benzoate or IPM)
- **Light-sensitive** (all expressed citrus, aldehydes): amber glass, UV-blocker recommendation, maximum shelf life after dilution
- **Oxygen-sensitive** (terpenes, aldehydes): headspace purge with N2 or argon, antioxidant loading rate

---

## SECTION 11: FORMULA ITERATION PROTOCOL

Codify the systematic process for refining a formula from first draft to final version:

1. **T=0: First Blend** — evaluate the skeleton only. Does the core accord do what it should? If not, adjust RATIOS before adding anything. Never fix a bad skeleton by adding more materials.
2. **T=2 days** — aldehyde-ethanol equilibration begun. Evaluate for rough edges. Remove or reduce the 1-2 worst offenders.
3. **T=1 week** — early maceration complete. Evaluate character completeness. Add 1-2 materials to fill gaps but DO NOT add more than 3 materials per iteration.
4. **T=2 weeks** — intermediate maceration. Evaluate performance (does it last? project?). Adjust fixative:volatile balance.
5. **T=4 weeks** — primary maceration complete. This is the FIRST reliable evaluation. Evaluate at 4 different distances (close skin, personal, arm's length, room entry). Compare to T=0. Adjust trace-level materials only (< 1% changes).
6. **T=8 weeks** — secondary maceration. Final adjustments. At this point, changes should be < 0.5% of formula weight.
7. **T=12 weeks** — final maceration. If still making changes at T=12, restart from a different skeleton.

**When to stop iterating**: when removing any material makes the formula worse (Roudnitska test).

---

## SECTION 12: EDGE CASES & EXCEPTIONS

### Anosmia Coverage (critical for musk formulation)
Document anosmia prevalence in population for all major musks:
- Androstenone: ~50% (specific genetic receptor)
- Iso E Super: ~30-40%
- Galaxolide: ~30%
- Muscone: ~15%
- beta-ionone: ~20%
- Cashmeran: ~10-15%
- Ambroxan: ~5-10%
- Linalool: ~5%

**Rule**: never rely on a single musk class. Minimum 3 different musk classes (polycyclic + macrocyclic + alicyclic) per formula to cover > 95% of population.

### Temperature Sensitivity
Many materials perform dramatically differently in tropical (35 degC, 80% RH) vs temperate (22 degC, 50% RH):
- VP ratio at 35 degC vs 22 degC (Clausius-Clapeyron, deltaHvap ~ 60 kJ/mol): factor ~2.8x
- Tropical formulas need 2-3x MORE base loading to maintain same temporal balance
- Which materials fail in high humidity? (water-reactive esters, hygroscopic materials)

### Solubility Risk Materials
At 5 degC (cold-shipping, winter storage):
- Coumarin: precipitates below 2% in ethanol 96%
- Vanillin: precipitates below 5% in ethanol 96%
- Oranger Crystals: precipitates below 1% without co-solvent
- Ethyl Maltol: precipitates below 0.5% over time
- Musk Ketone: precipitates below 1% in ethanol
- **Co-solvent fix**: benzyl benzoate 5-10%, IPM 5-10%, or DPG 5-15% eliminates precipitation for most of these

### Natural EO Complexity vs OAV Math
Natural essential oils are multi-component. Their effective OAV is NOT a single number:
- Bergamot EO: 30+ odor-active compounds. Dominant characters: linalool (ODT 0.51 ppb), linalyl acetate (ODT 2.7 ppb), limonene (ODT 10 ppb — mass dominant but not character dominant).
- When the natural EO is in the formula, use the ODT of the character-defining constituent, NOT the mass-dominant constituent.
- Natural EOs often have enhanced character due to trace compounds (e.g., grapefruit character is driven by 1-p-menthene-8-thiol at 0.0001 ppb, not limonene at 10 ppb despite limonene being 90% of the oil mass).

### Market-Specific Formulation Differences
Same formula at different concentration brackets is NOT just dilution:
- 40% extrait -> 20% EdP: reduce base loading ~20% (bases are already strong), increase heart ~10% to compensate for lower substantivity, keep top similar. OAV ratios change non-linearly due to Raoult non-ideality (activity coefficients shift with concentration).
- 20% EdP -> 5% body spray: dramatic shift. Base notes become sub-threshold. Top notes dominate. Add significant base loading (2-3x) to maintain dry-down presence. Or: use different, more potent base materials.
- Candle: entirely different design. Materials with VP < 0.005 Pa never reach headspace. Use only materials with VP 0.01-100 Pa.

### The "Ghost Note" Phenomenon
Some materials are perceptually present at OAV < 1 because they activate OR receptors without full perception — they add "texture" or "depth" without being directly identifiable. This is the basis of "transparent" perfumery (Ellena). Materials that produce this effect: Hedione (OR2G2), Iso E Super (multiple ORs), Ambroxan (OR7A17), Ultralia, Floralozone.

---

## SECTION 13: LITERATURE REFERENCES TO CITE

Classify all sources as:
- **Tier A**: peer-reviewed journal articles with direct sensory data
- **Tier B**: classical perfumery texts
- **Tier C**: practitioner codifications and supplier documentation
- **Tier D**: regulatory documents (IFRA, SCCS, EU)
- **Tier E**: author estimate based on structural analogy / homolog series

Literature to search and cite:
- Kraft & Swift (2005) "Perspectives in Flavor and Fragrance Research"
- Ohloff, Pickenhagen & Kraft (2011) "Scent and Chemistry: The Molecular World of Odors"
- Sell (2006) "The Chemistry of Fragrances: From Perfumer to Consumer"
- Turin (2006) "The Secret of Scent: Adventures in Perfume and the Science of Smell"
- Arctander (1969) "Perfume and Flavor Chemicals"
- Arctander (1960) "Perfume and Flavor Materials of Natural Origin"
- Jellinek (1997) "The Psychological Basis of Perfumery"
- Roudnitska "The Art of Perfumery" and various essays
- Carles (1961) "A Method of Creation in Perfumery"
- Ellena (2011) "Perfume: The Alchemy of Scent"
- Livermore & Laing (1996, 1998) — mixture perception limits
- Elsharif et al. (2015) — linalool/linalyl acetate ODT
- Motooka et al. (2015) — damascenone ODT
- Birkbeck et al. (2025) — javanol ODT
- Kraft (2008) — Iso E Super / Arborone
- Kraft & Eichenberger (2004) — Romandolide
- Porta et al. (2005) — Hedione isomer
- van Gemert (2011) "Compilations of Odour Threshold Values in Air, Water, and Other Media"
- Devos et al. (1990) "Standardized Human Olfactory Thresholds"
- Nagata (2003) "Measurement of Odor Threshold by Triangle Odor Bag Method"
- Czerny et al. (2008) — odor thresholds
- Rychlik et al. (1998) — odor thresholds of food odorants
- Teixeira et al. (2024) — OAV in perfumery
- IFRA 51st Amendment standards
- SCCS/1525/21 — EU allergen expansion
- EU Regulation 1223/2009 Annex III

---

## OUTPUT FORMAT

Return ALL data as structured JSON arrays matching these exact schemas:

```json
{
  "construction_methodologies": [
    {
      "method": "A",
      "name": "Pyramid Construction",
      "philosophy": "...",
      "when_to_use": "...",
      "limitations": "...",
      "worked_examples": [
        {
          "description": "Rose-Chypre at EdP strength",
          "formula": [{"material": "Bergamot FCF", "pct": 12.0, "oav_target": 150, "time_windows": "0-45min"}, ...],
          "t_h_b_ratio": [30, 40, 30],
          "hedonic": 3.5,
          "notes": "..."
        }
      ]
    }
  ],
  "balance_methods": [
    {
      "axis": "volatility",
      "name": "Evaporation Schedule",
      "description": "...",
      "target_ratios": {"EdC": [50, 30, 20], "EdT": [40, 35, 25], "EdP": [30, 35, 35], "Extrait": [20, 35, 45]},
      "material_examples": [...]
    }
  ],
  "accords": [
    {
      "name": "Grojsman Accord",
      "family": "floral-amber",
      "source": "Sofia Grojsman (IFF)",
      "ingredients": [{"material": "Galaxolide 50%", "parts": 1.0, "pct_in_accord": 25.0, "oav_in_accord": 45.0, "hedonic_contribution": 2.0, "role": "musk fixative backbone"}, ...],
      "character": {"warmth": 5, "sweetness": 4, "freshness": 5, "powdery": 6, "green": 0, "animalic": 0, "radiance": 8, "woody": 4, "spicy": 0, "floral": 6, "smoky": 0, "creamy": 3, "transparency": 8},
      "hedonic": 4.0,
      "typical_use_pct": 15.0,
      "variants": [...],
      "notes": "..."
    }
  ],
  "synergies": [
    {
      "materials": ["Hedione", "Bergamot FCF"],
      "mechanism": "Hedione enhances radiance of bergamot top notes; bergamot's linalool bridges to hedione's jasmine character via OR2G2 co-activation",
      "optimal_ratio": {"Hedione": 65, "Bergamot FCF": 35},
      "synergy_factor": 2.5,
      "active_range": {"min_oav": 1.0, "max_oav": 200.0},
      "hedonic_impact": 1.5,
      "source": "..."
    }
  ],
  "hedonic_profiles": [
    {
      "material": "Indole",
      "intrinsic": -2.5,
      "context_adjustments": {"floral": 4.5, "jasmine": 5.0, "orange_blossom": 3.5, "chypre": 0.0, "fougere": -2.0, "oriental": 1.5, "gourmand": -4.0, "aquatic": -5.0, "leather": 0.5, "citrus": -5.0, "woody": -1.0, "green": -2.0},
      "dose_response": "Peak hedonic at OAV 2-5 in jasmine context. Flips to fecal at OAV > 15.",
      "sweet_spot_oav": 3.0,
      "contrast_pairs": [["Indole", "Jasmine Absolute"], ["Indole", "Benzyl Acetate"], ["Indole", "Hedione"]],
      "suppression_pairs": [["Indole", "Methyl Benzoate"], ["Indole", "Cis Jasmone"]]
    }
  ],
  "character_shifts": [
    {
      "material": "Indole",
      "zones": [
        {"zone": "trace", "min_pct": 0.0, "max_pct": 0.05, "oav_range": [0, 0.5], "character": "green-floral, barely animalic", "hedonic": 1.0, "quality": "neutral"},
        {"zone": "moderate", "min_pct": 0.06, "max_pct": 0.5, "oav_range": [0.6, 5.0], "character": "indolic-jasmine, narcotic white floral", "hedonic": 4.5, "quality": "positive"},
        {"zone": "dominant", "min_pct": 0.6, "max_pct": 2.0, "oav_range": [5.1, 20.0], "character": "heavy animalic, challenging niche territory", "hedonic": 0.0, "quality": "dangerous"},
        {"zone": "overdose", "min_pct": 2.1, "max_pct": 100.0, "oav_range": [20.1, 9999], "character": "fecal, nauseating, unwearable", "hedonic": -5.0, "quality": "dangerous"}
      ],
      "hill_ec50": 0.3,
      "hill_n": 2.1,
      "hill_rmax": 1.0
    }
  ],
  "chemical_compatibility": [
    {
      "pair": ["Aldehyde C12 MNA", "Methyl Anthranilate"],
      "reaction_type": "Schiff base (aldimine formation)",
      "rate": "days-weeks at 25 degC",
      "products": "Imine (MW ~300, brown-yellow, orange blossom/floral character shift)",
      "flag": "avoid",
      "mitigation": "Separate storage. If combined, accept shift and evaluate at T=4 weeks only."
    }
  ],
  "performance_profiles": [
    {
      "material": "Galaxolide",
      "vp_pa_25c": 0.0001,
      "half_life_skin_32c_min": 1440,
      "half_life_blotter_25c_min": 2880,
      "substantivity": "very long",
      "sillage_radius": "personal",
      "note_tier": "base",
      "temperature_factor_35c_vs_22c": 3.0,
      "skin_vs_fabric": "fabric-dominant (logP 5.9)"
    }
  ],
  "dosing_tables": [
    {
      "material": "Beta Damascone",
      "stock_pct": 1.0,
      "target_pct": 0.01,
      "ul_per_10g_concentrate": 10.0,
      "equivalent_ppm_in_conc": 100,
      "estimated_oav_25pct_edp": 250.0,
      "handling": "Dilute to 0.1% stock for precision. 1% stock is too strong for manual pipetting at sub-10 uL."
    }
  ],
  "edge_cases": [
    {
      "type": "character_flip",
      "material": "Calone",
      "description": "Marine-watermelon at < 0.02% in concentrate. Metallic-ozonic off-note above 0.02%. At 0.5%, reads as 'synthetic pool cleaner.' Keep below 0.015% for safety margin.",
      "recommended_max_pct": 0.015
    }
  ],
  "family_profiles": [
    {
      "family": "Floral -- Jasmine",
      "methodology": "Accord-Based + Hedonic Optimization",
      "balance_targets": {"volatility_ratio_t_h_b": [25, 50, 25], "hedonic_distribution": [50, 35, 15], "oav_contrast_std_log": 0.8, "transparency_ratio": 60, "diffusion_layers": [15, 60, 50, 5]},
      "defining_materials": [
        {"material": "Hedione", "target_oav": 50, "role": "radiance, jasmine diffusion backbone"},
        {"material": "Benzyl Acetate", "target_oav": 30, "role": "fresh-floral top"},
        {"material": "Indole", "target_oav": 3, "role": "animalic warmth and depth"},
        {"material": "Jasmine Absolute", "target_oav": 8, "role": "natural jasmine anchor"}
      ],
      "secret_materials": [{"material": "Cis Jasmone", "pct": 0.3, "oav": 2.0, "note": "adds photorealistic green-jasmine freshness"}],
      "common_pitfalls": ["Overdosing indole (> 5% creates fecal)", "Too much benzyl acetate (soapy)", "Not enough hedione (lacks diffusion, too much benzyl acetate reads as cheap)"],
      "benchmarks": [{"fragrance": "Dior J'Adore", "estimated_hedonic": 4.5, "key_insight": "Hedione-forward with clean jasmine + fruity top"}],
      "niche_vs_mainstream": {"mainstream": "Hedione-dominant, clean indole, smooth muguet modifiers. Target hedonic > 4.0.", "niche": "Higher indole, animalic facets, jasmine absolute-forward, less hedione cushion. Target hedonic > 3.0."},
      "material_class_breakdown": {"florals": 50, "citrus": 10, "musks": 15, "woods": 10, "fixatives": 10, "animalic": 5},
      "performance_notes": "Hedione bridges heart-to-base. Indole adds substantivity via skin binding. Benzyl Benzoate 5% extends jasmine absolute longevity."
    }
  ]
}
```

**INSTRUCTIONS**: Research and output ALL data in a single structured JSON file. Each section is a top-level key in the JSON. Material names must match the exact naming conventions used in professional perfumery (e.g., "Hedione" not "methyl dihydrojasmonate", "Iso E Super" not "isocyclemone E"). Omit empty fields rather than returning null. When a value is uncertain, include `"_confidence": "low|medium|high"` and `"_source": "citation or reasoning"`. Target minimum: 200 materials covered, 35+ accords with full ratios, 200+ synergy pairs quantified, all 20 family categories with full subfamily breakdowns.
```

---

Final content review — sections added to address gaps found in the earliest draft:

| Gap identified | Where addressed |
|---|---|
| Cross-family blending | Section 2, Axis 7 — compatible/incompatible pairs, ratio limits, transition families |
| Livermore & Laing complexity paradox | Philosophical Foundation — OAV contrast illusion mechanism explained |
| Maceration as active construction tool | Section 2, Axis 8 — over-dosing strategy, T=0 vs T=30 day design |
| Concentration bracket calibration | Section 12, Market-Specific Differences — 40% vs 20% vs 5% adjustment rules |
| Fixative physics | Section 1-H — VP suppression (Raoult), caging, logP skin binding, H-bonding |
| Natural EO OAV math | Section 12 — multi-component character-defining vs mass-dominant distinction |
| Systematic iteration protocol | Section 11 — 7-stage timeline from T=0 to T=12 weeks |
| Evolution kinetics | Section 11 — what changes at 1, 2, 4, 8, 12 weeks of maceration |
| Market category adaptation | Section 12 — EdP vs body spray vs candle design rules |
| Panel methodology | Section 11 — evaluation distances, T=4 as first reliable point |
