from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

BASE_URL = "http://127.0.0.1:8421/v1"
MODEL = "deepmimo"
PROJECT_ID = "perfume-chem-sol-ultra"
TOKEN_ENV = "DEEPMIMO_PERFUME_CHEM_TOKEN"
HANDOFF_REQUEST_HEADER = "X-DeepMimo-Original-Model-Handoff"
HANDOFF_REQUEST_VALUE = "enabled"
MAX_PACKET_BYTES = 131_072
MAX_RESPONSE_BYTES = 2_097_152
MAX_MESSAGES = 64
MAX_COMPLETION_TOKENS = 4096
PREFLIGHT_TIMEOUT_SECONDS = 10
COMPLETION_TIMEOUT_SECONDS = 180
ALLOWED_ROLES = {"system", "developer", "user", "assistant"}
ALLOWED_PACKET_KEYS = {"messages", "base_url"}
APPROVED_ROUTES = (
    ("deepseek", "deepseek-flash"),
    ("mimo", "mimo-v2.6-pro"),
)
EXPECTED_ROUTE_ACCOUNTING = {
    ("deepseek", "deepseek-flash"): (0, 1),
    ("mimo", "mimo-v2.6-pro"): (1, 2),
}
SAFE_REASON = re.compile(r"[a-z0-9_]{1,64}\Z")
PREVIEW_VERSION = re.compile(r"2\.0\.1-preview\.(\d+)\Z")


class PacketBlockedError(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ReceiptInvalidError(ValueError):
    pass


def _blocked(reason: str, **details: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "BLOCKED",
        "reason": reason,
        "deepmimo": {"status": "NOT_CALLED"},
    }
    result.update(details)
    return result


def _fallback(reason: str, deepmimo: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "SOL_FALLBACK_ELIGIBLE",
        "reason": reason,
        "deepmimo": dict(deepmimo or {"status": "UNAVAILABLE"}),
    }


def _validate_base_url(value: Any) -> str:
    if value is None:
        return BASE_URL
    if not isinstance(value, str):
        raise PacketBlockedError("base_url_not_allowed")
    parsed = urlsplit(value)
    if (
        value != BASE_URL
        or parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port != 8421
        or parsed.path != "/v1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise PacketBlockedError("base_url_not_allowed")
    return value


def _validate_packet(packet: Any) -> tuple[str, list[dict[str, str]]]:
    if not isinstance(packet, dict):
        raise PacketBlockedError("packet_must_be_object")
    unknown = set(packet) - ALLOWED_PACKET_KEYS
    if unknown:
        raise PacketBlockedError("unsupported_packet_fields")
    base_url = _validate_base_url(packet.get("base_url"))
    messages = packet.get("messages")
    if not isinstance(messages, list) or not messages:
        raise PacketBlockedError("messages_must_be_nonempty")
    if len(messages) > MAX_MESSAGES:
        raise PacketBlockedError("too_many_messages")
    clean_messages: list[dict[str, str]] = []
    for message in messages:
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise PacketBlockedError("text_messages_only")
        role = message.get("role")
        content = message.get("content")
        if role not in ALLOWED_ROLES or not isinstance(content, str) or not content.strip():
            raise PacketBlockedError("text_messages_only")
        clean_messages.append({"role": role, "content": content})
    return base_url, clean_messages


def parse_packet_bytes(data: bytes) -> dict[str, Any]:
    if not data:
        raise PacketBlockedError("empty_packet")
    if len(data) > MAX_PACKET_BYTES:
        raise PacketBlockedError("packet_too_large")
    try:
        decoded = data.decode("utf-8")
        packet = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PacketBlockedError("invalid_json") from None
    if not isinstance(packet, dict):
        raise PacketBlockedError("packet_must_be_object")
    return packet


def _headers_dict(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    try:
        items = headers.items()
    except AttributeError:
        return {}
    return {str(name).lower(): str(value) for name, value in items}


def _user_environment_token() -> str | None:
    token = os.environ.get(TOKEN_ENV)
    if token:
        return token
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, TOKEN_ENV)
    except (ImportError, OSError):
        return None
    return value if isinstance(value, str) else None


def _resolve_project_token(explicit: str | None) -> str:
    token = _user_environment_token() if explicit is None else explicit
    if (
        not isinstance(token, str)
        or not token.startswith("dm_proj_")
        or len(token) > 256
        or any(character.isspace() for character in token)
    ):
        raise PacketBlockedError("project_token_unavailable")
    return token


def _supports_handoff_contract(version: Any) -> bool:
    if not isinstance(version, str):
        return False
    preview = PREVIEW_VERSION.fullmatch(version)
    if preview is not None:
        return int(preview.group(1)) >= 7
    parts = version.split(".")
    try:
        numeric = tuple(int(part) for part in parts)
    except ValueError:
        return False
    return len(numeric) == 3 and numeric >= (2, 0, 1)


def _read_json_response(response: Any) -> tuple[int, dict[str, str], dict[str, Any]]:
    data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ReceiptInvalidError("response_too_large")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ReceiptInvalidError("invalid_json") from None
    if not isinstance(payload, dict):
        raise ReceiptInvalidError("response_not_object")
    status = int(getattr(response, "status", response.getcode()))
    return status, _headers_dict(getattr(response, "headers", None)), payload


def _request_json(
    request: urllib.request.Request,
    *,
    timeout: float,
    opener: Callable[..., Any],
) -> tuple[int, dict[str, str], dict[str, Any]]:
    with opener(request, timeout=timeout) as response:
        return _read_json_response(response)


def _preflight(
    base_url: str,
    *,
    opener: Callable[..., Any],
    token: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    origin = base_url.removesuffix("/v1")
    try:
        health_status, _, health = _request_json(
            urllib.request.Request(origin + "/health", headers={"Accept": "application/json"}),
            timeout=PREFLIGHT_TIMEOUT_SECONDS,
            opener=opener,
        )
    except (urllib.error.URLError, TimeoutError, OSError, ReceiptInvalidError):
        return _blocked(
            "router_unavailable", deepmimo={"status": "UNAVAILABLE"}
        ), {}

    version = health.get("version")
    if (
        health_status != 200
        or health.get("status") != "ok"
        or health.get("service") != "DeepMimo"
    ):
        return _blocked(
            "router_unhealthy", deepmimo={"status": "UNHEALTHY"}
        ), {}
    if not _supports_handoff_contract(version):
        return _blocked("router_contract_unavailable", service_version=version), {}

    authenticated_headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    try:
        ready_status, _, ready = _request_json(
            urllib.request.Request(origin + "/health/ready", headers=authenticated_headers),
            timeout=PREFLIGHT_TIMEOUT_SECONDS,
            opener=opener,
        )
        model_status, _, models = _request_json(
            urllib.request.Request(base_url + "/models", headers=authenticated_headers),
            timeout=PREFLIGHT_TIMEOUT_SECONDS,
            opener=opener,
        )
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        exc.close()
        if status in {401, 403}:
            return _blocked("project_authentication_failed", http_status=status), {}
        if status == 503:
            return _blocked(
                "router_unhealthy", deepmimo={"status": "UNHEALTHY"}
            ), {}
        return _blocked(
            "invalid_receipt",
            http_status=status,
            deepmimo={"status": "INVALID_PREFLIGHT"},
        ), {}
    except (urllib.error.URLError, TimeoutError, OSError, ReceiptInvalidError):
        return _blocked(
            "router_unavailable", deepmimo={"status": "UNAVAILABLE"}
        ), {}

    if ready_status != 200 or ready.get("ready") is not True:
        return _blocked(
            "router_unhealthy", deepmimo={"status": "UNHEALTHY"}
        ), {}
    data = models.get("data")
    if model_status != 200 or not isinstance(data, list):
        return _blocked(
            "invalid_receipt",
            deepmimo={"status": "INVALID_MODELS_RECEIPT"},
        ), {}
    advertised = [row.get("id") for row in data if isinstance(row, dict)]
    if advertised != [MODEL]:
        return _blocked(
            "invalid_receipt",
            deepmimo={"status": "INVALID_MODELS_RECEIPT"},
        ), {}
    return None, {
        "health": "ok",
        "ready": True,
        "service_version": version,
        "advertised_model": MODEL,
        "project": PROJECT_ID,
    }


def _handle_http_error(exc: urllib.error.HTTPError, preflight: Mapping[str, Any]) -> dict[str, Any]:
    status = int(exc.code)
    headers = _headers_dict(exc.headers)
    try:
        _, _, payload = _read_json_response(exc)
    except ReceiptInvalidError:
        payload = {}
    finally:
        exc.close()

    if status in {400, 413, 422}:
        error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        error_code = error.get("code")
        if not isinstance(error_code, str) or SAFE_REASON.fullmatch(error_code) is None:
            error_code = None
        return _blocked(
            "router_rejected_packet",
            http_status=status,
            error_code=error_code,
        )

    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    if (
        status == 503
        and headers.get("x-deepmimo-handoff") == "original-model"
        and headers.get("x-deepmimo-handoff-reason") == "providers-exhausted"
        and headers.get("x-should-retry") == "false"
        and error.get("type") == "provider_error"
        and error.get("code") == "original_model_handoff"
    ):
        return _fallback(
            "original_model_handoff",
            {
                **dict(preflight),
                "status": "SOL_FALLBACK_ELIGIBLE",
                "handoff": "original-model",
                "handoff_reason": "providers-exhausted",
                "should_retry": False,
            },
        )
    if status in {401, 403}:
        return _blocked("project_authentication_failed", http_status=status)
    if status in {402, 409, 429}:
        return _blocked("router_policy_rejection", http_status=status)
    return _blocked(
        "invalid_receipt",
        http_status=status,
        deepmimo={**dict(preflight), "status": "INVALID_RESPONSE"},
    )


def execute(
    packet: Any,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
    token: str | None = None,
) -> dict[str, Any]:
    try:
        base_url, messages = _validate_packet(packet)
        project_token = _resolve_project_token(token)
    except PacketBlockedError as exc:
        return _blocked(exc.reason)

    preflight_failure, preflight = _preflight(base_url, opener=opener, token=project_token)
    if preflight_failure is not None:
        return preflight_failure

    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "temperature": 0,
            "max_tokens": MAX_COMPLETION_TOKENS,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {project_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            HANDOFF_REQUEST_HEADER: HANDOFF_REQUEST_VALUE,
            "User-Agent": "Perfume-Chem-Sol-Ultra-Delegate/2.0",
        },
        method="POST",
    )
    try:
        status, headers, response = _request_json(
            request,
            timeout=COMPLETION_TIMEOUT_SECONDS,
            opener=opener,
        )
    except urllib.error.HTTPError as exc:
        return _handle_http_error(exc, preflight)
    except (urllib.error.URLError, TimeoutError, OSError):
        return _blocked(
            "router_unavailable",
            deepmimo={**preflight, "status": "UNAVAILABLE"},
        )
    except ReceiptInvalidError:
        return _blocked(
            "invalid_receipt",
            deepmimo={**preflight, "status": "INVALID_RESPONSE"},
        )

    try:
        choice = response["choices"][0]
        message = choice["message"]
        content = message["content"]
        finish_reason = choice["finish_reason"]
    except (KeyError, IndexError, TypeError):
        return _blocked(
            "invalid_receipt",
            deepmimo={**preflight, "status": "INVALID_RESPONSE"},
        )

    provider = headers.get("x-deepmimo-provider")
    backend_model = headers.get("x-deepmimo-model")
    project = headers.get("x-deepmimo-project")
    legacy_provider = headers.get("x-llm-router-provider")
    legacy_model = headers.get("x-llm-router-model")
    stream_mode = headers.get("x-deepmimo-stream-mode")
    try:
        fallback_count = int(headers["x-deepmimo-fallback-count"])
        provider_calls = int(headers["x-deepmimo-provider-calls"])
    except (KeyError, TypeError, ValueError):
        fallback_count = -1
        provider_calls = -1
    valid = (
        status == 200
        and response.get("model") == MODEL
        and project == PROJECT_ID
        and (provider, backend_model) in APPROVED_ROUTES
        and legacy_provider == provider
        and legacy_model == backend_model
        and stream_mode == "native"
        and (fallback_count, provider_calls)
        == EXPECTED_ROUTE_ACCOUNTING.get((provider, backend_model))
        and isinstance(content, str)
        and bool(content.strip())
        and finish_reason == "stop"
    )
    if not valid:
        return _blocked(
            "invalid_receipt",
            deepmimo={
                **preflight,
                "status": "INVALID_RESPONSE",
            },
        )

    return {
        "status": "COMPLETED",
        "reason": "remote_completed",
        "deepmimo": {
            **preflight,
            "response_model": MODEL,
            "project": project,
            "provider": provider,
            "backend_model": backend_model,
            "fallback_count": fallback_count,
            "provider_calls": provider_calls,
            "stream_mode": stream_mode,
            "finish_reason": finish_reason,
        },
        "assistant_content": content,
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_PACKET_BYTES + 1)
    try:
        packet = parse_packet_bytes(raw)
        result = execute(packet)
    except PacketBlockedError as exc:
        result = _blocked(exc.reason)
    except Exception:
        result = _blocked("helper_internal_error")
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
