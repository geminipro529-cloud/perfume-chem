# From-Scratch Reconstruction Addendum

## When no ranked identity roster or formula hypothesis exists

This addendum extends the Universal Non-Compressed Perfume Reconstruction Protocol to perfumes for which only official notes, labels, public descriptions, family context, and physical reference samples are available.

The authority ceiling is lower than a reconstruction supported by a detailed identity roster or calibrated analytical data. The method must therefore produce an **ensemble of explicit hypotheses**, not one falsely exact formula.

---

## 1. Lock the exact reference

Record:

- brand and exact product;
- concentration;
- bottle and label version;
- market;
- batch code;
- approximate production date;
- storage and opening history;
- and known reformulation boundaries.

Do not combine EDT, EDP, Parfum, Intense, Absolu, and later reformulations as one target.

---

## 2. Build a documentary evidence matrix

Collect only attributable claims.

### Official product data

Extract:

- fragrance family;
- named notes;
- composition narrative;
- ingredient list;
- allergens;
- launch and reformulation data;
- perfumer attribution where officially documented;
- sibling-flanker descriptions.

### Independent but secondary data

Record separately:

- retailer note lists;
- interviews;
- patents;
- supplier demo formulas;
- historical reviews;
- and public databases.

### Evidence status

Every claim receives:

- source class;
- date;
- reference version;
- presence confidence;
- and whether it constrains identity, function, or only perception.

---

## 3. Translate note language into functional constraints

A note is not automatically an ingredient.

For each note, define:

```json
{
  "note": "iris",
  "required_facets": [
    "powder",
    "violet",
    "root",
    "cosmetic",
    "dry wood"
  ],
  "time_windows": ["heart","drydown"],
  "candidate_functions": [
    "ionone body",
    "orris diffusion",
    "powder bridge",
    "woody handoff"
  ],
  "forbidden_drift": [
    "lipstick dominant",
    "sweet violet candy"
  ]
}
```

This creates a search space without pretending the note reveals the commercial raw materials.

---

## 4. Use label evidence carefully

Declared allergens may support the presence of:

- free aroma chemicals;
- natural-material constituents;
- reaction or oxidation products;
- or components of a premade base.

Do not automatically add every allergen as an independent neat material.

Use the label to constrain candidate families and lower bounds only under the applicable labeling rules and product version.

---

## 5. Build the family graph

Construct a graph of official note functions and likely transitions.

Example for a clean iris fougere:

```text
citrus / neroli
      |
aromatic ester lift
      |
soap / muguet air
      |
iris / violet body
      |
pepper / geranium / patchouli
      |
cedar / amber / clean musks
```

The graph exposes missing hand-offs that a simple note list hides.

---

## 6. Use sibling flankers as differential evidence

Sibling products can act as a natural experiment.

For products \(P_1...P_n\):

\[
G_{shared} = \bigcap_j G(P_j)
\]

where \(G(P_j)\) is the functional graph of flanker \(j\).

Repeated functions across siblings are evidence for family DNA, not proof of identical materials or percentages.

Differences identify candidate module regions.

Avoid circular reasoning: marketing copy may repeat house language even where the formula changed.

---

## 7. Generate candidate material families

For every required role, create a candidate set.

Example:

```json
{
  "role": "powdery iris body",
  "candidates": [
    "Methyl Ionone Gamma Coeur",
    "Isoraldeine 95",
    "Alpha Isomethyl Ionone",
    "Dihydro Alpha Ionone",
    "Dihydro Beta Ionone",
    "orris natural or base",
    "UNKNOWN_IRIS_CAPTIVE_01"
  ]
}
```

Do not choose one material immediately. Preserve alternatives and unknown nodes.

---

## 8. Add analytical evidence when possible

### Direct injection GC-MS/FID

Useful for:

- major volatile and semivolatile composition;
- solvent and carrier;
- abundant musks;
- woods;
- naturals;
- and approximate mass balance.

### HS-SPME-GC-MS

Use multiple timepoints and extraction conditions. Headspace is condition-dependent and does not directly equal formula percentage.

### GC-olfactometry

Prioritize peaks that actually carry odor identity, including small or coeluted peaks.

### GCxGC, chiral GC, LC-MS, NMR

Use where coelution, stereochemistry, high-boiling material, naturals, or proprietary mixtures justify it.

Unknown peaks remain unknown nodes.

---

## 9. Build quantity priors

Without a roster, combine:

- analytical peak estimates;
- functional role priors;
- family-era priors;
- official-note constraints;
- allergen evidence;
- cost/manufacturing plausibility;
- and sensory recombination.

Represent each amount as a distribution:

\[
\log q_i \sim \mathcal{N}(\mu_i,\sigma_i^2)
\]

Do not collapse broad uncertainty into a precise microlitre amount without labeling it as a bench center.

---

## 10. Generate an ensemble

Create multiple complete candidate formulas.

Vary:

- material identity alternatives;
- block budgets;
- accord ratios;
- response factors;
- natural composition;
- and trace intensity.

Each ensemble member must remain complete. Do not create sparse candidates merely because optimization prefers fewer variables.

Report:

- median amount;
- credible interval;
- inclusion probability;
- and source confidence.

---

## 11. Recombination testing

Build:

1. central candidate;
2. iris system low/high;
3. soap-muguet system low/high;
4. pepper-geranium-patchouli system low/high;
5. musk architecture alternatives;
6. wood/amber alternatives;
7. candidate unknown replacements.

Evaluate blind against the exact retail reference through time.

Use omission tests to determine whether detail rows earn their place.

---

## 12. Chassis derivation from a from-scratch target

Do not design the chassis until one target ensemble member has become the accepted working center.

For uncertain target rows:

- protect central unknown functions if they appear essential;
- avoid moving low-confidence unknowns into the socket unless flanker evidence suggests mobility;
- give the chassis a wider uncertainty envelope;
- and require a stronger sensory gate.

The chassis report must state that parent recombination is exact relative to the **working hypothesis**, not relative to a proprietary commercial formula.

---

## 13. Authority label

Suggested labels:

- `TIER_0_NOTE_INSPIRED`
- `TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS`
- `TIER_2_SENSORY_RECOMBINATION_HYPOTHESIS`
- `TIER_3_ANALYTICALLY_CONSTRAINED`
- `TIER_4_QUANTITATIVELY_CALIBRATED`
- `TIER_5_BLIND_SENSORY_VALIDATED`
- `TIER_6_AUTHENTICATED_FORMULA`

The Prada L'Homme case study in this suite is Tier 1-2. Its 54 rows are a structured, testable center hypothesis, not a recovered commercial formula.

---

## 14. Additional hard gates

Fail when:

- official notes are treated as literal ingredient disclosures;
- review-site consensus replaces evidence;
- sibling flankers are copied into the parent;
- allergens become independent ingredients without provenance;
- every unknown is forced into a catalog material;
- one formula is generated without an alternative ensemble;
- or the final precision exceeds the evidence authority.

The purpose of from-scratch reconstruction is not to sound certain. It is to make uncertainty testable.
