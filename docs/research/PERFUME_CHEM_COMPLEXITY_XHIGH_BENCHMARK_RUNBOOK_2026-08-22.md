# Perfume-Chem Complexity xhigh Benchmark Runbook

**Status:** provider-free contracts verified; external benchmark requires the
execution gate below. This procedure compares plain ChatGPT xhigh with the same
model and effort receiving only the exact separated complexity bundle.

## Authority boundary

ChatGPT Pro work chats are advisory workers only. Their findings may motivate a
locally verified implementation decision but are not benchmark generations,
judges, source-admission authority, formula authority, or sensory evidence.
There is no DeepLuna provider transmission in this run.

Complexity means target-linked depth, coherent richness, temporal unfolding,
and potentially hedonic mechanisms that can be tested. It does not mean raw
ingredient, musk, module, interaction, descriptor, novelty, jargon, or prose
count. Software/model comparison cannot establish beauty or pleasure: physical liking remains NOT TESTED, as do physical similarity, stability, measured
headspace, safety, and release status unless separately measured.

## 1. Create one immutable run identity

Run these commands once in PowerShell from the repository root. Preserve the
same `$runId` and `$runDir` for every later operation.

```powershell
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ', [Globalization.CultureInfo]::InvariantCulture)
$suffix = (New-Guid).Guid.Replace('-', '').Substring(0, 8).ToLowerInvariant()
$runId = "CXB-$stamp-$suffix"
$runDir = "output/complexity_xhigh_benchmark/$runId"
python scripts/pipeline_audit.py complexity-benchmark --operation census --json
python scripts/pipeline_audit.py complexity-benchmark --operation prepare --run-dir $runDir --json
```

The required form is `CXB-YYYYMMDDTHHMMSSZ-` followed by eight lowercase
hexadecimal characters. Preparation must report `PASS`, 32 requests, 16 control
and 16 treatment arms, 32 unique nonces, and `provider_calls: 0`.

Verify the frozen corpus, rubric, registry, prompt, attachment, common-input,
and request hashes before transmission. For every pair, the common-input hash
must match and the treatment's only prompt delta must be `module_bundle`.

## 2. External execution gate

Before the first paid request, prove all of the following:

- actual product is ChatGPT and model identity is captured;
- reasoning effort is exactly `xhigh` for both arms;
- use one clean projectless conversation per request;
- no prior perfume, worker, benchmark-case, control, or treatment transcript is
  visible;
- exact prompt bytes and exact output bytes can be captured;
- a stable request or conversation ID and completion state are exposed; and
- each nonce is absent from accepted, in-flight, ambiguous, and terminal
  ledgers.

If any point is unprovable, stop and issue
`BENCHMARK_BLOCKED_UNVERIFIED_XHIGH`. Do not substitute another provider, model,
effort, context, or approximate receipt.

## 3. Execute the 32 sealed requests

Work in batches of at most four fresh conversations. Send only the exact prompt
payload and declared attachments from one request file. Never show either arm
the other response, a score, or reviewer feedback. Never reuse the four
advisory worker chats.

For each request, save:

- exact UTF-8 response bytes as `responses/<request_id>.json`;
- one execution receipt as `execution_receipts/<request_id>.json`;
- exact request ID and nonce;
- provider, product, model identity, and `xhigh` effort;
- clean-context and prior-transcript booleans;
- prompt, attachment, and response SHA-256 values;
- submitted/completed timestamps, terminal state, and conversation ID; and
- product-exposed token, latency, price, and accounting fields, or `null` when
  not exposed.

An ambiguous timeout is not permission for a second paid send. Look up the
stable ID; do not retry an ambiguous request. If it cannot be reconciled, mark
it `AMBIGUOUS`, block its pair, and stop aggregate scoring.

## 4. Validate and score

```powershell
python scripts/pipeline_audit.py complexity-benchmark --operation validate --run-dir $runDir --json
python scripts/pipeline_audit.py complexity-benchmark --operation score --run-dir $runDir --json
```

Validation requires 32 exact terminal receipts, zero duplicate nonces, zero
hash drift, and zero contaminated contexts. Scoring uses anonymous pairs, fixed
critical gates, and the frozen six-dimension rubric. Do not edit the cases,
rubric, prompts, or invariants after observing an output.

The treatment outperforms only with at least 12 wins, median paired gain at
least five, zero new critical failures, no category median regression below
-2, and valid receipts. The specified inconclusive band may be repeated once
only for disputed cases with new nonces and otherwise identical frozen bytes.

## 5. Ablate, repair once, or retire recoverably

Run ablation only after the full ensemble passes:

```powershell
python scripts/pipeline_audit.py complexity-benchmark --operation ablate --run-dir $runDir --json
```

Evaluate each family only on cases that declared it relevant before generation.
A capability must meet its gain or win-rate threshold; a guardrail must prevent
at least one critical failure. Zero relevant cases means
`NOT_EVALUATED_NO_RELEVANT_CASE`, not failure.

An underperformer gets at most one bounded repair at the diagnosed contract
locus, followed by its relevant frozen cases and four sealed unseen holdouts.
If it still fails, change its registry state to
`RETIRED_BENCHMARK_UNDERPERFORMER`, remove it from the active ensemble, and
preserve its exact source, tests, hashes, and ancestry. Retirement authorizes
no deletion. Tonalide, the inventory product Macrolide, and Musk Ketone remain
exception-only, omitted by default, and procurement-held in current builds.

## 6. Seal the local receipt

```powershell
python scripts/pipeline_audit.py complexity-benchmark --operation receipt --run-dir $runDir --json
```

The receipt must include exact corpus, rubric, registry, request, response, and
execution hashes; pair scores; telemetry state; aggregate decision; ablation,
repair, holdout, and registry decisions; preserved paths; zero deletion paths;
and all formula, inventory, physical, sensory, safety, and release authority
flags set to false.

If execution never clears the environment gate, write a blocked terminal
receipt instead of representing provider-free preparation as a model benchmark.
