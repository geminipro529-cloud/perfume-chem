# Lavande Ambre Profond R6 — personal sensory protocol draft

Date: 27 September 2026

Status: `DRAFT_NOT_AUTHORIZED_FOR_EXECUTION`

This is a single-person, personal-perfumery protocol draft for the user's stated
interest in hedonism, architecture, structure, performance, mass-appealness,
and reasoned complexity. It creates no human observation, does not authorize
skin application, and cannot establish population preference, safety,
regulatory compliance, or commercial readiness.

## Endpoint interpretation

The requested terms are retained, but their authority is narrowed truthfully:

| Requested idea | Recorded endpoint | Permitted interpretation |
|---|---|---|
| Hedonism | Personal liking | This assessor under the recorded condition only |
| Architecture | Phase definition and transition quality | Descriptive personal observation |
| Structure | Coherence and support of the lavender–amber concept | Descriptive personal observation |
| Performance | Perceived intensity, diffusion, and persistence | Personal sensory observation, not instrumental release |
| Mass-appealness | Personal impression of likely broad appeal | Hypothesis only; never a population claim |
| Complexity with reason | Meaningful facets and transitions that support the name | Not ingredient count and not maximal busyness |

No endpoints are summed into a beauty, quality, or winner score. Harshness and
other defects stay separate from liking.

## Sample branch

The attachment did not establish whether physical R5 or R6 samples exist. The
protocol therefore branches without asking again now:

- If comparable R5 and R6 samples later exist, use a blinded pairwise comparison.
- If only R6 exists, use separately coded repeat presentations of R6 for
  descriptive repeatability; do not claim comparative improvement.
- If no R6 sample exists, collect nothing.
- If samples differ materially in age, storage, bottle, dilution, or application
  history, record the mismatch and withhold a formula-level winner.

## Conditions to record before any later session

These are fields for the future record, not prerequisites to this draft:

- blind sample code and formula/sample receipt;
- sample age and storage description;
- substrate (`skin` is the desired initial domain);
- body site;
- application amount and method;
- date, local time, and session identifier;
- environment as measured values if instruments exist, otherwise explicitly
  `UNMEASURED` rather than guessed;
- recent fragrance exposure, illness, smoking, food, or other obvious context;
- presentation order; and
- any missing or interrupted timepoint.

Skin and blotter results must never be pooled. Because skin use was not
authorized in the submitted receipt, the desired skin branch remains on hold
until a separate skin-use and safety decision is made.

## Blinding and presentation

Use neutral codes that do not contain `R5`, `R6`, `old`, `new`, or formula
names. For a comparison, balance presentation order across repeat sessions.
Self-blinding is valid only when the code-to-sample key is genuinely hidden
during scoring; otherwise mark the session `OPEN_LABEL` and do not describe it
as blinded.

Evaluate one application site per sample under comparable application
conditions. Do not add a second application to compensate for a weak first
impression. Keep observations from each site and session separate.

## Observation schedule

Record observations at the following nominal elapsed times, retaining actual
elapsed time when it differs:

| Phase | Nominal time |
|---|---:|
| Opening | immediately after application |
| Early top | 5 minutes |
| Heart | 30 minutes |
| Late heart | 2 hours |
| Drydown | 4 hours |
| Optional extended drydown | 8 hours |

An unobserved timepoint is `MISSING`; it is not zero and is not interpolated.

## Rating sheet

Use independent `0–10` ratings for each axis, where `0` means absent or wholly
unsatisfactory for that named axis and `10` means extremely strong or fully
satisfactory for that axis. The same assessor should keep the same anchor
interpretation across sessions.

| Axis | Question |
|---|---|
| Personal liking | How much do I like this smell at this moment? |
| Lavender identity | How clearly and naturally does the lavender identity read? |
| Amber balance | How well does the amber support rather than erase the lavender? |
| Architecture | Are opening, heart, and drydown legible and intentionally connected? |
| Structure/coherence | Does the formula feel supported, proportionate, and unified? |
| Perceived intensity | How strong is it at the evaluation distance? |
| Diffusion impression | How readily does it radiate from the application site? |
| Persistence impression | How much meaningful character remains? |
| Personal mass-appeal impression | How broadly wearable do I personally expect it to be? |
| Reasoned complexity | Are there multiple useful facets without pointless clutter? |
| Harshness/defect | How distracting are sharpness, muddiness, sourness, imbalance, or other defects? |

Also record a short free-text description at every timepoint. Ratings for
unlike axes must not be averaged or weighted into one score.

## Pairwise outcome when both samples exist

After completing the independent ratings, record exactly one outcome for each
predeclared comparison and timepoint:

```text
LEFT_PREFERRED
RIGHT_PREFERRED
TIE
MISSING
```

Then record a short reason linked to one or more named axes. A tie is a result,
not a failure. If preferences change across timepoints, preserve the trajectory
instead of forcing a single overall winner.

## Minimum repetition and decision boundary

The draft target is at least three usable sessions on separate days for a
personal pattern. Fewer sessions may be kept as notes but do not establish
repeatability. Strong disagreement among sessions, material condition drift,
or incomplete observations yields `NONDISCRIMINATING_OR_INCOMPLETE`, not a
forced preference.

Even a consistent personal preference supports only:

```text
personal_liking_state = OBSERVED_FOR_THIS_ASSESSOR_AND_CONDITION
population_liking     = NOT_ESTABLISHED
mass_appeal           = NOT_ESTABLISHED
formula_superiority   = NOT_ESTABLISHED_BEYOND_RECORDED_ENDPOINTS
safety                = NOT_ESTABLISHED
release               = NOT_AUTHORIZED
```

The existing canonical external-validation system may receive observations
only after its full protocol bindings and separate evidence-admission rules are
satisfied. This draft alone does not lock that protocol or authorize intake.
