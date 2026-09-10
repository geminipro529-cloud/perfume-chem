import assert from "node:assert/strict";
import test from "node:test";

import { isDeterministicContractError } from "../.opencode/upgrades/CL-ORCH-UPGRADE-20260807-V1/candidate/runtime/lib/candidate-runtime.mjs";

test("required-read overflow is deterministic before transmission", () => {
  const error = new Error(
    "required_reads selected UTF-8 evidence 191523 bytes exceeds 15360-byte cap; split the task",
  );

  assert.equal(isDeterministicContractError(error), true);
});

test("required-read overflow text cannot relabel a transmitted failure", () => {
  const error = new Error(
    "required_reads selected UTF-8 evidence 191523 bytes exceeds 15360-byte cap; split the task",
  );
  error.transmitted = true;

  assert.equal(isDeterministicContractError(error), false);
});

test("explicit deterministic contract codes remain supported", () => {
  const error = new Error("request rejected");
  error.code = "CONTRACT_422";
  error.deterministic = true;

  assert.equal(isDeterministicContractError(error), true);
  assert.equal(isDeterministicContractError(new Error("filesystem unavailable")), false);
});
