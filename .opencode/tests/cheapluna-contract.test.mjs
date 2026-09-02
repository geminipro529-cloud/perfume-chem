import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

import {
  inspectRequiredReads,
  minimumRepositoryInputTokens,
  planRequiredReadShards,
  prepareDeepLunaInput,
  prepareDeepLunaShardPlan,
} from "../scripts/cheapluna-contract.mjs";
import { CheapLunaBudgetGuard } from "../plugins/cheapluna-budget-guard.js";
import {
  CHEAPLUNA_BUILD,
  SERVER_PATH,
  runStartupCanaryOnce,
} from "../scripts/cheapluna-chat-launcher.mjs";

function withWorkspace(run) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "cheapluna-contract-"));
  try {
    const result = run(root);
    if (result && typeof result.then === "function") {
      return result.finally(() => fs.rmSync(root, { recursive: true, force: true }));
    }
    fs.rmSync(root, { recursive: true, force: true });
    return result;
  } catch (error) {
    fs.rmSync(root, { recursive: true, force: true });
    throw error;
  }
}

test("runs one startup canary per exact daemon boot", () => {
  withWorkspace((root) => {
    let calls = 0;
    const health = {
      process_boot_id: "DI-0123456789abcdef0123456789abcdef",
      project_id: "perfume-chem-cheapluna-isolated",
      readiness: "READY",
      circuits: { provider_calls_enabled: true },
      budget: { unknown_reservations: 0, open_reserved_nano_usd: 0 },
      capacity: { active_reads: 0, active_writes: 0, queued: 0 },
    };
    const spawnCanary = () => {
      calls += 1;
      return {
        status: 0,
        stdout:
          '{"job_id":"DS-0123456789abcdef0123456789abcdef",' +
          '"status":"PASS","positive_findings":["DEEPLUNA_CHAT_CANARY_OK"]}',
        stderr: "",
      };
    };

    const first = runStartupCanaryOnce({
      environment: {},
      health,
      stateRoot: root,
      spawnCanary,
      now: () => 123,
    });
    const second = runStartupCanaryOnce({
      environment: {},
      health,
      stateRoot: root,
      spawnCanary,
      now: () => 456,
    });

    assert.equal(first.status, "PASS");
    assert.equal(first.reused, false);
    assert.equal(second.status, "PASS");
    assert.equal(second.reused, true);
    assert.equal(calls, 1);
  });
});

test("startup canary fails closed before transmission when health is blocked", () => {
  withWorkspace((root) => {
    let calls = 0;
    const result = runStartupCanaryOnce({
      environment: {},
      health: {
        process_boot_id: "DI-fedcba9876543210fedcba9876543210",
        project_id: "perfume-chem-cheapluna-isolated",
        readiness: "BLOCKED",
        circuits: { provider_calls_enabled: false },
        budget: { unknown_reservations: 1, open_reserved_nano_usd: 1 },
        capacity: { active_reads: 0, active_writes: 0, queued: 0 },
      },
      stateRoot: root,
      spawnCanary: () => {
        calls += 1;
        return { status: 0, stdout: "", stderr: "" };
      },
    });

    assert.equal(result.status, "BLOCKED");
    assert.equal(result.provider_transmission_attempted, false);
    assert.equal(calls, 0);
  });
});

test("splits a 401-line required read before provider submission", () => {
  withWorkspace((root) => {
    fs.writeFileSync(
      path.join(root, "evidence.txt"),
      Array.from({ length: 401 }, (_, index) => `L${index + 1}`).join("\n"),
      "utf8",
    );
    const raw = {
      task_id: "chunk-canary",
      tier: "PRO",
      max_output_tokens: 3000,
      required_reads: [
        { path: "evidence.txt", unit: "line", start: 1, end: 401 },
      ],
      route_constraints: {
        allowed_routes: ["DIRECT_PRO"],
        fallback_policy: "NO_LUNA",
        maximum_attempts: 1,
        maximum_provider_calls: 2,
        maximum_estimated_cost_usd: 0.08,
      },
    };

    const prepared = prepareDeepLunaInput(raw, { root });

    assert.deepEqual(prepared.input.required_reads, [
      { path: "evidence.txt", unit: "line", start: 1, end: 400 },
      { path: "evidence.txt", unit: "line", start: 401, end: 401 },
    ]);
    assert.equal(prepared.inspection.changed, true);
    assert.equal(raw.required_reads.length, 1, "caller input must remain unchanged");
  });
});

test("resolves end null and merges duplicate or adjacent ranges", () => {
  withWorkspace((root) => {
    fs.writeFileSync(path.join(root, "evidence.txt"), "one\ntwo\nthree\n", "utf8");

    const inspected = inspectRequiredReads([
      { path: "evidence.txt", unit: "line", start: 1, end: 2 },
      { path: "evidence.txt", unit: "line", start: 2, end: null },
    ], { root });

    assert.deepEqual(inspected.requiredReads, [
      { path: "evidence.txt", unit: "line", start: 1, end: 4 },
    ]);
  });
});

test("rejects selected evidence above the bounded Chat budget", () => {
  withWorkspace((root) => {
    fs.writeFileSync(
      path.join(root, "large.txt"),
      Array.from({ length: 401 }, () => "x".repeat(100)).join("\n"),
      "utf8",
    );

    assert.throws(
      () => inspectRequiredReads([
        { path: "large.txt", unit: "line", start: 1, end: 401 },
      ], { root }),
      /exceeds 15360-byte cap/,
    );
  });
});

test("plans exhaustive deterministic Chat shards instead of dropping oversized evidence", () => {
  withWorkspace((root) => {
    const lineCount = 240;
    fs.writeFileSync(
      path.join(root, "large.txt"),
      Array.from({ length: lineCount }, (_, index) =>
        `${String(index + 1).padStart(3, "0")}:${"x".repeat(157)}`
      ).join("\n"),
      "utf8",
    );
    const reads = [{ path: "large.txt", unit: "line", start: 1, end: lineCount }];

    const first = planRequiredReadShards(reads, { root });
    const second = planRequiredReadShards(reads, { root });

    assert.deepEqual(second, first, "the same evidence must produce the same shard plan");
    assert.ok(first.shards.length >= 3, "the fixture must cross the per-worker byte ceiling");
    const covered = [];
    for (const shard of first.shards) {
      assert.ok(shard.selectedBytes <= 15 * 1024);
      for (const read of shard.requiredReads) {
        assert.ok(read.end - read.start + 1 <= 400);
        for (let line = read.start; line <= read.end; line += 1) covered.push(line);
      }
    }
    assert.deepEqual(covered, Array.from({ length: lineCount }, (_, index) => index + 1));
    assert.equal(new Set(covered).size, lineCount, "no line may overlap another shard");
  });
});

test("prepares independently admissible DIRECT_PRO shard tasks under one cost gate", () => {
  withWorkspace((root) => {
    const lineCount = 240;
    fs.writeFileSync(
      path.join(root, "large.txt"),
      Array.from({ length: lineCount }, () => "y".repeat(160)).join("\n"),
      "utf8",
    );
    const raw = {
      task_id: "large-audit",
      objective: "Audit all supplied evidence.",
      tier: "PRO",
      max_output_tokens: 3000,
      required_reads: [
        { path: "large.txt", unit: "line", start: 1, end: lineCount },
      ],
      route_constraints: {
        allowed_routes: ["DIRECT_PRO"],
        fallback_policy: "NO_LUNA",
        maximum_attempts: 1,
        maximum_provider_calls: 2,
        maximum_input_tokens: 48_000,
        maximum_cached_input_tokens: 32_000,
        maximum_output_tokens_total: 6_000,
        maximum_total_tokens: 54_000,
        maximum_estimated_cost_usd: 0.08,
      },
    };

    const plan = prepareDeepLunaShardPlan(raw, { root });

    assert.ok(plan.shardCount >= 3);
    assert.ok(plan.maximumEstimatedCostUsd <= 0.08);
    assert.equal(plan.shards.length, plan.shardCount);
    assert.equal(raw.task_id, "large-audit", "caller input must remain unchanged");
    for (const [index, shard] of plan.shards.entries()) {
      assert.equal(shard.ordinal, index + 1);
      assert.equal(shard.count, plan.shardCount);
      assert.match(shard.input.task_id, new RegExp(`-s${index + 1}-of-${plan.shardCount}$`));
      assert.match(shard.input.objective, new RegExp(`Evidence shard ${index + 1}/${plan.shardCount}`));
      assert.deepEqual(shard.input.route_constraints.allowed_routes, ["DIRECT_PRO"]);
      assert.equal(shard.input.route_constraints.fallback_policy, "NO_LUNA");
      assert.equal(shard.input.route_constraints.maximum_attempts, 1);
      assert.equal(shard.input.route_constraints.maximum_provider_calls, 2);
      inspectRequiredReads(shard.input.required_reads, { root });
    }
  });
});

test("keeps deterministic shard task identifiers within the daemon 64-character limit", () => {
  withWorkspace((root) => {
    fs.writeFileSync(
      path.join(root, "large.txt"),
      Array.from({ length: 220 }, () => "i".repeat(160)).join("\n"),
      "utf8",
    );
    const raw = {
      task_id: "a".repeat(64),
      objective: "Inspect all evidence.",
      tier: "PRO",
      max_output_tokens: 3000,
      required_reads: [{ path: "large.txt", unit: "line", start: 1, end: 220 }],
      route_constraints: {
        allowed_routes: ["DIRECT_PRO"],
        fallback_policy: "NO_LUNA",
        maximum_attempts: 1,
        maximum_provider_calls: 2,
        maximum_input_tokens: 48_000,
        maximum_cached_input_tokens: 32_000,
        maximum_output_tokens_total: 6_000,
        maximum_total_tokens: 54_000,
        maximum_estimated_cost_usd: 0.08,
      },
    };

    const first = prepareDeepLunaShardPlan(raw, { root });
    const second = prepareDeepLunaShardPlan(raw, { root });
    const identifiers = first.shards.map((shard) => shard.input.task_id);

    assert.ok(identifiers.every((taskId) => taskId.length <= 64));
    assert.equal(new Set(identifiers).size, identifiers.length);
    assert.deepEqual(
      second.shards.map((shard) => shard.input.task_id),
      identifiers,
    );
  });
});

test("refuses an indivisible UTF-8 line above the worker evidence ceiling", () => {
  withWorkspace((root) => {
    fs.writeFileSync(path.join(root, "one-line.txt"), "z".repeat(15 * 1024 + 1), "utf8");

    assert.throws(
      () => planRequiredReadShards([
        { path: "one-line.txt", unit: "line", start: 1, end: 1 },
      ], { root }),
      (error) => {
        assert.equal(error.code, "UNSHARDABLE_REQUIRED_READ_LINE");
        assert.match(
          error.message,
          /path=one-line\.txt line=1 bytes=15361 cap=15360/,
        );
        return true;
      },
    );
  });
});

test("CLI plan is provider-free and exposes the complete shard coverage", () => {
  withWorkspace((root) => {
    fs.writeFileSync(
      path.join(root, "large.txt"),
      Array.from({ length: 220 }, () => "q".repeat(160)).join("\n"),
      "utf8",
    );
    const requestPath = path.join(root, "request.json");
    fs.writeFileSync(requestPath, JSON.stringify({
      task_id: "provider-free-plan",
      objective: "Inspect every supplied line.",
      tier: "PRO",
      max_output_tokens: 3000,
      required_reads: [{ path: "large.txt", unit: "line", start: 1, end: 220 }],
      route_constraints: {
        allowed_routes: ["DIRECT_PRO"],
        fallback_policy: "NO_LUNA",
        maximum_attempts: 1,
        maximum_provider_calls: 2,
        maximum_input_tokens: 48_000,
        maximum_cached_input_tokens: 32_000,
        maximum_output_tokens_total: 6_000,
        maximum_total_tokens: 54_000,
        maximum_estimated_cost_usd: 0.08,
      },
    }), "utf8");
    const env = { ...process.env, DEEPSEEK_ALLOWED_ROOT: root };
    delete env.CHEAPLUNA_SERVER;

    const result = spawnSync(
      process.execPath,
      [path.resolve(".opencode/scripts/cheapluna-cli.mjs"), "plan", requestPath],
      { cwd: path.resolve("."), env, encoding: "utf8" },
    );

    assert.equal(result.status, 0, result.stderr);
    const output = JSON.parse(result.stdout);
    assert.equal(output.execution, "CLIENT_FANOUT_EVIDENCE_SHARDS");
    assert.ok(output.shard_count >= 3);
    assert.equal(output.shards.length, output.shard_count);
    assert.deepEqual(
      output.shards.flatMap((shard) => shard.required_reads),
      planRequiredReadShards(
        [{ path: "large.txt", unit: "line", start: 1, end: 220 }],
        { root },
      ).shards.flatMap((shard) => shard.requiredReads),
    );
  });
});

test("rejects path traversal before reading evidence", () => {
  withWorkspace((root) => {
    assert.throws(
      () => inspectRequiredReads([
        { path: "../outside.txt", unit: "line", start: 1, end: 1 },
      ], { root }),
      /outside workspace/,
    );
  });
});

test("rejects a runtime-invalid output token floor before admission", () => {
  withWorkspace((root) => {
    assert.throws(
      () => prepareDeepLunaInput({
        tier: "PRO",
        max_output_tokens: 2500,
        required_reads: [],
        route_constraints: {
          allowed_routes: ["DIRECT_PRO"],
          fallback_policy: "NO_LUNA",
          maximum_attempts: 1,
          maximum_provider_calls: 1,
          maximum_estimated_cost_usd: 0.01,
        },
      }, { root }),
      /between 3000 and 8192/,
    );
  });
});

test("rejects provider fallback routes before admission", () => {
  withWorkspace((root) => {
    assert.throws(
      () => prepareDeepLunaInput({
        tier: "PRO",
        max_output_tokens: 3000,
        required_reads: [],
        route_constraints: {
          allowed_routes: ["DIRECT_PRO", "FLASH"],
          fallback_policy: "NO_LUNA",
          maximum_attempts: 1,
          maximum_provider_calls: 1,
          maximum_estimated_cost_usd: 0.01,
        },
      }, { root }),
      /only DIRECT_PRO/,
    );
  });
});

test("rejects one-call repository work before admission", () => {
  withWorkspace((root) => {
    fs.writeFileSync(path.join(root, "evidence.txt"), "evidence\n", "utf8");
    assert.throws(
      () => prepareDeepLunaInput({
        tier: "PRO",
        max_output_tokens: 3000,
        allowed_paths: ["evidence.txt"],
        required_reads: [
          { path: "evidence.txt", unit: "line", start: 1, end: 1 },
        ],
        route_constraints: {
          allowed_routes: ["DIRECT_PRO"],
          fallback_policy: "NO_LUNA",
          maximum_attempts: 1,
          maximum_provider_calls: 1,
          maximum_output_tokens_total: 6000,
          maximum_estimated_cost_usd: 0.08,
        },
      }, { root }),
      /repository work requires exactly 2 provider calls/,
    );
  });
});

test("rejects an aggregate output ceiling that cannot fund both repository turns", () => {
  withWorkspace((root) => {
    fs.writeFileSync(path.join(root, "evidence.txt"), "evidence\n", "utf8");
    assert.throws(
      () => prepareDeepLunaInput({
        tier: "PRO",
        max_output_tokens: 3000,
        allowed_paths: ["evidence.txt"],
        required_reads: [
          { path: "evidence.txt", unit: "line", start: 1, end: 1 },
        ],
        route_constraints: {
          allowed_routes: ["DIRECT_PRO"],
          fallback_policy: "NO_LUNA",
          maximum_attempts: 1,
          maximum_provider_calls: 2,
          maximum_output_tokens_total: 3000,
          maximum_estimated_cost_usd: 0.08,
        },
      }, { root }),
      /maximum_output_tokens_total >= 6000/,
    );
  });
});

test("auto-sizes an undersized repository input envelope before transmission", () => {
  withWorkspace((root) => {
    const evidence = "x".repeat(10_980);
    fs.writeFileSync(path.join(root, "evidence.txt"), evidence, "utf8");
    const prepared = prepareDeepLunaInput({
      tier: "PRO",
      max_output_tokens: 4000,
      allowed_paths: ["evidence.txt"],
      required_reads: [
        { path: "evidence.txt", unit: "line", start: 1, end: 1 },
      ],
      route_constraints: {
        allowed_routes: ["DIRECT_PRO"],
        fallback_policy: "NO_LUNA",
        maximum_attempts: 1,
        maximum_provider_calls: 2,
        maximum_input_tokens: 24_000,
        maximum_cached_input_tokens: 16_000,
        maximum_output_tokens_total: 8_000,
        maximum_total_tokens: 32_000,
        maximum_estimated_cost_usd: 0.08,
      },
    }, { root });

    const expectedFloor = minimumRepositoryInputTokens({
      selectedBytes: Buffer.byteLength(evidence),
      commandCount: 0,
    });
    assert.equal(
      prepared.input.route_constraints.maximum_input_tokens,
      expectedFloor,
    );
    assert.equal(
      prepared.input.route_constraints.maximum_total_tokens,
      expectedFloor + 8_000,
    );
  });
});

test("accounts for bounded command output and fails closed above the cost cap", () => {
  withWorkspace((root) => {
    fs.writeFileSync(path.join(root, "evidence.txt"), "evidence\n", "utf8");
    assert.throws(
      () => prepareDeepLunaInput({
        tier: "PRO",
        max_output_tokens: 4000,
        allowed_paths: ["evidence.txt"],
        required_reads: [
          { path: "evidence.txt", unit: "line", start: 1, end: 1 },
        ],
        commands_tests: ["test-one", "test-two"],
        route_constraints: {
          allowed_routes: ["DIRECT_PRO"],
          fallback_policy: "NO_LUNA",
          maximum_attempts: 1,
          maximum_provider_calls: 2,
          maximum_input_tokens: 22_000,
          maximum_cached_input_tokens: 16_000,
          maximum_output_tokens_total: 8_000,
          maximum_total_tokens: 30_000,
          maximum_estimated_cost_usd: 0.01,
        },
      }, { root }),
      /split the task/,
    );
  });
});

test("runtime autosizes the same repository envelope before provider admission", async () => {
  await withWorkspace(async (root) => {
    const evidence = "x".repeat(5_979);
    const evidencePath = path.join(root, "evidence.txt");
    fs.writeFileSync(evidencePath, evidence, "utf8");
    const { applyRepositoryInputAutosizing } = await import(
      `${pathToFileURL(SERVER_PATH).href}?autosize=${Date.now()}`
    );
    const sized = applyRepositoryInputAutosizing({
      workspace: fs.realpathSync(root),
      allowedPaths: ["evidence.txt"],
      requiredReads: [
        { path: "evidence.txt", unit: "line", start: 1, end: 1 },
      ],
      commandsTests: [],
      mode: "READ_ONLY",
      primaryProfile: "cheapluna-chat",
      packedEvidenceMode: null,
      routeConstraints: {
        allowedRoutes: ["DIRECT_PRO"],
        maximumInputTokens: 24_000,
        maximumCachedInputTokens: 16_000,
        maximumOutputTokensTotal: 8_000,
        maximumTotalTokens: 32_000,
        maximumEstimatedCostUsd: 0.08,
      },
    });

    assert.equal(sized.repositoryInputAutoSized, true);
    assert.equal(
      sized.routeConstraints.maximumInputTokens,
      minimumRepositoryInputTokens({
        selectedBytes: Buffer.byteLength(evidence),
        commandCount: 0,
      }),
    );
    assert.equal(
      sized.routeConstraints.maximumTotalTokens,
      sized.routeConstraints.maximumInputTokens + 8_000,
    );

    fs.writeFileSync(path.join(root, "large.txt"), "x".repeat(15 * 1024 + 1), "utf8");
    assert.throws(
      () => applyRepositoryInputAutosizing({
        ...sized,
        allowedPaths: ["large.txt"],
        requiredReads: [
          { path: "large.txt", unit: "line", start: 1, end: 1 },
        ],
      }),
      /exceeds 15360-byte cap/,
    );
  });
});

test("MCP budget hook rejects an unchunked range before transmission", async () => {
  await withWorkspace(async (root) => {
    fs.writeFileSync(
      path.join(root, "evidence.txt"),
      Array.from({ length: 401 }, (_, index) => `L${index + 1}`).join("\n"),
      "utf8",
    );
    const hook = await CheapLunaBudgetGuard({ directory: root });

    await assert.rejects(
      () => hook["tool.execute.before"](
        { tool: "cheapluna_deepseek_read_submit" },
        {
          args: {
            max_output_tokens: 3000,
            required_reads: [
              { path: "evidence.txt", unit: "line", start: 1, end: 401 },
            ],
            route_constraints: {
              allowed_routes: ["DIRECT_PRO"],
              fallback_policy: "NO_LUNA",
              maximum_attempts: 1,
              maximum_provider_calls: 2,
              maximum_estimated_cost_usd: 0.08,
            },
          },
        },
      ),
      /required_reads must be explicit, merged, and <=400 lines each/,
    );
  });
});

test("MCP budget hook accepts an explicit two-call chunked contract", async () => {
  await withWorkspace(async (root) => {
    fs.writeFileSync(
      path.join(root, "evidence.txt"),
      Array.from({ length: 401 }, (_, index) => `L${index + 1}`).join("\n"),
      "utf8",
    );
    const hook = await CheapLunaBudgetGuard({ directory: root });

    await hook["tool.execute.before"](
      { tool: "cheapluna_deepseek_read_submit" },
      {
        args: {
          max_output_tokens: 3000,
          required_reads: [
            { path: "evidence.txt", unit: "line", start: 1, end: 400 },
            { path: "evidence.txt", unit: "line", start: 401, end: 401 },
          ],
          route_constraints: {
            allowed_routes: ["DIRECT_PRO"],
            fallback_policy: "NO_LUNA",
            maximum_attempts: 1,
            maximum_provider_calls: 2,
            maximum_output_tokens_total: 6000,
            maximum_estimated_cost_usd: 0.08,
          },
        },
      },
    );
  });
});

test("MCP single-submit names the safe Chat fanout route for oversized evidence", async () => {
  await withWorkspace(async (root) => {
    fs.writeFileSync(
      path.join(root, "large.txt"),
      Array.from({ length: 240 }, () => "r".repeat(160)).join("\n"),
      "utf8",
    );
    const hook = await CheapLunaBudgetGuard({ directory: root });

    await assert.rejects(
      () => hook["tool.execute.before"](
        { tool: "cheapluna_deepseek_read_submit" },
        {
          args: {
            task_id: "large-mcp-read",
            max_output_tokens: 3000,
            required_reads: [
              { path: "large.txt", unit: "line", start: 1, end: 240 },
            ],
            route_constraints: {
              allowed_routes: ["DIRECT_PRO"],
              fallback_policy: "NO_LUNA",
              maximum_attempts: 1,
              maximum_provider_calls: 2,
              maximum_output_tokens_total: 6000,
              maximum_estimated_cost_usd: 0.08,
            },
          },
        },
      ),
      /safely shardable into 3 READ_ONLY Chat tasks.*cheapluna-cli\.mjs plan.*submit/s,
    );
  });
});

test("MCP single-submit exposes an indivisible oversized line without truncation", async () => {
  await withWorkspace(async (root) => {
    fs.writeFileSync(path.join(root, "one-line.txt"), "s".repeat(15 * 1024 + 1), "utf8");
    const hook = await CheapLunaBudgetGuard({ directory: root });

    await assert.rejects(
      () => hook["tool.execute.before"](
        { tool: "cheapluna_deepseek_read_submit" },
        {
          args: {
            task_id: "one-line-mcp-read",
            max_output_tokens: 3000,
            required_reads: [
              { path: "one-line.txt", unit: "line", start: 1, end: 1 },
            ],
            route_constraints: {
              allowed_routes: ["DIRECT_PRO"],
              fallback_policy: "NO_LUNA",
              maximum_attempts: 1,
              maximum_provider_calls: 2,
              maximum_output_tokens_total: 6000,
              maximum_estimated_cost_usd: 0.08,
            },
          },
        },
      ),
      /UNSHARDABLE_REQUIRED_READ_LINE path=one-line\.txt line=1 bytes=15361 cap=15360/,
    );
  });
});

test("daemon-backed batch nodes use five isolated clients", async () => {
  await withWorkspace(async (root) => {
    const { BatchManager } = await import(pathToFileURL(SERVER_PATH).href);
    const batchesRoot = path.join(root, "batches");
    let active = 0;
    let maximumActive = 0;
    let created = 0;
    let closed = 0;
    const parent = {
      daemonBacked: true,
      client: {},
      baseStoreRoot: root,
      storeRoot: root,
      projectId: "perfume-chem-cheapluna-isolated",
      projectRoot: root,
      origin: { origin_id: 1 },
      batchesRoot,
      retentionDays: 1,
      nowFunction: Date.now,
      apiKey: "",
      daemonContext: {},
      primaryProfile: {},
      codexOrchestrationEnabled: false,
      readerPoolPolicy: {
        fastOnly: false,
        mode: "DYNAMIC",
        readLimit: 5,
        writeLimit: 1,
        logicalLimit: 5,
        ownerProjectId: null,
      },
    };
    const manager = new BatchManager(parent, {
      pollDelayMs: 1,
      readerPoolPolicy: { fastOnly: false, mode: "DYNAMIC", readLimit: 5 },
      daemonNodeManagerFactory: async () => {
        created += 1;
        return {
          manager: {
            async submit() {
              active += 1;
              maximumActive = Math.max(maximumActive, active);
              await new Promise((resolve) => setTimeout(resolve, 25));
              active -= 1;
              return {
                status: "PASS",
                execution_status: "ACCEPTED",
                evidence_verdict: "POSITIVE",
                cache_hit: false,
                summary: "isolated-pass",
              };
            },
            async status() {
              throw new Error("terminal submission must not be polled");
            },
          },
          async close() {
            closed += 1;
          },
        };
      },
    });
    const nodes = Array.from({ length: 5 }, (_, index) => ({
      node_id: `node-${index}`,
      depends_on: [],
      accepted_evidence_verdicts: ["POSITIVE"],
      status: "PENDING",
      execution_status: null,
      evidence_verdict: "UNRESOLVED",
      job_id: null,
      cache_hit: false,
      summary: "",
      result_path: null,
    }));
    const state = {
      batch_id: "isolated-five",
      status: "RUNNING",
      concurrency: 5,
      worker_job_durability: "DURABLE_DAEMON",
      control_state_lifecycle: "CLIENT_LIFETIME_EPHEMERAL_WITH_LOCAL_CHECKPOINTS",
      restart_durable_orchestration: false,
      daemon_batch_rpc_active: false,
      submitted_at: new Date().toISOString(),
      finished_at: null,
      manifest_path: path.join(batchesRoot, "manifest.json"),
      nodes,
    };
    fs.mkdirSync(batchesRoot, { recursive: true });
    await Promise.all(
      nodes.map((node) => manager.runNode(node, { input: {} }, state, batchesRoot)),
    );
    assert.equal(created, 5);
    assert.equal(maximumActive, 5);
    assert.equal(closed, 5);
    assert.deepEqual(nodes.map((node) => node.status), Array(5).fill("PASS"));
  });
});

test("non-Fast Chat execution honors the configured 50-reader and 10-writer capacity", async () => {
  const capacityPath = path.join(
    path.dirname(SERVER_PATH),
    "lib",
    "capacity-policy.mjs",
  );
  const {
    WeightedFairScheduler,
    resolveCapacityPolicy,
  } = await import(pathToFileURL(capacityPath).href);
  const policy = resolveCapacityPolicy({
    fastOnly: false,
    readLimit: 50,
    writeLimit: 10,
  });
  assert.equal(policy.pools["deepluna-read"].capacity, 50);
  assert.equal(policy.pools["deepluna-write"].capacity, 10);
  const scheduler = new WeightedFairScheduler(policy);
  for (let index = 0; index < 50; index += 1) {
    scheduler.enqueue({
      jobId: `job-${index}`,
      taskId: `task-${index}`,
      poolId: "deepluna-read",
      priority: 0,
      createdAtMs: index,
    });
  }
  for (let index = 0; index < 50; index += 1) {
    assert.ok(scheduler.dispatchNext("deepluna-read"));
  }
  assert.equal(scheduler.snapshot().pools["deepluna-read"].running, 50);
  assert.equal(scheduler.dispatchNext("deepluna-read"), null);
  assert.throws(
    () => resolveCapacityPolicy({ fastOnly: false, readLimit: 51 }),
    /reader limit must be between 1 and 50/,
  );
});

test("production daemon accepts fifty isolated reader clients without exhausting control sockets", async () => {
  await withWorkspace(async (root) => {
    const runtime = await import(pathToFileURL(SERVER_PATH).href);
    const workspace = path.join(root, "workspace");
    const storeRoot = path.join(root, "store");
    const projectId = `capacity-test-${process.pid}-${Date.now()}`;
    const previousProfile = process.env.DEEPLUNA_PRIMARY_PROFILE;
    const clients = [];
    let daemon = null;
    fs.mkdirSync(workspace);
    process.env.DEEPLUNA_PRIMARY_PROFILE = "cheapluna-chat";
    try {
      daemon = await runtime.createProductionCandidateDaemon({
        storeRoot,
        projectId,
        workspace,
        projectScope: "project",
        projectCeilingNanoUsd: 1_000_000,
        primaryProfile: runtime.resolvePrimaryProfile("cheapluna-chat"),
        readerPoolPolicy: {
          fastOnly: false,
          mode: "DYNAMIC",
          readLimit: 50,
          writeLimit: 10,
          logicalLimit: 50,
          ownerProjectId: null,
        },
        apiKey: "test-key",
        headProducerEnabled: false,
      });
      await daemon.start();
      clients.push(...await Promise.all(
        Array.from({ length: 50 }, () =>
          runtime.connectProductionCandidateDaemon({
            storeRoot,
            projectId,
            workspace,
            timeoutMs: 10_000,
          })
        ),
      ));
      const health = await clients[0].request("health", {});
      assert.equal(clients.length, 50);
      assert.equal(health.capacity.read_limit, 50);
      assert.equal(health.capacity.write_limit, 10);
      assert.equal(health.runtime_build_hash, CHEAPLUNA_BUILD);
    } finally {
      for (const client of clients) client.close();
      if (daemon !== null) await daemon.stop();
      if (previousProfile === undefined) {
        delete process.env.DEEPLUNA_PRIMARY_PROFILE;
      } else {
        process.env.DEEPLUNA_PRIMARY_PROFILE = previousProfile;
      }
    }
  });
});
