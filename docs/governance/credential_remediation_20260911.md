# Credential remediation — tracked OpenAI API key files (2026-09-11)

## Finding

Two files containing OpenAI API keys were tracked in the canonical checkout
`D:\chatbots\perfume-chem` on branch `codex/astra`:

| Path | Size | sha256 fingerprint (first 16 hex) |
| --- | --- | --- |
| `incoming_review/openai-api-key.txt` | 164 bytes | `596ff5be13f3ae03` |
| `incoming_review/openai-api-key (1).txt` | 164 bytes | `0e22490b91a120c8` |

Contents were never read, copied, printed, or transmitted during this work. Only the fingerprints above
are recorded so the local files can be verified unchanged after the untracking.

Both paths were introduced by the single commit `e7002d4d` ("chore: add all remaining untracked files
(exclude LM-Studio.exe)"), which is the only commit in the repository's history that touches them
(`git log --all -- <paths>`).

## Reachability

- The repository `geminipro529-cloud/perfume-chem` is **private**: anonymous HTTPS requests to both the
  repository page and the REST API return 404, so the exposure is scoped to the account and anyone with
  repository access, not the public internet.
- `e7002d4d` **is on the remote**, as the tip of two refs:
  - `refs/heads/codex/add-inventory-materials`
  - `refs/pull/1/head` (a pull-request head ref)
- `e7002d4d` is **not an ancestor** of `codex/integration-20260909`
  (`git merge-base --is-ancestor e7002d4d HEAD` returns 1), and the integration branch never tracked
  those paths, so the integrated work does not carry them.

## Remediation applied

Canonical checkout, commit `df27d6cd` "Remove tracked API key files and ignore key material":

1. `git rm --cached -- "incoming_review/openai-api-key.txt" "incoming_review/openai-api-key (1).txt"`
   — untracked only. Both files remain on disk, byte-identical (fingerprints above re-verified after the
   commit), so they remain usable until rotation completes.
2. `.gitignore` gained `/incoming_review/openai-api-key*.txt`; `git check-ignore -v` resolves the rule at
   `.gitignore:117`, and `git add -A --dry-run` no longer sees the files.
3. The commit was made with an explicit pathspec so the checkout's pre-existing staged deletions (74
   entries, from the checkpoint restoration) were left untouched and still staged.

This integration tree carries the same ignore rule as a guard, and never tracked the files.

## Owner action required

**Rotate/revoke both keys at platform.openai.com.** Until rotation is completed, treat both as live.
Untracking and ignoring stop future propagation; they do not invalidate a key that already exists in the
remote's history. Status of this action: **PENDING as of this record** — the agent does not handle key
material.

## Decision recorded: keep history

The owner chose to keep the historical commit and rely on rotation. Deliberately not performed:

- No `git filter-repo`/BFG rewrite of `codex/add-inventory-materials`.
- No force-push.
- No pull-request surgery on PR #1.

Reasoning: rotation makes the residual bytes inert, GitHub does not release pull-request head refs to
client-side deletion, and a rewrite would invalidate every existing clone for no additional protection.
If the decision is ever revisited, the declined option is a mirror-clone rewrite of that one branch plus
a force-push, with the accepted caveats that `refs/pull/1/head` may persist server-side until GitHub
garbage-collects it, and that other clones must be re-cloned.

## Residual exposure statement

Revoked key material remains present in the private remote's history (the two refs above) and in any local
clone that fetched `codex/add-inventory-materials`. This is acceptable only while the keys are revoked.

## Verification recorded

- `git ls-files -- 'incoming_review/openai-api-key*'` in the canonical checkout: empty.
- `git check-ignore -v` in both trees: resolves to the new rule.
- Local files: both still 164 bytes with unchanged fingerprints.
- Canonical index: still exactly 74 staged deletions; checkout HEAD `df27d6cd`; stash `2851b5f7` intact.
