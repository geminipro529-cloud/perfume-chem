# QSAR: Quantitative Structure-Activity Relationship in Fragrance

## Overview
This document covers computational methods for predicting odor properties from molecular structure, including descriptor calculation, model building, and practical applications for fragrance discovery and optimization.

---

## 1. Fundamental QSAR Concepts

### 1.1 Core Principle

**QSAR attempts to find mathematical relationships:**
```
Biological Activity = f(Molecular Structure)
```

In fragrance:
```
Odor Property = f(Molecular Descriptors)
```

**Types of predictions:**
- **Qualitative:** Odor character (floral, woody, fruity)
- **Quantitative:** Odor threshold, intensity, hedonics
- **Similarity:** Distance to known reference compounds

### 1.2 QSAR Workflow

```
1. Compile training dataset (molecules + odor data)
2. Calculate molecular descriptors
3. Feature selection (identify relevant descriptors)
4. Build predictive model (regression, classification, ML)
5. Validate model (test set, cross-validation)
6. Apply to novel molecules (virtual screening, design)
```

### 1.3 Limitations

**Challenges unique to olfaction:**
- **Chirality matters:** (R)-carvone = spearmint, (S)-carvone = caraway
- **Concentration-dependent:** Indole (low = floral, high = fecal)
- **Mixture effects:** Synergy, masking (non-additive)
- **Receptor promiscuity:** Same molecule activates multiple receptors
- **Subjective perception:** Cultural/learned differences

**QSAR works best for:**
- Odor threshold prediction
- Structural class identification (terpene, aldehyde, etc.)
- "Smells like X" similarity ranking

**QSAR struggles with:**
- De novo character prediction (without training examples)
- Mixture perception
- Hedonic quality (cultural/personal)

---

## 2. Molecular Descriptors

### 2.1 Constitutional Descriptors (0D)

**Simple counts:**

| Descriptor | Symbol | Example (Linalool C₁₀H₁₈O) |
|------------|--------|----------------------------|
| Molecular weight | MW | 154.25 g/mol |
| Number of atoms | nAT | 29 |
| Number of carbons | nC | 10 |
| Number of oxygens | nO | 1 |
| Number of H-bond donors | nHD | 1 (OH) |
| Number of H-bond acceptors | nHA | 1 (O) |
| Number of rings | nRing | 0 |
| Number of rotatable bonds | nRB | 5 |

**Applications:**
- MW correlates with volatility (lower MW = higher volatility)
- nHD/nHA relate to hydrogen bonding (affects solubility, receptor binding)

### 2.2 Topological Descriptors (2D)

**Graph-based:**

**Wiener index (W):**
- Sum of all shortest-path distances between atoms
- Higher W = larger, more branched molecule

**Molecular connectivity indices (χ):**
```
χ = Σ(1/√δᵢδⱼ)
```
Where δ = vertex degree (number of bonds)

**Applications:**
- Correlates with boiling point, VP
- Discriminates isomers (same formula, different structure)

**Example:**
- n-Hexane (linear): χ⁰ = 3.414
- 2-Methylpentane (branched): χ⁰ = 3.270
- Different odors despite same MW

### 2.3 Geometric Descriptors (3D)

**Shape-based:**

**Molecular volume (Vm):**
- 3D space occupied
- Calculated from van der Waals radii

**Molecular surface area (MSA):**
- Solvent-accessible surface
- Correlates with hydrophobicity

**Principal moments of inertia (I₁, I₂, I₃):**
- Describes shape (rod-like, spherical, disc-like)

**Shape indices:**
```
Asphericity = (I₃ - 0.5(I₁ + I₂))
```

**Applications:**
- Receptor binding (shape complementarity)
- Woody vs. floral (different 3D shapes)

### 2.4 Electronic Descriptors

**Charge distribution:**

**Dipole moment (μ):**
- Measure of polarity
- Higher μ = more polar

**Partial charges (qᵢ):**
- Atom-specific charge (calculated via quantum mechanics)
- Identifies electron-rich/poor sites (receptor interaction)

**HOMO/LUMO energies:**
- **HOMO (Highest Occupied Molecular Orbital):** Electron donor capability
- **LUMO (Lowest Unoccupied Molecular Orbital):** Electron acceptor capability
- **HOMO-LUMO gap:** Reactivity, stability

**Electrostatic potential (ESP):**
- 3D map of charge distribution
- Predicts binding sites

### 2.5 Physicochemical Descriptors

**Partition coefficients:**

**log P (octanol/water):**
- Lipophilicity measure
- High log P = lipophilic (prefers organic phase)
- Low log P = hydrophilic

**Example values:**
- Limonene: log P = 4.45 (very lipophilic)
- Linalool: log P = 2.97 (moderately lipophilic)
- Vanillin: log P = 1.37 (moderately hydrophilic)

**Applications:**
- Predicts solubility, skin penetration
- Correlates with receptor access (through mucus)

**Other:**
- **pKa:** Acid/base strength
- **Solubility (S):** Water solubility
- **Vapor pressure (VP):** Volatility

---

## 3. Structure-Odor Relationships

### 3.1 Functional Group Trends

**Common associations (not absolute rules!):**

| Functional Group | Typical Odor Character | Examples |
|------------------|------------------------|----------|
| **Aldehyde (C=O at chain end)** | Green, fatty, citrus, floral | Hexanal (green), citral (lemon), benzaldehyde (almond) |
| **Alcohol (OH)** | Floral, rosy, fresh | Linalool (lavender), geraniol (rose), phenylethyl alcohol (rose) |
| **Ester (COO)** | Fruity, sweet | Benzyl acetate (fruity), linalyl acetate (bergamot) |
| **Ketone (C=O internal)** | Fruity, minty, woody | Carvone (mint), ionone (violet), muscone (musk) |
| **Lactone (cyclic ester)** | Creamy, peachy, coconut | γ-Decalactone (peach), δ-Decalactone (coconut) |
| **Ether** | Anisic, sweet | Anethole (anise), eugenol methyl ether |
| **Phenol (aromatic OH)** | Smoky, medicinal, spicy | Eugenol (clove), guaiacol (smoke) |
| **Thiol/Sulfide (SH, S)** | Sulfurous, garlicky (high); fruity (low) | Grapefruit mercaptan (grapefruit), dimethyl sulfide (DMS) |

**Caveat:** Context (rest of molecule) matters immensely!

### 3.2 Carbon Chain Length Effects

**Homologous series: Aliphatic aldehydes**

| Carbon # | Name | Odor | ODT (ppm) |
|----------|------|------|-----------|
| C6 | Hexanal | Green, grassy, fatty | 0.005 |
| C7 | Heptanal | Fatty, rancid, citrus | 0.003 |
| C8 | Octanal | Citrus, orange peel, fatty | 0.0007 |
| C9 | Nonanal | Waxy, citrus, floral | 0.001 |
| C10 | Decanal | Soapy, waxy, orange | 0.001 |
| C11 | Undecanal | Soapy, aldehydic, citrus | 0.002 |
| C12 | Dodecanal (Lauric) | Soapy, waxy, floral | 0.004 |

**Trends:**
- **Short chain (C4-C6):** Pungent, sharp, "green"
- **Medium chain (C7-C10):** Citrus, floral
- **Long chain (C12+):** Soapy, waxy, mild

**Volatility:** Decreases with chain length (higher MW, lower VP)

### 3.3 Branching Effects

**Linear vs. branched:**

**Example: C₁₀H₁₆ (Monoterpenes)**

| Molecule | Structure | Odor |
|----------|-----------|------|
| **α-Pinene** | Bicyclic, bridged | Pine, turpentine, sharp |
| **Limonene** | Monocyclic | Orange, citrus, fresh |
| **Linalool** | Acyclic, branched, OH | Lavender, floral, sweet |
| **Geraniol** | Acyclic, branched, OH | Rose, citrus, sweet |

**General:** More branching → less "sharp," more "rounded" odor.

### 3.4 Chirality (Stereoisomers)

**Same formula, different 3D arrangement:**

| Molecule | Enantiomer | Odor |
|----------|------------|------|
| **Carvone** | (R)-(-) | Spearmint |
| | (S)-(+) | Caraway |
| **Limonene** | (R)-(+) | Orange |
| | (S)-(-) | Lemon (pine-like) |
| **Linalool** | (R)-(-) | Lavender, woody |
| | (S)-(+) | Sweet, floral (petitgrain) |
| **Rose oxide** | (S)-(+) (cis) | Rose, green, intense |
| | (R)-(-) (cis) | Weaker, earthy |

**Explanation:** Different enantiomers bind differently to chiral receptor binding pockets → activate different receptors → different perceived odor.

**QSAR challenge:** Must use 3D descriptors that capture chirality.

---

## 4. QSAR Model Types

### 4.1 Linear Regression Models

**General form:**
```
Activity = β₀ + β₁(Descriptor₁) + β₂(Descriptor₂) + ... + βₙ(Descriptorₙ)
```

**Example: Odor threshold prediction**
```
log(1/ODT) = 2.5 - 0.8(log P) + 1.2(Polar Surface Area) - 0.05(MW)
```

**Interpretation:**
- Higher log P (lipophilicity) → lower ODT (more potent)
- Higher PSA (polarity) → higher ODT (less potent)
- Higher MW → lower ODT (less volatile)

**Advantages:**
- Interpretable coefficients
- Fast computation

**Limitations:**
- Assumes linear relationships (rarely true)
- Poor with complex, non-linear effects

### 4.2 Non-Linear Models (Polynomial, SVM)

**Polynomial regression:**
```
Activity = β₀ + β₁(D₁) + β₂(D₁²) + β₃(D₁ × D₂) + ...
```

**Support Vector Machine (SVM):**
- Maps data to high-dimensional space
- Finds optimal separating hyperplane
- Good for classification (floral vs. woody vs. fruity)

### 4.3 Machine Learning (Random Forest, Neural Networks)

**Random Forest:**
- Ensemble of decision trees
- Each tree votes on classification/prediction
- Robust, handles non-linearity well

**Example application:**
- Input: 100+ molecular descriptors
- Output: Probability of "floral" character
- Training: 5000 molecules with labeled odor

**Neural Networks (Deep Learning):**
- Multiple layers of nonlinear transformations
- Can learn complex patterns
- Requires large datasets (>10,000 molecules)

**Current state:**
- Limited by small odor databases (~5000 annotated molecules)
- Google/IBM working on larger datasets + deep learning

### 4.4 Similarity-Based Models (k-NN, Tanimoto)

**k-Nearest Neighbors (k-NN):**
```
Odor of unknown molecule ≈ Average odor of k most similar known molecules
```

**Tanimoto coefficient (molecular fingerprint similarity):**
```
T = (Bits in common) / (Total bits in either)
```

**Example:**
- Unknown molecule X
- Find 5 most similar molecules in database (via Tanimoto)
- If 4/5 smell "woody," predict X = "woody"

**Advantage:** Simple, interpretable, works with small datasets

**Disadvantage:** Requires good reference database

---

## 5. Molecular Fingerprints

### 5.1 Bit Vector Fingerprints

**Concept:** Encode structure as binary vector (presence/absence of substructures)

**MACCS keys (166 bits):**
- Each bit = specific structural feature
- Bit 42 = "Contains aromatic hydroxyl"
- Bit 89 = "Contains ester group"
- Example: Benzyl acetate = [0,0,1,0,0,...,1,0,1] (166 bits)

**Extended-Connectivity Fingerprints (ECFP):**
- Circular fingerprints around each atom
- ECFP4 (radius 2), ECFP6 (radius 3)
- Captures local environment

**Applications:**
- Fast similarity searching (Tanimoto coefficient)
- Classification (floral/woody/etc.)

### 5.2 Pharmacophore Models

**Definition:** 3D arrangement of key features (H-bond donor, acceptor, hydrophobic, aromatic)

**Example: "Musky" pharmacophore**
- Requirement: Large hydrophobic region (~15-17 Å)
- Optional: Ketone or lactone (electron withdrawing)
- Examples: Muscone, Galaxolide, Tonalide

**Use:** Screen libraries for molecules matching pharmacophore → predict "musky" character.

---

## 6. Receptor-Based QSAR (Docking)

### 6.1 Homology Modeling of ORs

**Challenge:** No crystal structures of odorant receptors (yet).

**Approach:**
1. Use related GPCR structures (e.g., β2-adrenergic receptor)
2. Build homology model of OR based on sequence alignment
3. Refine with molecular dynamics

**Accuracy:** Moderate (ORs are distant from solved GPCRs)

### 6.2 Molecular Docking

**Process:**
1. Prepare receptor (OR homology model)
2. Prepare ligand (odorant molecule)
3. Dock ligand into binding pocket
4. Score binding affinity (ΔG)

**Scoring functions:**
```
ΔG_bind = ΔG_vdW + ΔG_elec + ΔG_hbond + ΔG_desolv + ΔG_conform
```

**Output:** Binding pose + predicted affinity

**Example:**
- Dock linalool to OR10G4
- Predicted Kd = 8 μM (experimental ≈ 10 μM) ✓
- Identifies key interactions: H-bond to Ser residue

### 6.3 Virtual Screening

**Workflow:**
1. Build OR model (e.g., OR7D4 for musks)
2. Dock 100,000 virtual molecules
3. Rank by predicted binding affinity
4. Synthesize/test top 100
5. Validate hits experimentally

**Success rate:** ~5-15% of top predictions have desired activity (much better than random).

---

## 7. Case Studies

### 7.1 Predicting Odor Threshold (ODT)

**Dataset:**
- 500 molecules with measured ODTs
- Calculate 50 descriptors (MW, log P, PSA, shape, etc.)

**Model (Random Forest):**
```
log(1/ODT) = f(MW, log P, PSA, Dipole, ...)
```

**Result:**
- R² = 0.72 (explains 72% of variance)
- RMSE = 0.8 log units (~6× error)

**Interpretation:**
- **Key predictors:** MW (−), log P (−), PSA (+)
- Lower MW → more volatile → lower ODT
- Higher lipophilicity → better receptor access → lower ODT

### 7.2 Classifying Odor Character (Woody vs. Floral)

**Dataset:**
- 1000 molecules labeled "woody" or "floral"
- Calculate ECFP4 fingerprints

**Model (SVM):**
- Input: 2048-bit fingerprint
- Output: "woody" or "floral"

**Result:**
- Accuracy: 85% on test set
- Precision (woody): 88%
- Recall (woody): 82%

**Key substructures for "woody":**
- Sesquiterpene backbones (e.g., cedrol-like)
- Aromatic ethers (e.g., Iso E Super-like)

**Key substructures for "floral":**
- Aliphatic alcohols (linalool, geraniol)
- Phenylethyl derivatives

### 7.3 De Novo Design: Novel Musks

**Goal:** Find new synthetic musks (alternatives to nitromusks, polycyclic musks)

**Approach:**
1. Define "musk" pharmacophore (large hydrophobic cage, ~15-17 Å)
2. Generate virtual library (1 million molecules via combinatorial chemistry)
3. Filter by:
   - Matches pharmacophore
   - MW 200-300
   - log P 3-6
   - Synthetically feasible
4. Dock top 1000 to OR musk receptors (homology models)
5. Select top 50 for synthesis

**Result:**
- 50 synthesized → 7 have musky odor (14% hit rate)
- 2 are novel scaffolds (patentable)
- 1 has commercial potential (strong, long-lasting, cheap to make)

---

## 8. Databases & Tools

### 8.1 Odor Databases

**SuperScent (http://bioinf-applied.charite.de/superscent/):**
- ~5000 molecules with odor descriptors
- Includes odorant receptor data

**Flavornet (http://flavornet.org/):**
- ~700 flavor/fragrance compounds
- GC retention indices, odor descriptions

**The Good Scents Company (http://thegoodscentscompany.com/):**
- ~8000 materials
- Odor descriptions, applications

**Limitations:**
- Odor descriptions are subjective, inconsistent
- Many materials lack quantitative data (ODT, intensity)
- Biased toward common/commercial materials

### 8.2 Descriptor Calculation Software

**RDKit (Open source, Python):**
- 200+ 2D/3D descriptors
- Fingerprints (ECFP, MACCS)
- Free, widely used

**Dragon (Commercial):**
- 5000+ descriptors
- Very comprehensive
- Expensive

**Mordred (Open source, Python):**
- 1800+ descriptors
- Actively maintained

**Quantum chemistry (3D, electronic):**
- **Gaussian** (commercial, expensive)
- **ORCA** (free for academic)
- **GAMESS** (free, open source)

### 8.3 QSAR/ML Platforms

**KNIME (Open source):**
- Visual workflow for QSAR
- Integrates RDKit, ML algorithms
- No coding required

**Orange (Open source, Python):**
- Visual data mining
- Good for beginners

**Scikit-learn (Python):**
- ML library (Random Forest, SVM, etc.)
- Industry standard

**TensorFlow/PyTorch:**
- Deep learning
- For advanced users

---

## 9. Practical Workflow for Perfumers

### 9.1 Finding Alternatives to Restricted Materials

**Problem:** Material X is IFRA-restricted or discontinued.

**QSAR approach:**
1. Calculate fingerprint of X (ECFP4)
2. Search database for similar molecules (Tanimoto > 0.7)
3. Filter by:
   - Commercially available
   - IFRA-compliant
   - Similar MW (similar volatility)
4. Test top 10 candidates

**Example:**
- Oakmoss restricted → Find similar woody/earthy materials
- Top hits: Evernyl, Veramoss (synthetic alternatives)

### 9.2 Optimizing a Lead Structure

**Problem:** Material Y has great odor but poor longevity.

**QSAR approach:**
1. Generate analogs (add methyl, change functional group, etc.)
2. Calculate descriptors:
   - MW (higher → less volatile → longer lasting)
   - log P (higher → more substantive)
   - VP (lower → longer lasting)
3. Predict properties of analogs
4. Synthesize/test top 5 with best predicted longevity

**Example:**
- Linalool (fleeting) → Linalyl acetate (longer-lasting)
- Added acetate group: MW increases, VP decreases

### 9.3 Virtual Screening for Novel Materials

**Goal:** Discover new "green" note.

**QSAR approach:**
1. Define "green" from examples (cis-3-hexenol, hexanal, galbanum)
2. Build classification model ("green" vs. "not green")
3. Screen commercial chemical catalogs (100,000 molecules)
4. Test top 50 predicted "green" materials

**Hit rate:** ~10-20% have desired character.

---

## 10. Limitations & Future Directions

### 10.1 Current Challenges

**Small datasets:**
- Only ~5000 molecules with reliable odor data
- Deep learning needs 100,000+

**Subjectivity:**
- "Floral" means different things to different people
- Cultural/personal variation

**Mixture effects:**
- QSAR predicts single molecules
- Perfumes are mixtures (synergy, masking)

**Chirality:**
- Enantiomers can smell totally different
- Many QSAR tools ignore chirality

### 10.2 Emerging Solutions

**Crowdsourced odor perception:**
- Google/Leffingwell study: 50,000+ people rating odors
- Standardizing descriptors

**Transfer learning:**
- Use large chemical datasets (drugs, agrochemicals) to pre-train models
- Fine-tune on small odor dataset

**Multi-task learning:**
- Predict odor character + threshold + hedonic + intensity simultaneously
- Shares information across tasks

**Receptor-based models:**
- As OR structures are solved (cryo-EM), docking will improve
- Rational design becomes feasible

### 10.3 The "Holy Grail"

**De novo odor design:**
- Specify: "I want a woody, amber, long-lasting molecule"
- AI generates structure
- Synthesis + testing confirms

**We're not there yet, but getting closer.**

---

## 11. Practical Tips for Using QSAR

1. **Start simple:** Use similarity searching (Tanimoto) before complex models
2. **Know your limits:** QSAR predicts trends, not absolutes (test experimentally!)
3. **Use multiple models:** Consensus prediction is more reliable
4. **Validate:** Always set aside test set (20-30% of data)
5. **Interpret:** Understand which descriptors matter (not just black box)
6. **Iterate:** Use predictions to guide synthesis → test → improve model
7. **Combine with intuition:** QSAR + perfumer expertise > either alone

---

## 12. Quick Reference

### Key Descriptors for Fragrance QSAR

| Property | Descriptor | Interpretation |
|----------|------------|----------------|
| **Volatility** | MW, VP | Lower MW/higher VP = more volatile |
| **Lipophilicity** | log P | Higher log P = more lipophilic, better skin penetration |
| **H-bonding** | nHD, nHA, PSA | More H-bonding = lower volatility, higher polarity |
| **Shape** | Molecular volume, asphericity | Different shapes → different receptors |
| **Polarity** | Dipole moment | Higher dipole = more polar |
| **Reactivity** | HOMO-LUMO gap | Smaller gap = more reactive (stability concern) |

### Typical QSAR Performance

| Prediction Task | Typical R² or Accuracy | Notes |
|-----------------|------------------------|-------|
| Odor threshold (ODT) | R² = 0.6-0.8 | ~5-10× prediction error |
| Odor character (class) | 70-85% accuracy | Better with specific classes (woody vs. floral) |
| Similarity ranking | Top 10% enrichment ~5-10× | Better than random |
| Hedonic (pleasantness) | R² = 0.3-0.5 | High individual variation |

---

## References

- Arctander (1969) - *Perfume and Flavor Materials* (classic odor database)
- Rossiter (1996) - "Structure-odor relationships" (review)
- Zarzo (2007) - "Classification of odorants by QSAR" (methodology)
- Kowalewski & Ray (2020) - "Predicting odor from molecular structure" (modern ML approaches)
- Keller & Vosshall (2016) - "Olfactory perception of chemically diverse molecules" (neuroscience context)

**Tools:**
- RDKit: https://www.rdkit.org/
- SuperScent: http://bioinf-applied.charite.de/superscent/
- KNIME: https://www.knime.com/

**Critical Note:** QSAR in fragrance is less mature than in drug discovery. Use as guide, not gospel. Always validate predictions experimentally.
