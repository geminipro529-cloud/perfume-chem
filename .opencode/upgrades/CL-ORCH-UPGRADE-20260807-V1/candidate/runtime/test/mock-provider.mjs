// Deterministic mock provider (P5B). OpenAI/DeepSeek-compatible chat completions.
// Captures every request; serves a configurable deterministic scenario sequence.
// Control endpoints: POST /__control {scenario} | GET /__capture | GET /__reset.
import http from "node:http";

// Complete worker handoff per candidate contract final_json_keys (status, summary,
// files_inspected, files_changed, commands_run, tests, positive_findings,
// negative_findings, scientific_uncertainty, architecture_uncertainty,
// scope_deviation, residual_risks, recommended_next_action, execution_status,
// evidence_verdict). Fixtures MUST return a schema-complete handoff or the daemon
// marks the job INCOMPLETE.
function completeHandoff(overrides = {}) {
  return {
    status: "PASS",
    summary: "mock deterministic answer",
    files_inspected: [],
    files_changed: [],
    commands_run: [],
    tests: [],
    positive_findings: [],
    negative_findings: [],
    scientific_uncertainty: false,
    architecture_uncertainty: false,
    scope_deviation: false,
    residual_risks: [],
    recommended_next_action: "none",
    execution_status: "ACCEPTED",
    evidence_verdict: "NOT_APPLICABLE",
    ...overrides,
  };
}

const FIXTURES = {
  FAST_CONTENT: (body) => ({
    id: "mock-chatcmpl-1", object: "chat.completion", created: 1, model: body.model,
    choices: [{ index: 0, message: { role: "assistant", content: JSON.stringify(completeHandoff({ summary: "mock fast answer" })) }, finish_reason: "stop" }],
    usage: { prompt_tokens: 10, completion_tokens: 20, total_tokens: 30, prompt_cache_hit_tokens: 0, prompt_cache_miss_tokens: 10 },
  }),
  THINKING_CONTENT: (body) => ({
    id: "mock-chatcmpl-2", object: "chat.completion", created: 2, model: body.model,
    choices: [{ index: 0, message: { role: "assistant", content: JSON.stringify(completeHandoff({ summary: "mock thinking answer", evidence_verdict: "POSITIVE" })), reasoning_content: "mock reasoning trace" }, finish_reason: "stop" }],
    usage: { prompt_tokens: 20, completion_tokens: 40, total_tokens: 60, prompt_cache_hit_tokens: 0, prompt_cache_miss_tokens: 20, completion_tokens_details: { reasoning_tokens: 15 } },
  }),
  THINKING_TOOL_CALL: (body) => ({
    id: "mock-chatcmpl-3", object: "chat.completion", created: 3, model: body.model,
    choices: [{ index: 0, message: { role: "assistant", content: null, reasoning_content: "mock tool reasoning", tool_calls: [{ id: "call_mock_1", type: "function", function: { name: "read_file", arguments: JSON.stringify({ path: "inventory.txt", start_line: 1, end_line: 5 }) } }] }, finish_reason: "tool_calls" }],
    usage: { prompt_tokens: 30, completion_tokens: 50, total_tokens: 80, prompt_cache_hit_tokens: 0, prompt_cache_miss_tokens: 30, completion_tokens_details: { reasoning_tokens: 20 } },
  }),
  TOOL_RESULT_FINAL: (body) => ({
    id: "mock-chatcmpl-4", object: "chat.completion", created: 4, model: body.model,
    choices: [{ index: 0, message: { role: "assistant", content: JSON.stringify(completeHandoff({ summary: "mock final after tool", evidence_verdict: "POSITIVE" })), reasoning_content: "mock final reasoning" }, finish_reason: "stop" }],
    usage: { prompt_tokens: 40, completion_tokens: 30, total_tokens: 70, prompt_cache_hit_tokens: 0, prompt_cache_miss_tokens: 40, completion_tokens_details: { reasoning_tokens: 10 } },
  }),
  HANDOFF_TOOL_CALL: (body) => ({
    id: "mock-chatcmpl-7", object: "chat.completion", created: 7, model: body.model,
    choices: [{ index: 0, message: { role: "assistant", content: null, tool_calls: [{ id: "call_handoff_1", type: "function", function: { name: "finish_handoff", arguments: JSON.stringify(completeHandoff({ summary: "mock retried answer" })) } }] }, finish_reason: "tool_calls" }],
    usage: { prompt_tokens: 15, completion_tokens: 25, total_tokens: 40, prompt_cache_hit_tokens: 0, prompt_cache_miss_tokens: 15 },
  }),
  FINISH_REASON_LENGTH: (body) => ({
    id: "mock-chatcmpl-5", object: "chat.completion", created: 5, model: body.model,
    choices: [{ index: 0, message: { role: "assistant", content: "{" }, finish_reason: "length" }],
    usage: { prompt_tokens: 50, completion_tokens: 100, total_tokens: 150, prompt_cache_hit_tokens: 0, prompt_cache_miss_tokens: 50 },
  }),
  TOOL_RANGE_ERROR: () => ({
    id: "mock-chatcmpl-6", object: "chat.completion", created: 6, model: "deepseek-v4-flash",
    choices: [{ index: 0, message: { role: "assistant", content: null, tool_calls: [{ id: "call_mock_err", type: "function", function: { name: "read_file", arguments: JSON.stringify({ path: "x.txt", start_line: 1, end_line: 1500 }) } }] }, finish_reason: "tool_calls" }],
    usage: { prompt_tokens: 10, completion_tokens: 10, total_tokens: 20 },
  }),
  HTTP_400: () => ({ __status: 400, __body: { error: { message: "invalid request", type: "invalid_request_error" } } }),
  HTTP_401: () => ({ __status: 401, __body: { error: { message: "auth", type: "authentication_error" } } }),
  HTTP_402: () => ({ __status: 402, __body: { error: { message: "balance", type: "insufficient_quota" } } }),
  HTTP_422: () => ({ __status: 422, __body: { error: { message: "bad params", type: "invalid_request_error" } } }),
  HTTP_429: () => ({ __status: 429, __body: { error: { message: "rate limit", type: "rate_limit_error" } } }),
  HTTP_500: () => ({ __status: 500, __body: { error: { message: "server error", type: "server_error" } } }),
  HTTP_503: () => ({ __status: 503, __body: { error: { message: "overloaded", type: "overloaded_error" } } }),
  MALFORMED_JSON: () => ({ __raw: "{ not json" }),
  EMPTY_CHOICES: (body) => ({ id: "mock-c", object: "chat.completion", created: 1, model: body.model, choices: [], usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 } }),
  MISSING_MESSAGE: (body) => ({ id: "mock-c", object: "chat.completion", created: 1, model: body.model, choices: [{ index: 0, message: null, finish_reason: "stop" }], usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 } }),
  MISSING_TOOL_CALL_ID: (body) => ({ id: "mock-c", object: "chat.completion", created: 1, model: body.model, choices: [{ index: 0, message: { role: "assistant", content: null, tool_calls: [{ type: "function", function: { name: "read_file", arguments: "{}" } }] }, finish_reason: "tool_calls" }], usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 } }),
  DUPLICATE_TOOL_CALL_ID: (body) => ({ id: "mock-c", object: "chat.completion", created: 1, model: body.model, choices: [{ index: 0, message: { role: "assistant", content: null, tool_calls: [{ id: "call_dup", type: "function", function: { name: "read_file", arguments: "{}" } }, { id: "call_dup", type: "function", function: { name: "read_file", arguments: "{}" } }] }, finish_reason: "tool_calls" }], usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 } }),
  MISSING_REASONING_CONTENT: (body) => ({ id: "mock-c", object: "chat.completion", created: 1, model: body.model, choices: [{ index: 0, message: { role: "assistant", content: JSON.stringify(completeHandoff({ summary: "no reasoning", evidence_verdict: "POSITIVE" })) }, finish_reason: "stop" }], usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 } }),
  SEMANTIC_CORRUPTION: (body) => ({ id: "mock-c", object: "chat.completion", created: 1, model: body.model, choices: [{ index: 0, message: { role: "assistant", content: JSON.stringify(completeHandoff({ summary: "claims X contradicts source", status: "PASS", evidence_verdict: "POSITIVE" })) }, finish_reason: "stop" }], usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 } }),
};

const SCENARIOS = {
  fast_ok: ["FAST_CONTENT"],
  thinking_ok: ["THINKING_CONTENT"],
  tool_loop_ok: ["THINKING_TOOL_CALL", "TOOL_RESULT_FINAL"],
  truncation: ["FINISH_REASON_LENGTH"],
  tool_range_then_final: ["TOOL_RANGE_ERROR", "THINKING_CONTENT"],
  http_400: ["HTTP_400"], http_401: ["HTTP_401"], http_402: ["HTTP_402"], http_422: ["HTTP_422"],
  http_429_then_ok: ["HTTP_429", "HTTP_429", "HANDOFF_TOOL_CALL"],
  http_500_then_ok: ["HTTP_500", "HANDOFF_TOOL_CALL"],
  http_503_then_ok: ["HTTP_503", "HTTP_503", "HANDOFF_TOOL_CALL"],
  malformed_json: ["MALFORMED_JSON"], empty_choices: ["EMPTY_CHOICES"], missing_message: ["MISSING_MESSAGE"],
  missing_tool_call_id: ["MISSING_TOOL_CALL_ID"], duplicate_tool_call_id: ["DUPLICATE_TOOL_CALL_ID"],
  missing_reasoning_content: ["MISSING_REASONING_CONTENT"],
  semantic_corruption: ["SEMANTIC_CORRUPTION"],
};

const state = { scenario: "fast_ok", cursor: 0, captures: [] };

function send(res, status, body) {
  const data = typeof body === "string" ? body : JSON.stringify(body);
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(data);
}

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/__capture") return send(res, 200, { captures: state.captures });
  if (req.method === "GET" && req.url === "/__reset") { state.captures = []; state.cursor = 0; return send(res, 200, { ok: true }); }
  if (req.method === "POST" && req.url === "/__control") {
    let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => { try { const j = JSON.parse(b); state.scenario = j.scenario; state.cursor = 0; send(res, 200, { ok: true, scenario: state.scenario }); } catch (e) { send(res, 400, { error: "bad control" }); } }); return;
  }
  if (req.method === "POST" && req.url === "/chat/completions") {
    let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => {
      let parsed = null; try { parsed = JSON.parse(b); } catch (_) {}
      state.captures.push({ at: Date.now(), body: parsed, raw: b });
      const seq = SCENARIOS[state.scenario] || ["FAST_CONTENT"];
      const fixtureName = seq[Math.min(state.cursor, seq.length - 1)];
      state.cursor += 1;
      const fx = FIXTURES[fixtureName];
      const produced = fx(parsed || {});
      if (produced.__status) return send(res, produced.__status, produced.__body);
      if (produced.__raw !== undefined) { res.writeHead(200, { "Content-Type": "application/json" }); res.end(produced.__raw); return; }
      send(res, 200, produced);
    });
    return;
  }
  send(res, 404, { error: "not found" });
});

server.listen(0, "127.0.0.1", () => {
  console.log("MOCK_PROVIDER_PORT=" + server.address().port);
});
