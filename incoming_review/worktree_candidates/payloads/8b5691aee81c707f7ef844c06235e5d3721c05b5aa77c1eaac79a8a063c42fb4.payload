# Perfume-Chem construction-complexity literature and implementation map

Date: 2026-08-09  
Authority correction: 2026-08-10  
Workspace: `D:\chatbots\perfume-chem`  
Authority state: **STAGED / WITHHELD_UNKNOWN**  
Formula, inventory, safety, release, and canonical-database authority changed: **no**

## Outcome in easy words

The most valuable addition was not another perfume score. It was the missing
evidence foundation beneath any serious claim about gradients, empty space,
hedonic construction, or airiness:

1. The complete 35,084-row DREAM psychophysics derivative is now checked
   against its exact 9,461,137-byte parent workbook across all 736,764 retained
   response cells.
2. Perfume-Chem now emits a **multi-axis construction profile**. It keeps
   formula structure, modeled headspace distribution, modeled time change,
   descriptor gradients, foreground/background design, heavy-note coexistence,
   negative-space hypotheses, hedonics, graph structure, configural emergence,
   and individual variability separate.
3. There is deliberately **no overall complexity or beauty score**.
   The machine-readable decision contract now states
   `complexity_authority=WITHHELD`.
4. Functional groups are never treated as receptor spaces or perceptual
   coordinates. Raw material count is never treated as proof of olfactory
   white, congestion, richness, or clarity.
5. “Empty space,” “gradient,” “airiness,” “parallel perception,” and
   pleasantness remain testable construction hypotheses until the required
   headspace and human-panel evidence exists.

This is the correct order of work: establish source lineage and uncertainty,
then generate bounded design hypotheses, then test the hypotheses. It avoids
optimizing a perfume toward an attractive number that has no validated sensory
meaning.

## The literature boundary

### 1. Material count is not perceptual complexity

Weiss and colleagues found convergence toward “olfactory white” in
intensity-equalized mixtures that sampled olfactory space broadly, with
convergence becoming pronounced around several dozen components. That result
does **not** provide a universal raw-material cutoff for an unequal-intensity
perfume in a changing ethanol/water/skin matrix. The implementation therefore
reports modeled distribution shape but refuses a material-count-to-white rule.
[Weiss et al., PNAS 2012](https://www.weizmann.ac.il/brain-sciences/labs/schneidman/sites/neurobiology.labs.schneidman/files/publications/Weiss%2Bal_2012-PNAS.pdf)

Kermen and colleagues reported that molecular complexity of a **single
molecule** was associated with richer odor descriptions and pleasantness in
their dataset. Molecular complexity is not the number of materials in a
formula, the number of detectable headspace contributors, or the number of
notes a listener can separate. Those concepts remain distinct axes.
[Kermen et al., Scientific Reports 2011](https://www.nature.com/articles/srep00206)

### 2. Mixtures can be elemental, configural, suppressed, or unmasked

Competitive receptor binding can generate suppression, overshadowing, and
synergy without being recoverable from a functional-group label. A competitive
binding model predicted receptor responses to mixtures containing up to twelve
odorants in one experimental system, but the necessary receptor-specific
parameters are absent for most perfume materials and naturals.
[Singh et al., PNAS 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6511041/)

Selective adaptation can unmask components that were suppressed in the intact
mixture. Frank and colleagues found useful unmasking in binary mixtures, while
component identification in more complex mixtures remained difficult. This is
the closest operational basis for some “negative-space” ideas: compare intact,
adapted, omission, and addition conditions rather than assigning an aesthetic
gap score.
[Frank et al., Chemical Senses 2017](https://academic.oup.com/chemse/article/42/7/537/3876319)

Perfumer training can shift reports toward more elemental perception in binary
and ternary blends. Any validation panel must therefore preserve expertise and
participant-level responses rather than collapse everyone into one constant.
[Barkat et al., Chemical Senses 2012](https://pubmed.ncbi.nlm.nih.gov/21873604/)

### 3. Descriptor geometry is useful, but only with measured vectors

Snitz and colleagues represented mixtures with physicochemical vectors and
predicted aspects of perceptual similarity under intensity-controlled
conditions. Their representation did not solve finished-perfume vapor
partition, diffusion, concentration, or temporal change.
[Snitz et al., PLoS Computational Biology 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC3772038/)

Ravia and colleagues collected 49,788 pairwise estimates over 242
multicomponent odorants from 199 participants and learned a physicochemical
distance related to perceptual similarity. This supports a measured or learned
descriptor-space lane, not an assumption that ester, alcohol, aldehyde, or
terpene membership forms a continuous smell gradient.
[Ravia et al., Nature 2020](https://www.nature.com/articles/s41586-020-2891-7)

Homologous-series studies show that chain length and functional group can
change odor quality and threshold, often nonlinearly. Chemical series are
therefore useful **candidate generators** for experiments, not validated
perceptual interpolation axes.
[Laska and Teubner, Chemical Senses 1999](https://pubmed.ncbi.nlm.nih.gov/22666021/)
[Cometto-Muniz and Abraham, Journal of Agricultural and Food Chemistry 2014](https://pubs.acs.org/doi/10.1021/jf404885j)

### 4. Hedonic effects are concentration-, intensity-, and panel-dependent

In a 222-binary-mixture study, mixture pleasantness was often related to
component pleasantness and intensity, with partial-addition behavior in some
conditions. This is not a universal formula for a high-order perfume. The
current hand-entered `HEDONIC_VALENCE` table is therefore not accepted as
calibrated mixture authority.
[Ma et al., Chemical Senses 2020](https://academic.oup.com/chemse/article-pdf/45/4/303/33435595/bjaa020.pdf)

Earlier predictive work likewise treated component pleasantness and intensity
as important predictors for binary mixtures. It does not authorize a
finished-perfume beauty score or a context-free hedonic gradient.
[Lapid et al., PLoS Computational Biology 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC2533422/)

### 5. Time is a construction axis, not merely top/heart/base labels

Humans can discriminate reversed odor sequences at onset differences as short
as 60 ms in controlled conditions. This shows that temporal order can matter
within one sniff, while Perfume-Chem's current multi-hour evaporation simulator
operates at a different scale and remains uncalibrated.
[Wu et al., Nature Human Behaviour 2024](https://www.nature.com/articles/s41562-024-01984-8)

Temporal order and component identity become difficult to report in ternary
mixtures, consistent with severe limits on conscious component access. A large
modeled effective-component count must never be described as the number of
notes a person can identify.
[Laing and Francis, Physiology & Behavior 1999](https://www.sciencedirect.com/science/article/pii/S0926641099000348)

### 6. “Airiness” depends on the matrix and transport

Dynamic-headspace measurements over skin show that a component can diffuse
differently alone, in a mixture, and in a cosmetic matrix. This directly
supports testing the user's intuition that a heavy accord and more volatile
materials may coexist differently depending on the surrounding matrix.
[Dynamic headspace diffusion study](https://pubmed.ncbi.nlm.nih.gov/19250472/)

Perfume evaporation is nonideal: vapor-liquid equilibrium, ethanol/water
composition, and mutual solubility alter release. Hydroalcoholic partition
coefficients can change greatly with ethanol fraction. A modeled heavy/nonheavy
intensity share can screen a construction, but it cannot prove “airiness” or
independent parallel perception.
[Perfume mixture diffusion model](https://www.sciencedirect.com/science/article/pii/S0009250909000700)
[Nonideal ternary perfume equilibrium](https://pubs.acs.org/doi/10.1021/ie048760w)
[Hydroalcoholic partition study](https://www.sciencedirect.com/science/article/abs/pii/S0378381208000253)

### 7. Omission and recombination are the validation path for implied notes

GC-olfactometry/recombination work on lavender demonstrates how complete
recombinations and omission variants can test which constituents matter to the
recognized whole. That experimental logic is more defensible for
“negative-space” construction than an invented empty-space score.
[Lavender recombination and omission study](https://pmc.ncbi.nlm.nih.gov/articles/PMC3422294/)

### 8. A promising 2026 preprint remains provisional

A July 2026 bioRxiv preprint reports that simple averaging predicted many odor
quality profiles across 432 mixtures of 144 components evaluated by a trained
panel. It motivates an optional linear descriptor-centroid baseline. It is not
peer reviewed, does not erase receptor nonlinearity, intensity, concentration,
time, or panel dependence, and has declared commercial context. It is retained
as a future comparison baseline, not production authority.
[2026 mixture-perception preprint](https://www.biorxiv.org/content/10.64898/2026.07.03.736426v1)

### 9. 2026-08-10 source-identity and authority correction

The reported source identity "2026 peer-reviewed PNAS semantic mixture-distance
paper" could not be resolved. The work matching that description is a 2023
*Chemical Senses* article, not PNAS and not 2026. It models mixture
discriminability through learned semantic representations; it does not supply a
universal perfume-complexity score or material-count rule.
[Dhurandhar et al., Chemical Senses 2023](https://pubmed.ncbi.nlm.nih.gov/37262433/)

The distinct 2026 PhysSim paper uses physics-inspired latent dynamics as a
learned inductive bias for mixture similarity. The authors explicitly do not
claim literal molecular forces or a receptor theory, and monomolecular transfer
was near zero in the reported evaluation. It is a model-comparison candidate,
not semantic authority, a collision cutoff, or sensory equivalence.
[Kim, Journal of Chemical Information and Modeling 2026](https://pubmed.ncbi.nlm.nih.gov/42469179/)

The July 2026 linear-mixture preprint reports 432 mixtures made from 144
component stimuli, with 2 to 10 components, and finds that an averaged
component-quality model explained nearly all tested profiles. Within-session
replication reduced apparent nonlinearity. Because this remains a preprint and
one declared panel/context, it is retained as a source-scoped baseline rather
than a universal law. It also argues directly against requiring bespoke
nonlinear pair rules for every candidate interaction.
[Pellegrino et al., bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.07.03.736426v1.full)

Primary human-mixture evidence establishes why fixed row and similarity gates
are unsafe. Intensity-equated, olfactory-space-spanning mixtures can converge
toward olfactory white at high component counts, while exact component ratio
can switch the same binary pair between configural and elemental perception.
Only some tested binary/ternary mixtures blended, trained assessors reported
more elemental perception, and identification became very difficult beyond two
components in the tested task. In one unpleasant-mixture context, suppression
increased with component count and strongest-component intensity approximated
mixture intensity; that result is context-specific counter-evidence, not a new
universal rule.
[Weiss et al., PNAS 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3523876/)
[Wilson et al., Brain Research 2020](https://pubmed.ncbi.nlm.nih.gov/31866364/)
[Barkat et al., Chemical Senses 2012](https://pubmed.ncbi.nlm.nih.gov/21873604/)
[Jinks and Laing, Physiology & Behavior 2001](https://pubmed.ncbi.nlm.nih.gov/11239981/)
[Laing et al., Physiology & Behavior 1994](https://pubmed.ncbi.nlm.nih.gov/8084911/)

Finally, the often-cited molecular-complexity result concerns the structural
complexity of single molecules. It cannot justify a minimum number of materials
in a formula.
[Kermen et al., Scientific Reports 2011](https://pubmed.ncbi.nlm.nih.gov/22355721/)

The resulting operational boundary is noncompensatory: report recognizer
preservation, structural organization, interaction, temporal shape, texture,
contrast, robustness, post-ablation effective complexity, execution readiness,
and evidence uncertainty separately. Do not derive PASS, REBUILD, beauty,
liking, similarity, safety, or release from their sum or from row count.

## Construction taxonomy implemented or mapped

| Axis | What it asks | Current computation | Current authority |
|---|---|---|---|
| Formula structure | What was explicitly dosed? | Counts known, unknown, and opaque rows | Exact accounting only |
| Modeled headspace distribution | Is modeled perceptible intensity concentrated or spread? | OAV >= 1 effective count, evenness, top-1/top-3 share, coverage | Heuristic |
| Modeled temporal differentiation | How much does the modeled distribution change across windows? | Consecutive Jensen-Shannon distance and dominant-identity turnover | Heuristic, uncalibrated |
| Descriptor gradient | Do ordered, measured component vectors form a direct/even path? | Standardized-vector path length, directness, step CV, monotonic-axis fraction | Unknown without supplied vectors; heuristic when supplied |
| Foreground/background | Does a brief-declared figure sit above its declared support? | Modeled shares and salience ratio by time | Heuristic |
| Heavy-note coexistence | Are modeled heavy and non-heavy signals both present? | Heavy share, non-heavy effective count, coexistence windows | Heuristic; not independence or airiness |
| Negative space | Is a declared descriptor interval weakly occupied? | Modeled descriptor occupancy and data coverage by time | Speculative even with vectors |
| Hedonic gradient | Do panel-calibrated component values follow an ordered path? | Range, monotonicity, step CV | Unknown by default; never mixture beauty |
| Accord graph modularity | How are declared functional modules connected? | Mapped, awaiting authority-labeled edge input | Unknown |
| Configural emergence | Does the whole create or hide a note? | Requires recombination, omission, addition, or adaptation experiment | Unknown |
| Individual variability | For whom does the construction work? | Requires participant distributions, expertise, and repeats | Unknown |

No axis is silently summed into another. This protects the system from an
attractive but scientifically incoherent “complexity = 83/100” result.

## Operational translation of the requested ideas

### Building around empty space to imply a smell

Operational definition:

- Declare the intended descriptor interval before looking at results.
- Use standardized, source-linked component vectors for the exact
  concentration and matrix when possible.
- Report descriptor-data coverage and modeled occupancy through time.
- Compare the intact formula with a deliberately gap-filled variant and at
  least one omission variant.
- Ask blinded participants whether the target note is present, recognizable,
  and distinct. Preserve individual responses.

What is forbidden: “low occupancy means the perfume implies X.” Low occupancy
only defines the candidate gap.

### Chemical-group gradient

Operational definition:

- Chemical series or functional groups may propose candidates.
- The gradient itself must be computed from standardized empirical descriptor
  vectors or a separately validated perceptual embedding.
- Compare the intended order with shuffled, reversed, and endpoint-only
  controls.
- Test several concentrations because odor quality and threshold can change
  nonlinearly.

What is forbidden: treating `terpene_alcohol`, `ester`, or `aldehyde` as a
receptor channel or assuming adjacent chemistry smells adjacent.

### Hedonic gradient with foreground notes that pop out

Operational definition:

- Calibrate component and accord pleasantness within one panel, matrix, dose,
  and cultural context.
- Declare foreground/background partitions from the perfume brief.
- Use modeled OAV-derived salience only to select test doses.
- Test the complete perfume and controlled variants. Analyze pleasantness,
  target-note recognition, contrast, and coherence separately.

What is forbidden: using the current hand-curated valence table as a finished
perfume beauty function.

### Air around essential oils, ambers, and other heavy notes

Operational definition:

- Declare the heavy accord rather than inferring it from a note label.
- Track heavy share, non-heavy effective modeled contributors, and temporal
  coexistence.
- Measure dynamic headspace of the heavy accord alone, the surrounding matrix
  alone, and the complete formula.
- Use a factorial design: heavy dose x volatile scaffold x solvent/matrix x
  time. Rate airiness, separability, identity, diffusion, and target fidelity
  separately.

What is forbidden: describing simultaneous modeled signals as independently
perceived notes.

## Full-corpus DREAM lineage result

The full-corpus comparison uses four exact keys: compound identifier, trimmed
and case-folded odor label, dilution, and DREAM subject identifier. It compares
21 retained response fields per DREAM row.

| Full-corpus invariant | Recomputed result |
|---|---:|
| DREAM rows with one parent match | 35,084 |
| Retained cells compared | 736,764 |
| Parent workbook keyed rows | 48,804 |
| Parent-only keyed rows outside DREAM | 13,720 |
| Exact numeric cells | 124,973 |
| Source blank to target zero | 418,728 |
| Source blank to target blank | 182,080 |
| Deterministic 2-9 to 20-90 restoration | 5,268 |
| Published derivative 1 to 10 | 1,502 |
| Published derivative 1 to 100 | 4,213 |
| Incompatible cells | 0 |

The 5,715 source-value-one cells cannot be reconstructed as 10 versus 100 from
the workbook alone. The published DREAM derivative performs that
disambiguation. Consequently:

- the relation remains `CITES`, not `DERIVED_FROM`;
- `authority_state` remains `WITHHELD_UNKNOWN`;
- `canonical_rows_written` remains `0`;
- `promotion_allowed` remains `false`;
- only 50 deterministic/disambiguation examples per class are retained in the
  report; aggregate counts cover the complete corpus;
- the Geraniol B1/B2 observation tranche remains the only emitted observation
  tranche. Full-corpus canonical observation loading was not authorized.

The real dry-run, materialized run, and independent replay returned
`VERIFIED_STAGED` with no rejections. All 12 emitted reports were byte-identical
between the materialized run and replay. The deterministic bundle SHA-256 is
`483a18fca51d764dd2dcf1d3fa923e69613bd5467183bd206ede1891ed2a22c6`,
the validation ID is `lin-7a769347eacf7b393e0aaa21528ce780`, the validation
record SHA-256 is
`619dc2842f4f548984cbafa2eec85f4b67abbe09be35e573a46d0fd7b068279d`,
and no authority changed.

## Implementation map

```text
Exact source bytes and manifests
  -> full-corpus key and cell lineage audit
  -> staged empirical descriptor/valence evidence (still quarantined)
  -> explicit ConstructionComplexityInputs
  -> engine.perception.construction_complexity
       - exact formula accounting
       - heuristic modeled headspace and temporal axes
       - optional descriptor/semantic/hedonic hypotheses
       - UNKNOWN experimental axes
  -> engine.workbench canonical output
  -> blinded experiments and dynamic headspace
  -> empirical calibration only after held-out validation
```

Changed implementation surfaces:

- `engine/perception/construction_complexity.py`
- `engine/perception/__init__.py`
- `engine/workbench.py`
- `engine/ingestion/scientific.py`
- `data/source_manifests/dream_olfaction_fb47cb343cdf.json`
- `tests/test_construction_complexity.py`
- `tests/test_scientific_source_ingestion.py`

No new pipeline script was created.

## Highest-value experimental program

### Phase C0 - vocabulary and panel contract

Define anchors for airiness, separability, density, coherence, target fidelity,
contrast, emergence, and recognition. Record participant expertise, repeated
ratings, anosmia screens where relevant, concentration, matrix, dose, sniff
timing, and environment.

### Phase C1 - negative-space triads

For each hypothesis, compare complete, gap-filled, and omission variants.
Primary outcomes: target-note recognition and emergence. Secondary outcomes:
pleasantness and coherence. Stop if the gap cannot be described reliably above
the preregistered threshold.

### Phase C2 - gradient controls

Compare intended, shuffled, reversed, and endpoint-only material sequences at
multiple concentrations. Test descriptor continuity, target identity, and
pleasantness independently. Do not optimize against the construction metrics
until held-out panel prediction is demonstrated.

### Phase C3 - heavy-note airiness factorial

Vary heavy-accord dose, volatile scaffold, and matrix. Pair sensory ratings
with dynamic headspace at opening, 5 minutes, 30 minutes, 2 hours, and 4 hours.
The result should calibrate a matrix-specific separability model, not a
universal airiness constant.

### Phase C4 - temporal and expertise replication

Repeat the best candidates across trained and untrained groups and across
days. Preserve distributions. A result that exists only in the perfumer group
is still valuable, but it must be labeled as expertise-dependent.

## Remaining gaps and future directions

1. There is no accepted universal psychophysical scale for perfume “airiness”
   or “negative space.” A project-specific protocol must be validated.
2. DREAM measurements are molecule-, dilution-, paraffin-oil-, and
   panel-specific. They are candidate descriptors, not direct perfume-matrix
   values.
3. Natural materials and commercial bases require batch/lot constituent
   evidence; parent labels hide internal complexity and variability.
4. Current temporal simulation is heuristic and cannot predict skin life or
   absolute diffusion.
5. Current receptor coverage is insufficient for receptor-level mixture
   claims.
6. Hedonic values need participant-level calibration and held-out prediction.
7. Accord-graph edges need edge-level evidence classes before graph topology
   can inform construction decisions.
8. A linear descriptor-centroid baseline, a learned perceptual model such as
   the Principal Odor Map, and nonlinear interaction models should be compared
   only after a frozen local benchmark is established.
   [Principal Odor Map paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11898014/)
   [OpenPOM reference implementation](https://github.com/ARY2260/openpom)

## DeepLuna Chat audit and debugging record

DeepLuna Chat was used only as bounded read-only review through
`cheapluna-chat / DIRECT_PRO`. DeepLuna Fast, alternate providers, Codex
subagents, and fallback routes were not used.

- `DS-4bc6f604bcc06c03c2caf65c5b75782c` mapped existing graph and
  psychophysics primitives and correctly flagged functional-group receptor
  claims, raw channel-count clarity claims, fixed olfactory-white thresholds,
  and unbounded anosmia constants as unsafe.
- `DS-25bff77d707525072e7a2bfb1d3cd3a5` passed the lineage generalization audit
  and recommended parameterized scope plus bounded detail output.
- `DS-d4e24239f686e67e26b481adccd50a39` blocked after exhausting its two-call
  cap. That is retained as a worker-performance defect; Sol did not shrink or
  deny the high-value task and did not retry through another provider.
- `DS-bef444a090999e708e166aa289a140fe` failed closed on 2026-08-10 before
  collecting any required file receipt because its repository-tool budget was
  exhausted. Its findings were empty; Sol verified the active prompt, governing
  document, native profile, and tests locally and used no retry or fallback.

The job artifact shows that turn two was already forced-final and exposed only
`finish_handoff`, but the runtime did not produce a terminal handoff. Inspection
of the installed immutable runtime localizes the failure: if the
`finish_handoff` argument string is absent, invalid JSON, or JSON `null`, parsing
produces a falsy value; the call is then handled like an ordinary failed tool
call. The loop reaches its provider-call cap and replaces the actionable
terminal-payload error with `MAXIMUM_PROVIDER_CALLS_EXHAUSTED`. The audit log
retains the tool name but not its raw argument string, so it cannot distinguish
those three malformed-payload cases after the fact.

The repair boundary for a future orchestrator release is therefore narrow:
forced-final `finish_handoff` arguments must parse to a JSON object or fail
immediately with a dedicated local-contract error, and the original error must
survive instead of being masked by the call cap. A regression should cover
missing, malformed, `null`, and schema-invalid terminal arguments. This study
did not patch the installed immutable runtime or the user's in-progress upgrade
candidate.

Sol independently inspected the code, performed the full-corpus calculations,
made all scientific and architectural decisions, implemented the changes, and
retains final acceptance.

## Preservation and focused acceptance

Before edits, five in-scope paths were archived and restoration-tested as
`archive/construction-complexity-prechange-20260809T212236956.zip` (SHA-256
`cd616b99c9b683d1fee99c00a2d2596eecf75a7e8f552069f744d0fa39acf484`).
All five restored copies matched their source bytes.

Before the 2026-08-10 authority cutover, six exact in-scope paths were archived
and restoration-tested as
`archive/meaningful-complexity-authority-prechange-20260810T084000693.zip`
(SHA-256
`b27386b961a411fb0b5fe4835f782364c27516bdd30428cdc9a6e736946640ea`).
All six restored copies matched their source bytes.

Protected inputs remained unchanged:

- `inventory.txt`: `dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec`
- `data/perfumery_kb.db`: `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`
- DREAM `TrainSet.txt`: `ae43841013a9c5ecb3975953b85e5965663d416d2445178e86ad577d907575a0`
- Keller/Vosshall workbook: `efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62`

Focused acceptance passed: 30 scientific-ingestion tests; 33 construction,
workbench, and golden-regression tests; Ruff; Python compilation; a real
full-corpus dry-run, materialized run, and replay; and 12/12 byte-identical
replay reports. This is not a release claim, so the full release verifier and
formula pipeline were not run.

The reciprocal prompt was delivered directly to ChatGPT conversation
`6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf` with a pointer back to Codex task
`019fe3a3-3cca-7462-b8e9-e315015e95df`. Delivery is confirmed; no assistant
acknowledgement is inferred.

## Claims explicitly withheld

This work does not establish that any perfume is beautiful, complex, airy,
separable, realistic, similar to a target, safe, IFRA-compliant, stable,
long-lasting, or ready to compound or release. It adds evidence-labeled
diagnostics and a source-lineage prerequisite for future experiments.
