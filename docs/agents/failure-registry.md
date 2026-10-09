# Agent failure registry (F1-F11)

> Moved out of `AGENTS.md` unchanged on 2026-10-08 so every session loads less; `AGENTS.md` links here. These are working notes and historical diagnostics, not universal policy: where they disagree with the rules in `AGENTS.md` (Rules 0-7 and the reviewed knowledge boundary), those rules win.

## Agent Failure Registry (Session 2026-07-06 - Cassis Iris Smoke)

Every systemic failure from this session. Read before formulating. Learn or repeat.

### F1. OAKMOSS COMPOSITE OAV - 300x UNDERESTIMATE
- Symptom: Perfumer smelled dominant oakmoss. Pipeline said OAV 0.03.
- Root cause: Composite decomposition had 5 constituents at 23% weight. Missing: atranorin degradation on skin (time-dependent, not equilibrium), methyl beta-orcinol carboxylate (primary olfactory monoaryl), orcinol phenolics (highest VP oakmoss constituents at 0.15-0.50 Pa).
- Fix: Expanded to 10 constituents at 46% weight. Added degradation pathway. Composite OAV 0.03 to 0.28 (10x) but still below threshold - equilibrium models cannot capture reaction kinetics.
- Learning: Natural absolute OAV models are PERCEPTUALLY FLOORS. Trust the nose over the model. Applicable to all naturals with degradation pathways (labdanum, tonka, vanilla, patchouli).

### F2. HEDIONE CROWDING - 18% = ONE-NOTE
- Symptom: All character voices buried under Hedione radiance.
- Root cause: One bottle with Hedione at 18% of concentrate smelled flat. Hedione is used at high levels in many fine fragrances, so this is a single observation, not a rule about where it stops being a carrier.
- Fix: Hedione cannot be taken out of a mixed bottle; adding more of the character materials is the only way to lower its share.
- Learning: Soft warning from that one bottle: above about 15% Hedione often dominates; compare against a lower-Hedione control before mixing. Not a safety limit and not a universal cap.

### F3. SILENT PASSENGERS - MATERIALS BELOW OAV 1
- Symptom: 20/44 materials below OAV 1 despite character/signature labeling.
- Root cause: VP below 0.05 Pa + low dose = headspace vacuum. VP wall is absolute.
- Fix: Cut them or reclassify as structural. Jasmine, Indole, Cade cut. Cade replaced with IBQ (VP 1 Pa).
- Learning: VP below 0.05 Pa = skin-only. Do not label as character/signature.
- **Withdrawn (2026-10-08):** this entry relied on vapour pressures about 100x too low (guaiacol is about 13.7 Pa and indole about 1.63 Pa at 25 °C); the corrected values come with the material data PR. Don't use its VP cut-offs as rules.

### F4. PIPELINE PARSER BUG - SECTION HEADERS AS MATERIALS
- Symptom: Accord headers parsed as material entries, inflating concentrate total.
- Root cause: Number + uL + % triggers row parser regardless of prefix.
- Fix: Use flat single-table format. Remove section headers for first gate.
- Learning: Check exact_subtotal in JSON. If parsed > expected, headers are being read as materials.

### F5. GUAIACOL IFRA VIOLATION
- Symptom: Boosted to 180 uL of 10% (0.3% active), 3x IFRA Cat4 limit.
- Root cause: Chasing headspace OAV without checking IFRA. VP 0.053 Pa will never project strongly regardless of dose.
- Fix: Revert to 60 uL (0.1%). Use IBQ and Birch Tar for headspace smoke.
- Learning: Materials with VP below 0.1 Pa hit IFRA limits before meaningful headspace OAV. Use higher-VP analogs.
- **Withdrawn (2026-10-08):** this entry relied on vapour pressures about 100x too low (guaiacol is about 13.7 Pa and indole about 1.63 Pa at 25 °C); the corrected values come with the material data PR. Don't use its VP cut-offs as rules.

### F6. IONONE RECEPTOR SATURATION
- Historical observation: Alpha Irone increases reportedly gave diminishing returns in one formulation; this is not a universal dose-response finding.
- Withdrawn explanation: OR5AN1 assignment, a fixed 200 uL ceiling and receptor-orthogonal pairings were not established by evidence.
- Reviewed boundary: Jaeger et al. (2013), DOI 10.1016/j.cub.2013.07.030, supports OR5A1-related beta-ionone sensitivity differences, not those claims.
- Design response: Compare recognizer, root texture and support roles under the locked brief, with matched controls. Do not infer receptor affinities from chemical-family labels.

### F7. SUBAGENT MODEL FORMAT FAILURE
- Symptom: All task() calls fail with model format errors.
- Root cause: oh-my-openagent.json uses bare names (deepseek-chat) but system expects provider/model format.
- Fix: Edit config, restart session. Workaround: direct execution.
- Learning: Check subagent availability first. If broken, proceed directly.

### F8. DILUTION MISMATCH
- Symptom: Formula labels mismatch inventory dilutions.
- Root cause: Formula text includes non-dilution text. Inventory has duplicate entries at different dilutions.
- Fix: Run evaluate_formula.py or /validate before gating.
- Learning: Three minutes of preflight saves three hours of debugging.

### F9. PIPELINE BRIEF MISMATCH
- Symptom: generic brief expects generic floral pyramid. Chypre flagged as FAIL.
- Root cause: No chypre fruity/modern brief. Available archetype targets Mitsouko, not modern pineapple-iris.
- Fix: Gate with generic, ignore perfume_knowledge FAIL, evaluate pyramid manually.
- Learning: Brief system needs expansion for modern chypre/fruity territory.

### F10. OAKMOSS FIX IS TEMPLATE FOR ALL NATURALS
- Learning: Before gating, check if natural has composite decomposition in natural_absolute_decomposition.py. If absent, OAV is significantly underestimated.

### F11. NATURAL LUXURY KITCHEN-SINK FAILURE — L'HOMME RESERVE (2026-07-07)
- Symptom: 28-material L'Homme Reserve smelled "muddy/chaotic" — unrecognizable as L'Homme EDT. User wasted 225µL Alpha Irone 30% (expensive iris butter).
- Historical hypothesis: particular natural additions reportedly made the target muddy. Their constituent-family differences do not establish physical incompatibility, a reaction, or an inevitable sensory clash.
- Fix: Cut 7 materials. v3 = 21 materials: kept only chemically compatible families (Ginger zingiberene + Bergamot limonene/linalool + Rose citronellol/geraniol + Clove eugenol + Iris irones + Violet Leaf + woody-amber synthetics).
- Reviewed learning: separate solubility, chemical stability, sensory masking and target drift. Each needs its own evidence; chemical taxonomy alone decides none of them.
- Design response: retain the control and compare a small omission/addition or block alternative. Natural complexity must earn a target-linked function rather than being included as an automatic luxury upgrade.
