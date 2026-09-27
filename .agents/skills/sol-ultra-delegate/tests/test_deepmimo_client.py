from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = SKILL_ROOT / "scripts" / "deepmimo_client.py"
SPEC = importlib.util.spec_from_file_location("deepmimo_client", HELPER_PATH)
assert SPEC and SPEC.loader
CLIENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLIENT)


class FakeResponse:
    def __init__(self, payload, *, status=200, headers=None):
        self.status = status
        self.headers = headers or {}
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self.status

    def read(self, size=-1):
        return self._data if size < 0 else self._data[:size]


class FakeOpener:
    def __init__(self, *items):
        self.items = list(items)
        self.requests = []

    def __call__(self, request, *, timeout):
        self.requests.append((request, timeout))
        if not self.items:
            raise AssertionError("unexpected HTTP call")
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


TOKEN = "dm_proj_test-only-token"


def health(status="ok", service="DeepMimo", version="2.0.1-preview.12"):
    return FakeResponse({"status": status, "service": service, "version": version})


def ready(value=True):
    return FakeResponse({"ready": value})


def models(model="deepmimo"):
    return FakeResponse({"object": "list", "data": [{"id": model}]})


def completion(provider="deepseek", backend="deepseek-flash", **overrides):
    payload = {
        "model": "deepmimo",
        "choices": [
            {
                "message": {"role": "assistant", "content": "EVIDENCE_OK"},
                "finish_reason": "stop",
            }
        ],
    }
    payload.update(overrides)
    return FakeResponse(
        payload,
        headers={
            "X-DeepMimo-Project": "perfume-chem-sol-ultra",
            "X-DeepMimo-Provider": provider,
            "X-DeepMimo-Model": backend,
            "X-DeepMimo-Fallback-Count": "0" if provider == "deepseek" else "1",
            "X-DeepMimo-Provider-Calls": "1" if provider == "deepseek" else "2",
            "X-DeepMimo-Stream-Mode": "native",
            "X-LLM-Router-Provider": provider,
            "X-LLM-Router-Model": backend,
        },
    )


def completion_with_accounting(provider, backend, fallback_count, provider_calls):
    response = completion(provider, backend)
    response.headers["X-DeepMimo-Fallback-Count"] = str(fallback_count)
    response.headers["X-DeepMimo-Provider-Calls"] = str(provider_calls)
    return response


def packet():
    return {"messages": [{"role": "user", "content": "Return bounded evidence."}]}


class DeepMimoClientTests(unittest.TestCase):
    def test_remote_provider_contract_is_exactly_deepseek_then_mimo(self):
        self.assertEqual(
            CLIENT.APPROVED_ROUTES,
            (
                ("deepseek", "deepseek-flash"),
                ("mimo", "mimo-v2.6-pro"),
            ),
        )
        self.assertNotIn("luna", repr(CLIENT.APPROVED_ROUTES).lower())

    def test_accepts_valid_deepseek_receipt(self):
        opener = FakeOpener(health(), ready(), models(), completion())

        result = CLIENT.execute(packet(), opener=opener, token=TOKEN)

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["deepmimo"]["provider"], "deepseek")
        sent = json.loads(opener.requests[3][0].data)
        self.assertEqual(sent["model"], "deepmimo")
        self.assertEqual(sent["max_tokens"], 4096)
        self.assertNotIn("tools", sent)
        self.assertEqual(
            opener.requests[3][0].headers["X-deepmimo-original-model-handoff"],
            "enabled",
        )
        self.assertNotIn("X-llm-router-fallback-owner", opener.requests[3][0].headers)
        for request, _ in opener.requests[1:]:
            self.assertEqual(request.headers["Authorization"], f"Bearer {TOKEN}")

    def test_accepts_valid_mimo_receipt(self):
        opener = FakeOpener(health(), ready(), models(), completion("mimo", "mimo-v2.6-pro"))

        result = CLIENT.execute(packet(), opener=opener, token=TOKEN)

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["deepmimo"]["backend_model"], "mimo-v2.6-pro")

    def test_rejects_route_accounting_that_contradicts_provider_order(self):
        deepseek_after_fallback = FakeOpener(
            health(),
            ready(),
            models(),
            completion_with_accounting("deepseek", "deepseek-flash", 1, 2),
        )
        mimo_without_deepseek = FakeOpener(
            health(),
            ready(),
            models(),
            completion_with_accounting("mimo", "mimo-v2.6-pro", 0, 1),
        )

        results = [
            CLIENT.execute(packet(), opener=deepseek_after_fallback, token=TOKEN),
            CLIENT.execute(packet(), opener=mimo_without_deepseek, token=TOKEN),
        ]

        self.assertTrue(all(row["status"] == "BLOCKED" for row in results))
        self.assertTrue(all(row["reason"] == "invalid_receipt" for row in results))

    def test_original_model_handoff_is_eligible(self):
        body = {
            "error": {
                "type": "provider_error",
                "code": "original_model_handoff",
                "message": "DeepMimo providers were exhausted; continue locally.",
            }
        }
        error = urllib.error.HTTPError(
            CLIENT.BASE_URL + "/chat/completions",
            503,
            "Service Unavailable",
            {
                "X-DeepMimo-Handoff": "original-model",
                "X-DeepMimo-Handoff-Reason": "providers-exhausted",
                "X-Should-Retry": "false",
            },
            io.BytesIO(json.dumps(body).encode()),
        )
        opener = FakeOpener(health(), ready(), models(), error)

        result = CLIENT.execute(packet(), opener=opener, token=TOKEN)

        self.assertEqual(result["status"], "SOL_FALLBACK_ELIGIBLE")
        self.assertEqual(result["reason"], "original_model_handoff")
        self.assertFalse(result["deepmimo"]["should_retry"])

    def test_incomplete_or_unvalidated_handoff_is_blocked(self):
        body = {
            "error": {
                "type": "provider_error",
                "code": "original_model_handoff",
                "message": "Unverified handoff.",
            }
        }
        error = urllib.error.HTTPError(
            CLIENT.BASE_URL + "/chat/completions",
            503,
            "Service Unavailable",
            {
                "X-DeepMimo-Handoff": "original-model",
                "X-DeepMimo-Handoff-Reason": "providers-exhausted",
            },
            io.BytesIO(json.dumps(body).encode()),
        )

        result = CLIENT.execute(
            packet(),
            opener=FakeOpener(health(), ready(), models(), error),
            token=TOKEN,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "invalid_receipt")

    def test_unavailable_or_unhealthy_router_is_blocked(self):
        unavailable = FakeOpener(urllib.error.URLError("not listening"))
        unhealthy = FakeOpener(health(status="degraded"))

        unavailable_result = CLIENT.execute(packet(), opener=unavailable, token=TOKEN)
        unhealthy_result = CLIENT.execute(packet(), opener=unhealthy, token=TOKEN)

        self.assertEqual(unavailable_result["status"], "BLOCKED")
        self.assertEqual(unavailable_result["reason"], "router_unavailable")
        self.assertEqual(unhealthy_result["status"], "BLOCKED")
        self.assertEqual(unhealthy_result["reason"], "router_unhealthy")

    def test_wrong_advertised_or_response_model_is_blocked(self):
        wrong_advertised = FakeOpener(health(), ready(), models("other"))
        wrong_response = FakeOpener(health(), ready(), models(), completion(model="other"))

        advertised_result = CLIENT.execute(packet(), opener=wrong_advertised, token=TOKEN)
        response_result = CLIENT.execute(packet(), opener=wrong_response, token=TOKEN)

        self.assertEqual(advertised_result["status"], "BLOCKED")
        self.assertEqual(response_result["status"], "BLOCKED")
        self.assertEqual(advertised_result["reason"], "invalid_receipt")
        self.assertEqual(response_result["reason"], "invalid_receipt")

    def test_missing_headers_invalid_pair_empty_content_and_length_are_blocked(self):
        missing_headers = FakeOpener(health(), ready(), models(), FakeResponse({
            "model": "deepmimo",
            "choices": [{"message": {"content": "x"}, "finish_reason": "stop"}],
        }))
        invalid_pair = FakeOpener(health(), ready(), models(), completion("deepseek", "mimo-v2.6-pro"))
        empty = completion()
        empty._data = json.dumps({
            "model": "deepmimo",
            "choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
        }).encode()
        empty_content = FakeOpener(health(), ready(), models(), empty)
        length = completion()
        length._data = json.dumps({
            "model": "deepmimo",
            "choices": [{"message": {"content": "partial"}, "finish_reason": "length"}],
        }).encode()
        truncated = FakeOpener(health(), ready(), models(), length)

        results = [
            CLIENT.execute(packet(), opener=missing_headers, token=TOKEN),
            CLIENT.execute(packet(), opener=invalid_pair, token=TOKEN),
            CLIENT.execute(packet(), opener=empty_content, token=TOKEN),
            CLIENT.execute(packet(), opener=truncated, token=TOKEN),
        ]

        self.assertTrue(all(row["status"] == "BLOCKED" for row in results))
        self.assertTrue(all(row["reason"] == "invalid_receipt" for row in results))

    def test_non_loopback_override_empty_oversized_and_tools_are_blocked(self):
        non_loopback = CLIENT.execute({**packet(), "base_url": "http://example.com/v1"}, token=TOKEN)
        tools = CLIENT.execute({**packet(), "tools": []}, token=TOKEN)

        self.assertEqual(non_loopback["status"], "BLOCKED")
        self.assertEqual(non_loopback["reason"], "base_url_not_allowed")
        self.assertEqual(tools["reason"], "unsupported_packet_fields")
        with self.assertRaisesRegex(CLIENT.PacketBlockedError, "empty_packet"):
            CLIENT.parse_packet_bytes(b"")
        with self.assertRaisesRegex(CLIENT.PacketBlockedError, "packet_too_large"):
            CLIENT.parse_packet_bytes(b"x" * (CLIENT.MAX_PACKET_BYTES + 1))

    def test_router_400_413_and_422_are_blocked(self):
        for status in (400, 413, 422):
            with self.subTest(status=status):
                body = {"error": {"type": "invalid_request_error", "code": "bad_packet"}}
                error = urllib.error.HTTPError(
                    CLIENT.BASE_URL + "/chat/completions",
                    status,
                    "Rejected",
                    {},
                    io.BytesIO(json.dumps(body).encode()),
                )
                result = CLIENT.execute(
                    packet(),
                    opener=FakeOpener(health(), ready(), models(), error),
                    token=TOKEN,
                )
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["reason"], "router_rejected_packet")

    def test_missing_or_rejected_project_token_is_blocked(self):
        missing = CLIENT.execute(packet(), token="")
        body = {"error": {"type": "authentication_error", "code": "invalid_api_key"}}
        error = urllib.error.HTTPError(
            CLIENT.BASE_URL + "/models",
            401,
            "Unauthorized",
            {},
            io.BytesIO(json.dumps(body).encode()),
        )
        rejected = CLIENT.execute(packet(), opener=FakeOpener(health(), error), token=TOKEN)

        self.assertEqual(missing["status"], "BLOCKED")
        self.assertEqual(missing["reason"], "project_token_unavailable")
        self.assertEqual(rejected["status"], "BLOCKED")
        self.assertEqual(rejected["reason"], "project_authentication_failed")

    def test_quota_and_policy_rejections_are_blocked(self):
        for status in (402, 409, 429):
            with self.subTest(status=status):
                body = {"error": {"type": "policy_error", "code": "request_rejected"}}
                error = urllib.error.HTTPError(
                    CLIENT.BASE_URL + "/chat/completions",
                    status,
                    "Rejected",
                    {},
                    io.BytesIO(json.dumps(body).encode()),
                )
                result = CLIENT.execute(
                    packet(),
                    opener=FakeOpener(health(), ready(), models(), error),
                    token=TOKEN,
                )
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["reason"], "router_policy_rejection")

    def test_pre_handoff_service_version_is_blocked(self):
        result = CLIENT.execute(
            packet(),
            opener=FakeOpener(health(version="2.0.1-preview.6")),
            token=TOKEN,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "router_contract_unavailable")

    def test_helper_writes_no_files_and_contains_no_process_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            os.chdir(directory)
            try:
                before = set(Path(directory).iterdir())
                result = CLIENT.execute(
                    packet(),
                    opener=FakeOpener(health(), ready(), models(), completion()),
                    token=TOKEN,
                )
                after = set(Path(directory).iterdir())
            finally:
                os.chdir(previous)

        source = HELPER_PATH.read_text(encoding="utf-8")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(before, after)
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("Start-Process", source)
        self.assertNotIn("codex exec", source)


if __name__ == "__main__":
    unittest.main()
