# Skill: cheapluna-literature-review

# CheapLuna Fast bounded delegation

Use CheapLuna only for bounded mechanical reads or frozen, host-verified leaf
writes. The active OpenCode head retains architecture, perfume interpretation,
scope, security, provenance, and final acceptance.

## Hard routing boundary

- Never use Codex subagents.
- Run a fresh `deepseek_check` for `perfume-chem-cheapluna` before transmission.
- Accept only `READY` with zero unknown reservations and coherent capacity.
- Use `tier=FLASH`, `allowed_routes=["FLASH"]`, and `fallback_policy="NO_LUNA"`.
- Set `maximum_attempts=1`, `maximum_provider_calls=1`, and
  `maximum_estimated_cost_usd<=0.01`.
- Never route to PRO, DIRECT_PRO, V4_PRO, NEMOTRON, GLM, LUNA, SOL, Codex, or
  another project.
- Never retry a deterministic admission, provider-schema, or transport failure.

## Read delegation

Use `deepseek_read_submit` for one bounded `READ_ONLY` task with exact
`allowed_paths`, `required_reads`, forbidden actions, done criteria, and a
compact required output. Use `deepseek_batch_submit` only for independent
read-only nodes and keep physical concurrency within the Fast pool.

## Write delegation

Use `deepseek_write_submit` only when all of these are frozen:

1. One writer owns the project.
2. `allowed_paths` is explicit, nonempty, and contains only mutation targets.
3. `required_reads` are immutable evidence inputs.
4. Archive and transactional rollback behavior are required.
5. At least one host verifier independently checks the staged result.
6. The active OpenCode head inspects and accepts the final diff.

Provider text never expands scientific, safety, inventory, formula, publication,
or release authority.

## Failure handling

Return the exact local or provider failure class, durable job identifier when
available, token/cost accounting, and whether any file changed. Fail closed on
uncertainty. Do not substitute another worker or Codex path.
