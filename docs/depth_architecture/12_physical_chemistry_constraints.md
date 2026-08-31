# Volume 12 — Physical-Chemistry Constraints

**Status:** normative computational and measurement doctrine  
**Measured headspace, sensory performance, safety, and stability:** `NOT TESTED`

## Construct

Physical chemistry constrains what a perfume can deliver, but it does not
determine the resulting percept by itself. The program uses active dose, ppm,
ODT, OAV, vapor pressure, mole fraction, activity coefficient, evaporation,
permeation, and temporal simulation to detect impossible instructions, stock
errors, missing data, dominance risks, and weak delivery hypotheses. These are
floors and diagnostics, not beauty or depth scores.

Formula ppm is defined on the declared quantity basis. For a concentrate with
total volume used as the working approximation, active ppm is active material
divided by total concentrate, multiplied by one million. Every stock line must
distinguish raw transfer from active equivalent. A ten-percent stock delivers
one-tenth of its raw volume as active material under the stated v/v assumption.
Weight-based work requires densities and a separate mass closure; volume
arithmetic must not silently become weight authority.

ODT is a threshold under a specific matrix, route, method, and population.
Air ppb and ethanol-solution ppm are not interchangeable. OAV in its simple
form is concentration divided by threshold. The pipeline's headspace model
uses a modified Raoult relationship in which partial pressure depends on mole
fraction, pure-component vapor pressure, and an activity coefficient. That
model is more informative than raw liquid concentration but remains sensitive
to uncertain physical data and mixture nonideality.

An OAV above one means modeled concentration exceeds the selected threshold; it
does not guarantee a separately perceived note, a beneficial role, or the
finished-mixture intensity. OAV below one can flag a problem when a role
requires conscious perceptibility, but structural, modulatory, or physical
roles need different evidence. Unknown OAV remains unknown.

Naturals require composite OAV. A flower oil, absolute, EO, or resinoid cannot
be assigned one monomolecular threshold and bulk vapor pressure as though it
were a pure compound. Constituent decomposition estimates odor-active
contributions while the actual natural remains one formula identity. Missing
constituent coverage or unknown lot composition creates a quantitative hold,
not zero odor.

## Mechanisms

**Stock rebasing** changes active amount and all downstream diagnostics. If a
line changes from ten percent to neat at fixed raw microlitres, active dose and
OAV must increase by the corresponding factor unless another input changes.
Mutation tests guard this historical class of failure.

**Partitioning and evaporation** govern release from liquid or skin film.
Pure-component vapor pressure alone is insufficient; mole fraction, activity,
solvent, temperature, and substrate matter. **Permeation** removes or delays
material through skin. **Diffusion and airflow** dilute and intermittently
transport vapor. **Adaptation and receptor interaction** then modify perceived
intensity, so physical release is only one layer.

**Temperature correction** may be approximated with Clausius–Clapeyron when
compound-specific enthalpy is unavailable, but the approximation and reference
temperature must be stated. A Bangkok-warm environment can change release
substantially relative to a cool laboratory. No temperature factor is allowed
to become an unqualified performance claim.

## Material translation

Known chemicals need molecular weight, vapor pressure at a stated temperature,
ODT with units and matrix, stock dilution, and preferably activity behavior.
Profiles, YAML data, generated material properties, and ODT dictionaries must
be synchronized. Duplicate ODT entries are dangerous because later dictionary
values can silently win.

Naturals need exact inventory name, supplier or lot where available, stock
fraction, constituent-decomposition coverage, and whole-material preservation.
Carriers need identity and volume. Musks and very low-volatility materials may
show low modeled headspace despite important film or skin roles, while
high-impact chemicals may dominate at trace active amounts.

Every raw-stock transfer below ten microlitres requires a practical preparation.
For example, instead of instructing a five-microlitre source dose, prepare a
lower stock using at least ten microlitres of the source stock, a named carrier,
a closed total, and a stated final fraction; then deliver a measurable volume
from that preparation. The instruction records source fraction, source volume,
carrier volume, final volume, final fraction, delivered volume, and delivered
active equivalent.

## Interactions

Physical properties interact with formula composition. Activity coefficients
can depart from unity. Solvent changes can alter headspace and skin behavior.
Two materials can compete at receptors despite independent OAVs. A large
limonene-like pool can dominate modeled and perceived opening and contribute to
adaptation. Low-volatility supports can change film and persistence without
appearing as loud notes.

Physical diagnostics interact with target architecture. A missing late
recognizer is a temporal-design problem only after confirming that its active
dose and data are correct. A high OAV outlier may be a desirable identity
anchor or a masking risk. The model proposes tests; the name and anatomy decide
what counts as a problem.

## Failure modes

**Raw/active confusion** treats stock volume as neat material. **Unit collision**
mixes air ppb and solution ppm. **Duplicate-key corruption** lets a stale ODT
replace the verified value. **Unknown-to-zero conversion** makes absent data
look safely subthreshold. **Natural monomolecule error** assigns one threshold
to a mixture. **Activity-equals-one silence** hides an assumption.

**Lemonile-type rebasing failure** leaves OAV unchanged when stock strength
changes. **Canonical-direct conflict** silently averages incompatible OAV
paths. **Unmeasurable trace dosing** instructs a source transfer below ten
microlitres. **Model promotion** calls vapor estimates projection, longevity,
or depth. **Data-path drift** leaves material properties inconsistent across
ODT, profiles, generated JSON, and YAML.

## Observables

Every pipeline analysis reports material, stock dilution, raw microlitres,
active microlitres, molecular weight, mole fraction, vapor pressure, activity
coefficient, vapor ppm, ODT, OAV, and note tier. It also reports OAV-weighted
distribution and time windows. These appear before gate summaries because raw
physics is more diagnostic than a pass/fail label.

Record data provenance, units, temperature, assumptions, aliases, and missing
values. Cross-check exact agreement across formula state, evidence gate,
release gate, compact report, and full analysis. For naturals report
constituent coverage and composite result without pretending the constituent
model is a sensory reconstruction.

## Controlled tests

Use arithmetic unit tests for stock conversion and ppm. Use mutation tests that
change stock strength and require active dose and OAV to respond. Test duplicate
ODT detection and alias resolution. Test natural composite coverage and ensure
the whole material remains in formula output. Test unknown propagation.

For physical validation, use measured headspace or evaporation where available,
with exact formula, substrate, temperature, and time. For sensory contribution,
pair physical diagnostics with omission and ratio tests. A high OAV material
that produces no target-linked difference is not rescued by the model; a low
modeled OAV structural material requires an explicit non-perceptual hypothesis.

For preparations, verify source and carrier closure, final fraction, delivered
active dose, and minimum source transfer. Do not compound merely because the
paper instruction is arithmetically valid; physical work requires separate
authorization and safety review.

## Claim boundary

Physical calculations can identify contradictions and shape experiments. They
cannot establish actual headspace without measurement, finished-mixture
perception, liking, realism, texture, sillage, longevity, safety, stability, or
release. All such endpoints remain `NOT TESTED`. OAV is never a substitute for
the nose, and the nose is never a substitute for safety or analytical evidence.

## Primary literature

- Almeida RN, Costa P. *Evaporation and permeation of fragrance applied to the
  skin.* Industrial & Engineering Chemistry Research 58 (2019), 9644–9650.
  https://doi.org/10.1021/acs.iecr.9b01004
- Brattoli M et al. *Gas chromatography analysis with olfactometric detection
  as a useful methodology for chemical characterization of odorous compounds.*
  Sensors 13 (2013), 16759–16800. https://pmc.ncbi.nlm.nih.gov/articles/PMC3892869/
- Johnson AJ et al. *GC-recomposition-olfactometry and multivariate study of
  three terpenoid compounds in the aroma profile of Angostura bitters.*
  Scientific Reports 9 (2019), 7633. https://pmc.ncbi.nlm.nih.gov/articles/PMC6529406/
- Oka Y et al. *Olfactory receptor antagonism between odorants.* EMBO Journal
  23 (2004), 120–126. https://doi.org/10.1038/sj.emboj.7600032
- *A quantitative framework for predicting odor intensity across molecules
  and mixtures.* Nature Communications (2025).
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12363845/

