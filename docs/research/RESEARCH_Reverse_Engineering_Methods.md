# Scientific Methods for Reverse-Engineering Perfume Formulas from Public Information

## A Research Report for Hobbyist Perfumers

---

## Table of Contents

1. [Evidence Sources for Reverse-Engineering Perfumes](#1-evidence-sources)
2. [Evidence Fusion & Combination Methods](#2-evidence-fusion)
3. [Perfumery-Specific Reconstruction Methods](#3-perfumery-reconstruction)
4. [Technical Implementation Considerations](#4-technical-implementation)

---

## 1. Evidence Sources

### 1.1 GC-MS Data (Gas Chromatography–Mass Spectrometry)

**What it reveals:** GC-MS is the gold standard analytical technique for identifying volatile and semi-volatile organic compounds in perfumes. It separates a complex mixture into individual components (GC step), then identifies each by its mass spectrum (MS step).

**Reliability for reconstruction: HIGH (0.85–0.95 confidence)**

**Key characteristics:**
- **Electron ionization (EI)** at 70 eV is standard; produces reproducible fragmentation patterns
- **Spectral libraries** (NIST, Wiley) contain 250,000+ reference spectra for compound matching
- **Detection modes:** Full scan (broad identification) vs. Selected Ion Monitoring (SIM, higher sensitivity for known targets)
- **Headspace GC-MS** and solid-phase microextraction (SPME) are used for volatile analysis without destroying the sample

**What GC-MS tells you about a perfume:**
- Identification of specific aroma chemicals (e.g., "this contains linalool, hedione, and Iso E Super")
- Approximate relative proportions from peak area ratios (±10–20% accuracy)
- Detection of synthetic vs. natural origin markers (e.g., chiral ratios of linalool distinguish synthetic from lavender-derived)
- Essential oil fingerprints (terpene profiles reveal whether bergamot is Calabrian or synthetic reconstitution)

**What GC-MS does NOT tell you:**
- **Absolute concentrations** in the original formula (only relative proportions of volatiles)
- **Non-volatile components** like musks (Galaxolide, Ambrox) are underrepresented due to low volatility
- **Finished formula percentages** — a GC trace of the headspace is biased toward top notes
- **Pre-blending details** — whether a component came from an EO or was added as a pure synthetic
- **Base materials like DPG, ethanol** are solvents/carriers and may obscure trace components

**Where to find GC-MS data as a hobbyist:**
- Published academic papers analyzing commercial perfumes (search PubMed, Google Scholar for "GC-MS fragrance analysis")
- Leffingwell & Associates database (partial free access)
- The Good Scents Company (thegoodscentscompany.com) — lists GC-MS profiles of many essential oils and aroma chemicals
- Scientific papers on essential oil composition (e.g., "chemical composition bergamot essential oil GC-MS")
- EU SCCS (Scientific Committee on Consumer Safety) opinions sometimes include analytical data

**Practical numbers:**
- A typical fine fragrance contains 30–80 distinct chemical entities detectable by GC-MS
- Top 10 components usually account for 60–80% of total detected mass
- Components below 0.1% of the formulation are often at or below detection limits in headspace analysis
- Modern GC-MS can detect some compounds at parts-per-billion (ppb) levels

---

### 1.2 Patent Databases

**What they reveal:** Fragrance patents disclose specific formulation information — sometimes exact formulas, sometimes ranges or classes of materials.

**Reliability for reconstruction: MODERATE (0.50–0.75 confidence)**

**Types of fragrance patents:**
1. **Composition patents** — Disclose exact formulas as examples (most useful). Example claims format: "A fragrance composition comprising 5–15% hedione, 2–8% Iso E Super, 0.5–3% Ambroxan..."
2. **Process patents** — Describe manufacturing methods (less useful for formula reconstruction)
3. **Use patents** — Describe applications of specific materials (useful for understanding material function)
4. **Captive molecule patents** — Disclose new aroma chemicals (e.g., Givaudan's patent for Javanol, IFF's patent for Iso E Super). These reveal the EXISTENCE of proprietary materials but not which commercial perfumes use them.

**Where to search:**
- **Google Patents** (patents.google.com) — Free, full-text searchable, covers USPTO, EPO, WIPO, JPO
- **Espacenet** (worldwide.espacenet.com) — European Patent Office, excellent for Givaudan/Firmenich/Symrise patents
- **WIPO PatentScope** (patentscope.wipo.int) — International PCT applications

**Key search strategies:**
- Search by company name + "fragrance composition" or "perfume composition"
- Search by CAS number of known aroma chemicals
- Search by IUPAC name or trade name of specific captive molecules
- IPC class C11B 9/00 = "Essential oils; Perfumes" — use this classification code
- Look for patents by known perfumers (check Fragrantica for perfumer name, then search patents by inventor)

**Critical caveats:**
- Patents often list RANGES, not exact amounts: "1–20% of a musk component" is technically accurate but unhelpful
- The example formulations in patents are real compositions but may not correspond to any commercial product
- Fragrance houses deliberately obfuscate patents — they patent many compositions they never commercialize
- Captive molecules (e.g., Givaudan's Paradisone, Firmenich's Clearwood) appear in patents by trade name AND chemical name — you need both to track them
- Patent examples typically show concentrations as weight percent of the fragrance oil concentrate, NOT the finished alcohol solution

**Typical patent formula structure:**
```
Component A (hedione):           15.0%
Component B (Iso E Super):        8.0%
Component C (bergamot EO):        5.0%
Component D (Ambroxan):           3.0%
Component E (linalool):           2.0%
...
Carrier (DPG or DEP):            balance to 100%
```

---

### 1.3 EU Allergen Declarations (INCI / Cosmetics Regulation)

**What they reveal:** EU Regulation (EC) No 1223/2009 on cosmetic products mandates that 26 specific fragrance allergens must be declared on product packaging when present above specified thresholds.

**Reliability for reconstruction: LOW-MODERATE (0.30–0.55 confidence) — but high CERTAINTY for confirming presence/absence of specific materials**

**The 26 mandatory allergens (and what they tell a reconstructor):**

| Allergen (INCI Name) | Chemical Identity | Reconstruction Clue |
|---|---|---|
| Linalool | Linalool | Present in most florals, lavender, bergamot, rosewood, coriander |
| Limonene | D-Limonene | Citrus materials present (orange, lemon, bergamot) |
| Citronellol | Citronellol | Rose materials (geranium EO, rose EO, or synthetic citronellol) |
| Geraniol | Geraniol | Rose, palmarosa, geranium, or synthetic geraniol |
| Citral | Citral (neral + geranial) | Lemongrass, litsea cubeba, verbena, or citrus peel oils |
| Coumarin | Coumarin | Coumarin present (fougère structure likely, or tonka/lavender) |
| Eugenol | Eugenol | Clove, carnation, rose absolute, cinnamon leaf |
| Isoeugenol | Isoeugenol | Carnation, ylang-ylang, or synthetic isoeugenol |
| Cinnamal | Cinnamaldehyde | Cinnamon materials |
| Cinnamyl alcohol | Cinnamyl alcohol | Balsamic materials, styrax, hyacinth |
| Hydroxycitronellal | Hydroxycitronellal | Muguet (lily of the valley) accords |
| Benzyl alcohol | Benzyl alcohol | Jasmine absolute, ylang-ylang, or solvent residue |
| Benzyl benzoate | Benzyl benzoate | Fixative, balsams, jasmine absolute |
| Benzyl salicylate | Benzyl salicylate | Key fixative — cosmetic-clean, diffusion base |
| Benzyl cinnamate | Benzyl cinnamate | Balsam of Peru, balsam of Tolu |
| Alpha-isomethyl ionone | Alpha-isomethyl ionone | Violet/iris accords (the synthetic ionone) |
| Butylphenyl methylpropional (Lilial) | Lilial / BMHCA | NOW BANNED in EU — if listed, old stock |
| Amyl cinnamal | Amyl cinnamaldehyde | Jasmine character, floral aldehydic |
| Amylcinnamyl alcohol | Amylcinnamyl alcohol | Floral fixative |
| Hexyl cinnamal | Hexyl cinnamaldehyde | Chamomile, floral-fruity |
| Farnesol | Farnesol | Floral (muguet, linden), antibacterial |
| Methyl 2-octynoate | Methyl heptin carbonate | Violet-leaf green, metallic |
| Anise alcohol | Anise alcohol | Anisic notes, rare |
| Evernia prunastri | Oakmoss extract | CHYPRE structure confirmed |
| Evernia furfuracea | Treemoss extract | Chypre/fougère structure |
| HICC (Lyral) | Hydroxyisohexyl 3-cyclohexene carboxaldehyde | NOW BANNED in EU |

**Thresholds for declaration:**
- **Leave-on products** (perfume, body lotion): Must declare if allergen exceeds **0.001%** (10 ppm) of finished product
- **Rinse-off products** (shampoo, shower gel): Must declare if allergen exceeds **0.01%** (100 ppm)

**How to use this for reconstruction:**
- The ORDER of allergens on the INCI list is NOT concentration-ordered (unlike other INCI ingredients)
- PRESENCE confirms the material or a natural source containing it is used
- ABSENCE at low concentrations is ambiguous — the material may be present just below threshold
- Cross-reference with GC-MS: if limonene and linalool are declared, AND the fragrance smells of bergamot, the source is likely bergamot EO (which contains both)
- If coumarin is declared, expect a fougère/coumarinic base structure
- If oakmoss (Evernia prunastri) is declared, the perfume has a chypre architecture

**Updated regulation note (2023+):** The EU has expanded the allergen list from 26 to approximately 80+ substances under the revised Cosmetics Regulation annexes. This provides even more reconstruction data from packaging.

---

### 1.4 Fragrantica / Basenotes Community Data

**What they reveal:** Crowd-sourced olfactive descriptors, accords, note pyramids, longevity/sillage ratings, and comparative commentary.

**Reliability for reconstruction: LOW individually (0.15–0.35 confidence per review), MODERATE in aggregate (0.45–0.65 when meta-analyzed across 50+ reviews)**

**Fragrantica data structure:**
- **Official notes pyramid:** TOP / HEART / BASE — listed by the brand, not analytically verified
  - These are marketing notes, not formulation notes
  - "Oud" in the notes pyramid usually means a synthetic oud accord, not real oud
  - "Amber" almost always means Ambroxan or an amber base, not actual amber
- **User votes on notes:** Users can vote whether they detect specific notes → this is consensus olfaction
- **Accords chart:** Aggregated user perception of fragrance character (woody, floral, fresh, etc.)
- **Longevity/sillage ratings:** Crowdsourced, scale-sensitive, but directionally informative
- **"Similar perfumes"** recommendations — useful for identifying shared accord structures

**Basenotes data structure:**
- More technically literate community than Fragrantica
- Forum discussions often contain perfumer-level analysis
- Users sometimes post partial GC-MS results or deconstruction analyses
- "What's in this?" threads often contain high-quality educated guesses

**How to extract reconstruction value from community data:**

1. **Consensus note extraction:** If 80%+ of users detect "iris" and "cedar," the formula almost certainly contains ionones and cedarwood materials
2. **Negative evidence:** If a note is listed officially but <10% of users detect it, the brand is using a trace amount or a marketing fiction
3. **Comparative analysis:** "X smells like Y but with more vanilla" → shared structural base, Y's formula + vanilla augmentation
4. **Temporal analysis:** "The opening is aldehydic, drying down to sandalwood-musk" → reveals the volatility structure and approximate material classes
5. **Reformulation detection:** Multiple users noting "it changed after 2018" → ingredient substitution occurred, often due to IFRA regulation changes

**Statistical extraction approach:**
- Treat each user review as a noisy sensor reading
- Weight users by their review history length and consistency
- Apply majority-vote consensus with a minimum threshold (e.g., note mentioned by ≥30% of reviewers = "detected")
- Weight "power reviewers" (500+ reviews) more heavily than casual reviewers

---

### 1.5 Perfumer Disclosures and Brand Marketing

**What they reveal:** Perfumers occasionally discuss their creative process, key materials, or inspiration in interviews. Brand marketing reveals intended olfactive positioning.

**Reliability: MODERATE (0.40–0.70 confidence)**

**Sources:**
- **Perfumer interviews** (Nez magazine, Cafleurebon, ÇaFleureBon, Fragrantica interviews)
  - Jean-Claude Ellena famously discussed his minimalist approach and specific material choices
  - Francis Kurkdjian has discussed hedione dosing philosophy
  - Perfumers sometimes name specific captive molecules they used
- **Brand press releases** — mention key ingredients (usually the "hero" note)
- **Behind-the-scenes videos** — occasionally show the perfumer's organ or brief formulation glimpses
- **Masterclass/educational content** — perfumers teaching sometimes reference commercial formulas
- **Stevenotes/keynotes at fragrance conferences** (World Perfumery Congress, Esxence)

**Calibration notes:**
- When a perfumer says "I used a lot of hedione," this typically means 15–30% of the concentrate
- When they say "just a touch of" something, this typically means 0.1–2%
- "The backbone is Iso E Super" = likely 10–25% of concentrate
- Perfumers NEVER disclose exact percentages in public — they speak in relative terms
- Marketing language overstates naturals and understates synthetics

---

### 1.6 IFRA Standards and Restriction Lists

**What they reveal:** IFRA publishes maximum permitted concentrations for ~180 materials across 11 product categories. This provides UPPER BOUNDS on material dosing.

**Reliability for bounding: HIGH (0.80–0.90 for establishing maximum possible concentration)**

**How IFRA limits aid reconstruction:**
- Category 4 (fine fragrance, applied to skin) has specific limits
- Example: Oakmoss extract (Evernia prunastri) is limited to 0.1% in Category 4 → if a perfume contains oakmoss, you KNOW it can't exceed ~1% of concentrate at 10% EdP dilution
- Coumarin maximum in fine fragrance: determined by IFRA 50th Amendment
- Citral: restricted due to sensitization — maximum varies by category
- Methyl eugenol: restricted to very low levels — eliminates certain natural sources (basil EO high in methyl eugenol)

**This is primarily useful for:**
- Setting ceiling values: "Material X cannot exceed Y% in this product type"
- Eliminating impossible formulations: "This can't have 5% oakmoss — IFRA limits it to 0.1%"
- Inferring reformulations: "Pre-2009 versions could contain higher oakmoss"

---

## 2. Evidence Fusion & Combination Methods

### 2.1 Bayesian Inference Framework

**Core principle:** Start with prior beliefs about what materials a perfume might contain, then update those beliefs as evidence accumulates from different sources.

**Bayes' Theorem:**

$$P(M_i | E) = \frac{P(E | M_i) \cdot P(M_i)}{P(E)}$$

Where:
- $P(M_i | E)$ = posterior probability that material $M_i$ is in the formula, given evidence $E$
- $P(E | M_i)$ = likelihood of observing evidence $E$ if material $M_i$ is present
- $P(M_i)$ = prior probability of material $M_i$ being used (base rate)
- $P(E)$ = marginal probability of evidence $E$ (normalizing constant)

**Sequential updating for multiple evidence sources:**

Given evidence from $n$ independent sources $E_1, E_2, ..., E_n$:

$$P(M_i | E_1, E_2, ..., E_n) \propto P(M_i) \cdot \prod_{k=1}^{n} P(E_k | M_i)$$

**Practical example — Is hedione in Dior Sauvage?**

| Step | Evidence Source | Prior → Posterior |
|------|---------------|-------------------|
| 0 | Prior: hedione is in ~60% of modern masculines | P(hedione) = 0.60 |
| 1 | GC-MS study detects methyl dihydrojasmonate | P(hedione\|GC-MS+) ≈ 0.97 |
| 2 | Fragrantica users detect "jasmine radiance" | P(hedione\|GC-MS+, reviews) ≈ 0.98 |
| 3 | François Demachy (perfumer) mentions "jasmine petal" | P(hedione\|all) ≈ 0.99 |

**Setting prior probabilities $P(M_i)$ — base rates for aroma chemicals:**

These priors can be estimated from industry knowledge:

| Material Category | Est. Base Rate in Fine Fragrance |
|---|---|
| Hedione (methyl dihydrojasmonate) | 0.55–0.65 (present in majority of modern fragrances) |
| Iso E Super | 0.50–0.60 |
| Galaxolide (HHCB) | 0.40–0.50 |
| Ambroxan | 0.25–0.35 |
| Linalool (any source) | 0.70–0.80 |
| Benzyl salicylate | 0.45–0.55 |
| Coumarin | 0.30–0.40 |
| Cashmeran | 0.15–0.25 |
| Natural oakmoss | 0.05–0.10 (post-IFRA restriction) |
| Real oud oil | 0.01–0.03 (almost always synthetic) |

**Setting likelihood values $P(E_k | M_i)$ — how likely is evidence given material presence:**

| Evidence Type | If Material Present | If Material Absent |
|---|---|---|
| GC-MS peak matched in NIST library | 0.90–0.98 | 0.02–0.05 (false positive from co-elution) |
| EU allergen declared on packaging | 0.95 (above threshold) | 0.10 (could be below threshold) |
| Fragrantica note listed in official pyramid | 0.50–0.70 | 0.15–0.30 (marketing fiction) |
| >50% user reviews mention the note | 0.60–0.80 | 0.05–0.15 |
| Perfumer mentions material in interview | 0.85–0.95 | 0.01–0.05 |
| Patent example includes material | 0.40–0.60 | 0.20–0.35 (many patent examples, not all commercial) |

---

### 2.2 Dempster-Shafer Theory of Evidence

**Why it's useful here:** Unlike Bayesian inference, Dempster-Shafer (D-S) theory explicitly handles UNCERTAINTY and IGNORANCE — you can assign belief to "I don't know" rather than being forced to distribute probability across all hypotheses.

**Core concepts:**

**Frame of discernment** $\Theta$: The set of all possible materials
$$\Theta = \{M_1, M_2, ..., M_n\}$$

For a perfume with 130 candidate materials (a hobbyist's inventory), $\Theta$ has 130 elements.

**Mass function** $m: 2^\Theta \rightarrow [0, 1]$: Assigns belief to subsets of $\Theta$

$$m(\emptyset) = 0, \quad \sum_{A \subseteq \Theta} m(A) = 1$$

**Key advantage over Bayesian:** $m(\Theta)$ represents total ignorance — belief assigned to "could be anything."

**Belief and Plausibility bounds:**

$$\text{Bel}(A) \leq P(A) \leq \text{Pl}(A)$$

Where:
- $\text{Bel}(A) = \sum_{B \subseteq A} m(B)$ — minimum confidence that $A$ is true
- $\text{Pl}(A) = 1 - \text{Bel}(\bar{A}) = \sum_{B \cap A \neq \emptyset} m(B)$ — maximum plausibility

**Dempster's Rule of Combination** — fusing two independent evidence sources:

$$m_{1,2}(A) = \frac{1}{1 - K} \sum_{\substack{B \cap C = A \\ A \neq \emptyset}} m_1(B) \cdot m_2(C)$$

Where the **conflict factor** $K$ measures disagreement:

$$K = \sum_{B \cap C = \emptyset} m_1(B) \cdot m_2(C)$$

**Practical example — Is Cashmeran in a fragrance?**

Source 1 (GC-MS): No clear peak for Cashmeran CAS# 33704-61-9
$$m_1(\{\text{no Cashmeran}\}) = 0.70, \quad m_1(\Theta) = 0.30$$
(70% confident Cashmeran absent, 30% uncertain — maybe the GC conditions missed it)

Source 2 (User reviews): Multiple users describe "soft musky-woody" skin scent
$$m_2(\{\text{Cashmeran or Iso E Super or Galaxolide}\}) = 0.60, \quad m_2(\Theta) = 0.40$$
(60% confident it's one of these three "skin scent" materials, 40% uncertain)

Combining with Dempster's rule:
- The conflict $K$ between these sources is calculable
- The combined mass function narrows the uncertainty

**When to prefer D-S over Bayesian:**
- When evidence sources are truly independent and may be partially ignorant
- When you want to DISTINGUISH between "probably absent" and "no information"
- When combining fundamentally different evidence types (analytical chemistry vs. olfactive perception)

**When D-S has problems:**
- Zadeh's counter-example: When two sources strongly disagree, Dempster's rule can produce unintuitive results
- High conflict ($K > 0.7$) between sources suggests one source is unreliable — investigate rather than blindly combining
- Computational complexity grows exponentially with $|\Theta|$ — for 130 materials, pre-filtering is essential

---

### 2.3 Meta-Analysis / Inverse-Variance Weighting

**Core idea:** Treat each evidence source as a "study" and combine them using established statistical methods for research synthesis.

**Fixed-effect model:**

$$\hat{\theta} = \frac{\sum_{i=1}^{k} w_i \cdot \hat{\theta}_i}{\sum_{i=1}^{k} w_i}$$

Where:
- $\hat{\theta}_i$ = estimate from source $i$ (e.g., estimated concentration of material X)
- $w_i = 1 / \text{Var}(\hat{\theta}_i)$ = inverse-variance weight

**This assumes all sources estimate the SAME true value.** For perfume reconstruction, this is appropriate when:
- Multiple GC-MS analyses of the same batch give slightly different peak areas
- Multiple reviewers estimate longevity of a specific accord

**Random-effects model:**

$$w_i^* = \frac{1}{\text{Var}(\hat{\theta}_i) + \tau^2}$$

Where $\tau^2$ is the between-source heterogeneity variance. This is more appropriate when:
- Sources measure different ASPECTS of the same underlying formula
- GC-MS estimates proportions, while reviews estimate olfactive character — these are related but different measurements

**Practical variance estimates for each source type:**

| Source | Typical Variance (for concentration estimate) | Inverse-Variance Weight |
|---|---|---|
| Published GC-MS study | Low: σ² ≈ 0.5–2.0 | HIGH: w ≈ 0.5–2.0 |
| Patent example formula | Moderate: σ² ≈ 5.0–15.0 | MODERATE: w ≈ 0.07–0.20 |
| EU allergen declaration | Very wide: σ² ≈ 20.0–50.0 (presence only, no concentration) | LOW: w ≈ 0.02–0.05 |
| Expert perfumer interview | Moderate: σ² ≈ 8.0–20.0 | LOW-MOD: w ≈ 0.05–0.13 |
| Fragrantica consensus | High: σ² ≈ 25.0–100.0 | VERY LOW: w ≈ 0.01–0.04 |

---

### 2.4 Consensus Weighting / Wisdom-of-Crowds Approach

**Applicable specifically to community review data.**

**Condorcet Jury Theorem application:** If each reviewer has probability $p > 0.5$ of correctly identifying a note, then the majority vote converges to truth as the number of reviewers increases:

$$P(\text{majority correct}) = \sum_{k=\lceil n/2 \rceil}^{n} \binom{n}{k} p^k (1-p)^{n-k}$$

For $n = 100$ reviewers with individual accuracy $p = 0.55$:
$$P(\text{majority correct}) \approx 0.84$$

For $n = 500$ reviewers with $p = 0.55$:
$$P(\text{majority correct}) \approx 0.99$$

**Fragrantica typically has 100–5000+ reviews per mainstream fragrance** — this makes consensus extraction statistically powerful despite low individual accuracy.

**Calibration factors for crowd note detection:**

| Note Category | Individual Detection Accuracy | Required Consensus Threshold |
|---|---|---|
| Strong top notes (citrus, mint) | p ≈ 0.70–0.85 | ≥40% of reviews |
| Obvious heart notes (rose, jasmine) | p ≈ 0.60–0.75 | ≥35% of reviews |
| Abstract molecular notes (Iso E Super, ambroxan) | p ≈ 0.25–0.40 | ≥15% of reviews (often UNNAMED) |
| Base notes (musk, amber, sandalwood) | p ≈ 0.50–0.65 | ≥25% of reviews |
| Green/herbal specific (galbanum vs. violet leaf) | p ≈ 0.20–0.35 | ≥10% of reviews |

---

### 2.5 Corroboration Value — When Multiple Sources Agree

**The most powerful reconstruction signal is corroboration across independent evidence types.**

**Corroboration scoring matrix:**

| Evidence Combination | Joint Confidence Multiplier | Example |
|---|---|---|
| GC-MS + allergen declaration | ×1.8–2.2 | Linalool peak confirmed by INCI listing |
| GC-MS + perfumer interview | ×2.0–2.5 | Hedione peak + perfumer says "jasmine radiance" |
| GC-MS + patent formula | ×2.2–2.8 | Same material in both analytical and disclosed data |
| Allergen declaration + user reviews | ×1.3–1.6 | Coumarin listed + users detect "hay/tonka" |
| Patent + perfumer interview | ×1.5–2.0 | Patent lists material + perfumer confirms use |
| 3+ independent sources agree | ×3.0–4.0 | Convergence across analytical, regulatory, perceptual |

**Anti-corroboration (contradiction):**
- If GC-MS shows NO linalool but it's listed on INCI → likely present below GC detection limit OR present via a natural that GC didn't fully resolve
- If patent lists a material but GC-MS doesn't detect it → patent may describe a different formula or a precursor composition
- If users strongly detect a note but no analytical evidence supports it → likely an olfactive illusion from synergy (e.g., "peach" from lactones + Iso E Super, not from any actual peach material)

---

## 3. Perfumery-Specific Reconstruction Methods

### 3.1 Olfactive Descriptor → Chemical Identity Mapping

**This is the central challenge:** translating subjective smell descriptions into probable chemical identities.

**High-confidence mappings (descriptor → material class → specific candidates):**

| Olfactive Descriptor | Material Class | Specific Candidates (with confidence) |
|---|---|---|
| "Powdery iris" | Ionones, orris materials | Alpha-Isomethyl Ionone (0.85), Alpha-Irone (0.60), Orris butter (0.15) |
| "Clean musk" | Synthetic macrocyclic/polycyclic musks | Galaxolide (0.40), Ethylene Brassylate (0.25), Habanolide (0.15), Muscenone (0.10) |
| "Woody-amber warmth" | Amber woods | Iso E Super (0.45), Ambroxan (0.30), Cashmeran (0.15) |
| "Jasmine radiance" | Jasmonates | Hedione (0.75), Hedione HC (0.15), cis-Jasmone (0.05) |
| "Soapy-clean" | Aldehydes + salicylates | Benzyl salicylate + C10/C11/C12 aldehydes (0.70) |
| "Green-leafy" | Green chemicals | cis-3-Hexenol (0.30), Galbanum (0.20), Violet leaf abs. (0.20) |
| "Smoky-leathery" | Phenolic/tar materials | Birch tar (0.25), Guaiacol (0.20), Castoreum reconstitution (0.15), Isobutyl quinoline (0.20) |
| "Metallic-ozonic" | Ozone chemicals | Calone (0.30), Scentenal (0.20), Helional (0.20) |
| "Creamy sandalwood" | Sandalwood synthetics | Bacdanol (0.30), Javanol (0.25), Ebanol (0.20), Sandalore (0.15) |
| "Transparent bergamot" | FCF bergamot or synthetic | Bergamot FCF (0.60), Linalyl acetate + limonene blend (0.25) |
| "Fruity-tropical" | Tropical fruit chemicals | Paradisamide (0.20), Damascone delta (0.15), Stemone (0.15), Methyl pamplemousse (0.10) |

**Important ambiguity zones — multiple material classes produce indistinguishable descriptors:**

1. **"Woody"** could be: cedarwood EO, Iso E Super, Cashmeran, Vertofix, Timberol, Javanol, Ebanol, Koavone, or a vetiver derivative. GC-MS is ESSENTIAL to disambiguate.

2. **"Musky"** could be: Galaxolide, Ethylene Brassylate, Habanolide, Muscone, Exaltone, nitro musks (historical), or Ambrette seed musk. The olfactive character varies dramatically between classes but untrained noses conflate them.

3. **"Amber"** could be: Ambroxan (crystalline-mineral), Labdanum (dark-resinous), Ambrettolide (clean-animalic), synthetic Ambergris accords, vanilla-benzoin-labdanum blends. This word is nearly meaningless without further qualification.

### 3.2 Accord Architecture Analysis

**Method:** Instead of identifying individual materials, identify the ACCORD STRUCTURE first, then fill in specific materials.

**The 7 canonical accord architectures:**

1. **Citrus-aromatic (Cologne/Eau Fraîche):** Citrus EOs + lavender/rosemary + light musk
   - Materials: 3–5 materials, simple structure
   - Reconstruction difficulty: LOW

2. **Floral bouquet:** Rose + jasmine + muguet synthetics + salicylate cushion
   - Materials: 8–15 materials
   - Reconstruction difficulty: MODERATE

3. **Chypre:** Bergamot + oakmoss/Evernyl + labdanum + patchouli
   - Materials: 10–20 materials
   - Reconstruction difficulty: MODERATE-HIGH (oakmoss alternatives are the challenge)

4. **Fougère:** Lavender + coumarin + geranium/oakmoss + musk
   - Materials: 8–15 materials
   - Reconstruction difficulty: MODERATE

5. **Oriental/Amber:** Vanilla + benzoin/labdanum + spices + amber woods
   - Materials: 12–25 materials
   - Reconstruction difficulty: MODERATE

6. **Woody-molecular:** Iso E Super / ambroxan-heavy structures with minimal decoration
   - Materials: 3–8 materials but at specific RATIOS
   - Reconstruction difficulty: LOW (materials) but HIGH (ratios — small changes drastically alter character)

7. **Gourmand:** Ethyl maltol + vanillin + lactones + coumarin + musk
   - Materials: 8–15 materials
   - Reconstruction difficulty: LOW-MODERATE

**Diagnostic tests for accord identification:**

| Test | Method | Identifies |
|---|---|---|
| Spray on paper, smell at 30 seconds | Top note analysis | Citrus type, aldehyde presence, green notes |
| Smell at 30 minutes | Heart emergence | Floral class, spice presence, aromatic character |
| Smell at 4+ hours | Base structure | Woody type, musk class, amber system |
| Spray on skin vs. paper | Skin chemistry interaction | Musk character (skin-reactive vs. air-projecting) |
| Compare with known reference | Triangulation | "Smells like X but with more Y" → structural insight |

### 3.3 Concentration Estimation from Olfactive Intensity

**This is speculative but directionally useful.**

**General intensity-to-concentration mapping:**

| Olfactive Impact Level | Typical Concentration in Concentrate | Confidence |
|---|---|---|
| "This IS the perfume" — dominant character | 15–30% of concentrate | ±50% (wide range) |
| "Strong supporting role" — clearly present | 5–15% of concentrate | ±40% |
| "Detectable modifier" — adds character | 1–5% of concentrate | ±50% |
| "Barely there but contributes" — trace | 0.1–1% of concentrate | ±60% |

**Material-specific impact thresholds (detection thresholds in air):**

| Material | Odor Detection Threshold in Air | Implication |
|---|---|---|
| Iso E Super | ~0.4 ppb — VERY low | Even trace amounts project significantly |
| Ambroxan | ~0.3 ppb — VERY low | Dominates drydown even at 1–3% |
| Hedione | ~5 ppb — moderate | Needs higher concentration (15–30%) for "radiance" effect |
| Benzyl salicylate | ~50 ppb — moderate | Present at high concentration but olfactively subtle |
| Galaxolide (HHCB) | ~1.5 ppb — low | Projects as "clean" at moderate concentrations |
| Coumarin | ~20 ppb — moderate | Detectable as "hay/tonka" at 1–3% |
| Ethyl vanillin | ~0.005 ppb — EXTREMELY low | Tiny amounts create strong vanilla |
| Guaiacol | ~3 ppb — low | Very powerful — trace amounts create "smoky" |

---

## 4. Technical Implementation Considerations

### 4.1 Data Structures for Probabilistic Material Identification

**Recommended representation — Material Evidence Record:**

```
MaterialCandidate {
    name: string                           // "Hedione"
    cas_number: string                     // "24851-98-7"  
    olfactive_class: string[]              // ["jasmine", "radiance", "fresh-floral"]
    
    // Evidence accumulation
    prior_probability: float               // Base rate: 0.60
    posterior_probability: float            // After evidence: 0.97
    
    // Source-specific evidence
    evidence_sources: [
        {source: "GC-MS", confidence: 0.95, data: "peak at RT 23.4 min, match factor 92%"},
        {source: "EU_allergen", confidence: 0.0, data: "not a listed allergen"},
        {source: "Fragrantica", confidence: 0.65, data: "72% of users detect jasmine radiance"},
        {source: "perfumer_interview", confidence: 0.90, data: "Demachy mentions jasmine petal"},
        {source: "patent", confidence: 0.40, data: "US2015/0238425A1 Example 3"}
    ]
    
    // Concentration estimate
    concentration_estimate: {
        mean: float,                       // 18.5% of concentrate
        lower_bound: float,                // 10.0%
        upper_bound: float,                // 30.0%
        ifra_maximum: float                // No IFRA limit for hedione
    }
    
    // Reconstruction confidence
    overall_confidence: float              // 0.97 (near certain present)
    concentration_confidence: float        // 0.45 (uncertain about exact amount)
}
```

### 4.2 Evidence Integration Pipeline

**Recommended processing order (from most reliable to least):**

```
Stage 1: GC-MS data ingestion (if available)
    → Candidate list with high-confidence identifications
    → Approximate relative proportions
    
Stage 2: EU allergen/INCI verification
    → Confirm/deny presence of 26+ allergens
    → Narrow candidate list for natural vs. synthetic sources
    
Stage 3: Patent cross-reference
    → Search by company + material CAS numbers from Stage 1
    → If patent formula found, use as PRIOR for concentration estimates
    
Stage 4: IFRA ceiling application
    → Apply maximum concentration limits
    → Eliminate impossible formulations
    
Stage 5: Community consensus extraction
    → Extract Fragrantica/Basenotes note votes
    → Weight by reviewer expertise
    → Fill in GAPS — materials not detected by GC-MS (non-volatile musks, macrocyclics)
    
Stage 6: Perfumer disclosure integration
    → Search interviews for material mentions
    → Update posteriors for mentioned materials
    
Stage 7: Accord architecture validation
    → Does the assembled formula make SENSE as a perfume?
    → Are the proportions within professional norms?
    → Does the top/heart/base structure match temporal descriptions?
    
Stage 8: Iterative refinement
    → Compound the formula at estimated concentrations
    → Compare to target perfume
    → Adjust based on olfactive comparison
```

### 4.3 Conflict Resolution Between Sources

**When sources disagree, apply this hierarchy:**

1. **GC-MS > all other sources** for material identification (detection is chemical fact)
2. **IFRA limits > estimated concentrations** (regulatory ceiling is absolute)
3. **EU allergen declaration > user reviews** for presence/absence of listed allergens
4. **Patent formulas > user estimates** for concentration ranges
5. **Expert perfumer > crowd consensus** for material class identification
6. **Crowd consensus > individual reviewer** for olfactive character

**Conflict detection threshold:** If two sources disagree with combined confidence > 0.7, flag for manual review rather than attempting automatic resolution.

### 4.4 Confidence Normalization and Reporting

**Three-tier confidence system:**

| Level | Range | Meaning | Action |
|---|---|---|---|
| **CONFIRMED** | P ≥ 0.85 | Material almost certainly present/absent | Include in reconstruction at estimated concentration |
| **PROBABLE** | 0.50 ≤ P < 0.85 | More likely than not, but not certain | Include with wide concentration range; test variants |
| **SPECULATIVE** | P < 0.50 | Possible but unconfirmed | Create variant formulations with/without this material |

**For a reconstruction to be considered "actionable," it should have:**
- ≥ 80% of total formula mass assigned to CONFIRMED materials
- ≤ 15% of formula mass in PROBABLE materials
- ≤ 5% of formula mass in SPECULATIVE materials

### 4.5 Practical Workflow for a Hobbyist Perfumer

**Step 1: Initial Intelligence Gathering (1–2 hours)**
- Search Fragrantica for: notes pyramid, accords chart, user reviews, similar fragrances
- Search Basenotes forums for: analytical discussions, "what's in this?" threads
- Check product packaging for: EU allergen declarations
- Google "[perfume name] + ingredients" or "[perfume name] + INCI"
- Google "[perfume name] + GC-MS" or "[brand] + patent"

**Step 2: Hypothesis Formation (30 minutes)**
- Determine accord family (chypre? fougère? oriental? woody-molecular?)
- List 5–10 "almost certain" materials based on allergen list + accord family
- List 5–10 "probable" materials based on user reviews + perfumer interviews
- List 3–5 "speculative" materials that would explain unusual notes

**Step 3: Prior Formula Draft (1 hour)**
- Build a hypothetical formula hitting the identified accord architecture
- Use published formulation norms for the accord type as concentration guide:
  - Hedione: 15–25% for "radiance" effect
  - Iso E Super: 10–20% for "molecular" effect
  - Musks: 5–15% total musk blend
  - Featured natural EOs: 3–8% each
  - Top notes: 8–15% total (citrus, green, fresh)
  - Modifiers/trace: 0.1–2% each
  - Fixatives (benzyl salicylate, etc.): 5–15%

**Step 4: Compound and Compare (ongoing)**
- Make a 10 mL test batch
- Compare side-by-side with target on blotter strips
- Note discrepancies and adjust:
  - "Too sweet" → reduce vanilla/ethyl maltol, increase woody/dry materials
  - "Missing radiance" → increase Hedione or add a salicylate
  - "Too heavy/dark" → lighten base, increase citrus/green
  - "Wrong texture" → check musk blend, salicylate ratio
  - "Opening is right but drydown diverges" → base note materials need revision

**Step 5: Iterate (per adjustment cycle ~30 minutes)**
- Make targeted 1–2 material changes per iteration
- Keep detailed notes on what changed and what improved
- After 5–10 iterations, you will converge on a "credible reconstruction" — not an exact duplicate, but an accord that captures the essential character

---

## Appendix A: Source Reliability Summary Table

| Source | Confidence Range | Best For | Worst For |
|---|---|---|---|
| GC-MS analysis | 0.85–0.98 | Identifying specific chemicals | Non-volatiles, exact concentrations |
| EU allergen declaration | 0.80–0.95 (presence) | Confirming listed allergens | Non-allergen materials, concentration |
| IFRA standards | 0.80–0.90 (ceiling) | Maximum possible dose | What IS present, actual dose |
| Patent formulas | 0.40–0.75 | Concentration ranges, material combinations | Matching to specific commercial products |
| Perfumer interviews | 0.40–0.70 | Key character materials | Exact concentrations, full formula |
| Fragrantica consensus | 0.45–0.65 (aggregate) | Accord character, note detection | Specific material identification |
| Individual user review | 0.15–0.35 | Nothing in isolation | Everything in isolation |
| Brand marketing notes | 0.20–0.40 | "Hero" ingredient identification | Formula accuracy, supporting materials |

## Appendix B: Key Reference Numbers

- **Typical fine fragrance:** 30–80 individual aroma chemicals
- **Typical concentrate strength:** 10–20% in EdP, 5–15% in EdT
- **Number of commercially available aroma chemicals:** ~3,000 (major suppliers catalog)
- **Number commonly used by any single house:** 500–1,500
- **Number in a hobbyist inventory:** 50–200 (your inventory: ~130)
- **Materials contributing >1% each to a typical formula:** 8–15
- **Materials contributing <0.5% each:** 15–30 (modifiers, blenders, trace effects)
- **GC-MS identification accuracy (NIST match):** >90% for match factor ≥85
- **Time for a trained perfumer to "decode" a competitor's fragrance:** 2–8 hours (per Calkin & Jellinek, 1994)
- **Time for GC-MS complete analysis:** 30–90 minutes instrument time + 2–8 hours data interpretation
- **EU mandatory allergen disclosure threshold:** 0.001% (leave-on), 0.01% (rinse-off)
- **IFRA 50th Amendment:** Published January 2022, covers ~180 materials across 11 product categories

## Appendix C: Recommended Reading

1. **Calkin, R.R. & Jellinek, J.S. (1994).** *Perfumery: Practice and Principles.* Wiley. — Chapter on reverse engineering; authoritative industry source; quote: "anyone armed with good GC/MS equipment and experienced in using this equipment can today, within days, find out a great deal about the formulation of any perfume"
2. **Burr, Chandler (2003).** *The Emperor of Scent.* Random House. — Readable account of perfume composition and analysis
3. **Ellena, Jean-Claude (2011).** *Perfume: The Alchemy of Scent.* Arcade. — Perfumer's perspective on construction
4. **Surburg, H. & Panten, J. (2006).** *Common Fragrance and Flavor Materials.* Wiley. — Chemical reference for aroma materials
5. **Arctander, Steffen (1969).** *Perfume and Flavor Chemicals.* Self-published. — 2-volume encyclopedia of 3,000+ materials with olfactive descriptions. Still the definitive reference.
6. **NIST Chemistry WebBook** (webbook.nist.gov) — Free access to mass spectra for compound identification

---

*This report is research only — a synthesis of publicly available information on methods for analyzing and reconstructing perfume compositions from multiple evidence sources. It provides the theoretical framework and practical guidance for evidence-based perfume reconstruction.*
