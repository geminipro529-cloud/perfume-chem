"""Tests for engine.llm_cache — local response cache + prefix optimizer.

The provider call path is mocked via monkeypatching of urllib.request.urlopen
so these tests run offline, do not consume API credits, and do not depend on
the live DeepSeek / DeepInfra services.

Tests must use per-test isolated cache directories (LLM_CACHE_DIR env override
happens once at module import, so we threshold at the import boundary).
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
import urllib.error
import urllib.request
from contextlib import contextmanager
from unittest import mock

import pytest

# Ensure the repo root is on sys.path so `engine.*` resolves.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Each test gets its own cache dir + ledger via the env var the module reads at import.

    Because engine.llm_cache resolves CACHE_DIR at import time, we must reload
    the module after the env var is set to get isolation. We also drop the SQLite
    lock from a stale import.
    """
    cache_dir = tmp_path / "llm_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LLM_CACHE_DIR", str(cache_dir))
    # Force reimport so CACHE_DIR / CACHE_DB / LEDGER rebind to tmp_path.
    if "engine.llm_cache" in sys.modules:
        del sys.modules["engine.llm_cache"]
    import engine.llm_cache as mod

    # Module-level constants recompute from the env var at import.
    assert pathlib.Path(mod.CACHE_DIR) == cache_dir, (
        f"cache dir not isolated: {mod.CACHE_DIR!r} != {cache_dir!r}"
    )
    yield mod
    # Clean up module-level state so the next test starts fresh.
    if "engine.llm_cache" in sys.modules:
        del sys.modules["engine.llm_cache"]


def _fake_response(
    content: str = "ok",
    prompt_tokens: int = 100,
    completion_tokens: int = 10,
    cached_input_tokens: int = 0,
):
    """Build the dict shape OpenAI-compatible endpoints return."""
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "prompt_cache_hit_tokens": cached_input_tokens,
        },
    }


@contextmanager
def _mock_urlopen(return_value: dict, fail_first: bool = False):
    """Patch urllib.request.urlopen to return ``return_value`` (or raise once)."""
    call_count = {"n": 0}
    fake_resp_bytes = json.dumps(return_value).encode("utf-8")

    class _FakeCtx:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return fake_resp_bytes

    def _fake_urlopen(req, timeout=None):
        call_count["n"] += 1
        if fail_first and call_count["n"] == 1:
            # We don't use this in current tests but keep for future expiry tests
            raise RuntimeError("forced failure")
        return _FakeCtx()

    with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen) as patched:
        yield patched, call_count


# --- cache key determinism --------------------------------------------------


def test_cache_key_idempotent(isolated_cache):
    """Identical inputs always produce identical cache keys."""
    mod = isolated_cache
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    k1 = mod._cache_key(
        "deepseek",
        "deepseek-v4-pro",
        mod._normalize_messages(msgs),
        "",
        0.0,
        4000,
        1.0,
        "auto",
        None,
        "auto",
    )
    k2 = mod._cache_key(
        "deepseek",
        "deepseek-v4-pro",
        mod._normalize_messages(msgs),
        "",
        0.0,
        4000,
        1.0,
        "auto",
        None,
        "auto",
    )
    assert k1 == k2


def test_cache_key_changes_with_system_message(isolated_cache):
    """Different system prompt => different cache key, even with same user msg."""
    mod = isolated_cache
    m_a = [{"role": "system", "content": "A"}, {"role": "user", "content": "u"}]
    m_b = [{"role": "system", "content": "B"}, {"role": "user", "content": "u"}]
    ka = mod._cache_key(
        "deepseek",
        "deepseek-v4-pro",
        mod._normalize_messages(m_a),
        "",
        0.0,
        4000,
        1.0,
        "auto",
        None,
        "auto",
    )
    kb = mod._cache_key(
        "deepseek",
        "deepseek-v4-pro",
        mod._normalize_messages(m_b),
        "",
        0.0,
        4000,
        1.0,
        "auto",
        None,
        "auto",
    )
    assert ka != kb


def test_cache_key_changes_with_temperature(isolated_cache):
    mod = isolated_cache
    msgs = [{"role": "user", "content": "u"}]
    ka = mod._cache_key(
        "p", "m", mod._normalize_messages(msgs), "", 0.0, 4000, 1.0, "auto", None, "auto"
    )
    kb = mod._cache_key(
        "p", "m", mod._normalize_messages(msgs), "", 0.7, 4000, 1.0, "auto", None, "auto"
    )
    assert ka != kb


# --- message normalization (provider prefix-cache friendliness) -----------


def test_normalize_messages_system_first(isolated_cache):
    """System messages hoisted to the front even if input has them out of order."""
    mod = isolated_cache
    msgs = [
        {"role": "user", "content": "u1"},
        {"role": "system", "content": "s1"},
        {"role": "assistant", "content": "a1"},
        {"role": "system", "content": "s2"},
    ]
    out = mod._normalize_messages(msgs)
    parsed = json.loads(out)
    assert [m["role"] for m in parsed] == ["system", "system", "user", "assistant"]
    # order preserved among system messages
    assert [m["content"] for m in parsed if m["role"] == "system"] == ["s1", "s2"]
    # non-system order preserved
    assert parsed[2]["content"] == "u1"
    assert parsed[3]["content"] == "a1"


# --- hit / miss paths ------------------------------------------------------


def test_cached_chat_miss_then_hit(monkeypatch, isolated_cache):
    """First call hits the (mocked) provider; second call is a cache hit and
    must NOT invoke urlopen a second time."""
    mod = isolated_cache
    monkeypatch.setenv("PERFUME_DEEPSEEK_API_KEY", "test-key")
    msg = _fake_response(content="hi", prompt_tokens=100, completion_tokens=10)

    with _mock_urlopen(msg) as (patched, calls):
        r1 = mod.cached_chat(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.0,
            max_tokens=4000,
        )
        assert r1["choices"][0]["message"]["content"] == "hi"
        assert calls["n"] == 1, "first call should have hit the provider"

        r2 = mod.cached_chat(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.0,
            max_tokens=4000,
        )
        assert r2["choices"][0]["message"]["content"] == "hi"
        assert calls["n"] == 1, "second identical call must not hit the provider"

    # Cache should record 1 hit, 1 miss in stats.
    stats = mod.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_cached_chat_temperature_skips_cache(monkeypatch, isolated_cache):
    """temperature > 0 bypasses the cache (non-deterministic)."""
    mod = isolated_cache
    monkeypatch.setenv("PERFUME_DEEPSEEK_API_KEY", "test-key")
    msg = _fake_response(content="rand")

    with _mock_urlopen(msg) as (_p, calls):
        mod.cached_chat(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "x"}],
            temperature=0.7,
            max_tokens=4000,  # nonzero => skip cache
        )
        mod.cached_chat(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "x"}],
            temperature=0.7,
            max_tokens=4000,
        )
        assert calls["n"] == 2, "both non-deterministic calls should hit the provider"

    stats = mod.get_stats()
    # nocache calls are recorded separately; cache table should be empty.
    assert stats["cache_entries"] == 0
    assert stats["nocache_calls"] == 2


# --- TTL expiry -----------------------------------------------------------


def test_cached_chat_ttl_expiry(monkeypatch, isolated_cache):
    """An expired cache entry triggers a new provider call."""
    mod = isolated_cache
    monkeypatch.setenv("PERFUME_DEEPSEEK_API_KEY", "test-key")
    msg = _fake_response(content="v1")

    with _mock_urlopen(msg) as (_p, calls):
        # First call — expires IMMEDIATELY (ttl_days=0 actually means no expiry;
        # we use 0.001 days = ~1 second but force an expired record manually).
        mod.cached_chat(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "q"}],
            temperature=0.0,
            max_tokens=4000,
            ttl_days=7,
        )
        assert calls["n"] == 1

        # Manually backdate the cached row by setting created_at 8 days ago.
        conn = mod._connect()
        try:
            from datetime import datetime, timedelta, timezone

            old_ts = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
            conn.execute("UPDATE cache SET created_at = ? WHERE 1=1", (old_ts,))
            conn.commit()
        finally:
            conn.close()

        # Second call with same prompt — expiry triggers a miss => provider hit.
        msg2 = _fake_response(content="v2")
        # need to update the mock return without breaking the patch.
    # Re-patch with a different return for the second pass.
    with _mock_urlopen(msg2) as (_p, calls):
        r = mod.cached_chat(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "q"}],
            temperature=0.0,
            max_tokens=4000,
            ttl_days=7,
        )
        assert r["choices"][0]["message"]["content"] == "v2"
        assert calls["n"] == 1, "expired row must force a fresh provider call"


# --- provider error path ----------------------------------------------------


def test_cached_chat_provider_http_error(monkeypatch, isolated_cache):
    """HTTP 4xx from provider propagates as RuntimeError and does not cache."""
    mod = isolated_cache
    monkeypatch.setenv("PERFUME_DEEPSEEK_API_KEY", "test-key")

    def fake_urlopen_err(req, timeout=None):
        # Build a real urllib.error.HTTPError so the cached_chat error path
        # (which catches HTTPError, reads the body, and re-raises as RuntimeError)
        # exercises production code, not a synthetic test helper.
        import email.message

        raise urllib.error.HTTPError(
            url="https://api.deepseek.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=email.message.Message(),
            fp=io.BytesIO(b'{"error":"bad key"}'),
        )

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen_err):
        with pytest.raises(RuntimeError, match="HTTP 401"):
            mod.cached_chat(
                provider="deepseek",
                model="deepseek-v4-pro",
                messages=[{"role": "user", "content": "x"}],
                temperature=0.0,
                max_tokens=4000,
            )

    stats = mod.get_stats()
    assert stats["cache_entries"] == 0


# --- savings estimate ------------------------------------------------------


def test_estimate_savings_deepseek_v4_pro(monkeypatch, isolated_cache):
    """Savings = prompt + completion token cost at published rates."""
    mod = isolated_cache
    # 1M prompt_tokens (cache miss) + 1M completion_tokens => $0.435 + $0.87 = $1.305
    savings = mod._estimate_savings(
        provider="deepseek",
        model="deepseek-v4-pro",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        cached_input_tokens=0,
        service_tier="auto",
    )
    assert abs(savings - 1.305) < 1e-6, f"expected 1.305, got {savings}"


def test_estimate_savings_deepseek_v4_pro_with_cache_hit(monkeypatch, isolated_cache):
    """Cached input tokens billed at the cache-hit rate ($0.003625/M)."""
    mod = isolated_cache
    # 1M prompt tokens, 50% cached => 500k at miss + 500k at hit + 0 completion
    savings = mod._estimate_savings(
        provider="deepseek",
        model="deepseek-v4-pro",
        prompt_tokens=1_000_000,
        completion_tokens=0,
        cached_input_tokens=500_000,
        service_tier="auto",
    )
    expected = (500_000 * 0.435 + 500_000 * 0.003625) / 1_000_000
    assert abs(savings - expected) < 1e-6


def test_estimate_savings_deepinfra_flex_discount(monkeypatch, isolated_cache):
    """DeepInfra flex tier multiplies cost by 0.8."""
    mod = isolated_cache
    # 1M + 1M tokens of GLM-5.2 standard = $0.95 + $3.00 = $3.95
    # flex (0.8) = $3.16
    savings = mod._estimate_savings(
        provider="deepinfra",
        model="zai-org/GLM-5.2",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        cached_input_tokens=0,
        service_tier="flex",
    )
    assert abs(savings - 3.16) < 1e-6, f"expected 3.16, got {savings}"


# --- maintenance API -------------------------------------------------------


def test_clear_cache_removes_everything(monkeypatch, isolated_cache):
    mod = isolated_cache
    monkeypatch.setenv("PERFUME_DEEPSEEK_API_KEY", "test-key")
    msg = _fake_response(content="x")
    with _mock_urlopen(msg):
        mod.cached_chat(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "x"}],
            temperature=0.0,
            max_tokens=4000,
        )
    assert mod.get_stats()["cache_entries"] == 1
    removed = mod.clear_cache()
    assert removed == 1
    assert mod.get_stats()["cache_entries"] == 0


def test_inspect_returns_recent_entries(monkeypatch, isolated_cache):
    mod = isolated_cache
    monkeypatch.setenv("PERFUME_DEEPSEEK_API_KEY", "test-key")
    msg = _fake_response(content="x")
    with _mock_urlopen(msg):
        mod.cached_chat(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "x"}],
            temperature=0.0,
            max_tokens=4000,
        )
    rows = mod.inspect_cache(model="deepseek-v4-pro")
    assert len(rows) == 1
    assert rows[0]["model"] == "deepseek-v4-pro"
    assert rows[0]["prompt_tokens"] == 100
    # response body is NOT included (too big for inspection output)
    assert "response" not in rows[0]


# --- helpers ---------------------------------------------------------------
# (Inline helpers in test bodies preferred; this section kept for future additions.)
