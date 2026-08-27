"""Local response cache + token-prefix optimizer for OpenAI-compatible LLM calls.

Cuts cost by two complementary mechanisms:

1. **Local response cache** (this module): idempotent requests skip the API call
   entirely. Cached completions are returned from a SQLite store keyed by
   ``sha256(provider, model, normalized_messages, temperature, max_tokens, top_p,
   thinking_mode, response_format, service_tier)``. Only ``temperature == 0``
   calls are cached by default (deterministic); pass ``force_cache=True`` to
   cache higher temperatures.

2. **Token-prefix optimization** (the provider's own prefix cache): we normalize
   messages so the system prompt is always first and tool definitions are sorted
   deterministically. DeepSeek-native charges 120x less for cached input
   ($0.003625 vs $0.435 / Mtok for V4-Pro). DeepInfra charges 5-7x less
   ($0.18 vs $0.95 / Mtok cached input for GLM-5.2). Stable prefix ordering is
   what tricks their cache into hitting. This module does not need to send any
   special hint flag — the providers detect cache hits automatically.

Provider pricing database is inlined below (verified 2026-07-23 against
``api-docs.deepseek.com/quick_start/pricing`` and ``deepinfra.com/pricing``).
Use the savings ledger to track actual money saved.

Cache store: ``cache/llm_cache.db`` (SQLite, WAL mode) — gitignored.
Ledger (one line per call): ``cache/llm_cache_ledger.jsonl`` — gitignored.

Usage
-----
Python:
    >>> from engine.llm_cache import cached_chat
    >>> resp = cached_chat(
    ...     provider="deepseek",
    ...     model="deepseek-v4-pro",
    ...     messages=[{"role": "system", "content": "..."},
    ...               {"role": "user", "content": "..."}],
    ...     temperature=0.0,
    ...     max_tokens=4000,
    ... )

CLI (see ``scripts/llm_cache_stats.py``):
    $ python scripts/llm_cache_stats.py stats
    $ python scripts/llm_cache_stats.py clear --older-than 30d
    $ python scripts/llm_cache_stats.py inspect --model deepseek-v4-pro

Environment overrides
----------------------
``LLM_CACHE_DIR`` redirects the cache directory (defaults to ``<repo>/cache``).
``PERFUME_DEEPSEEK_API_KEY`` and ``DEEPINFRA_API_KEY`` are read by name; pass
``api_key=...`` to override for a single call.
``DEEPINFRA_SERVICE_TIER`` (``standard`` | ``flex`` | ``priority``) overrides
the default per-call service tier for DeepInfra only. DeepSeek-native has no
service tier concept; cache-hit pricing applies automatically based on prompt
prefix reuse.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "ProviderConfig",
    "PROVIDERS",
    "cached_chat",
    "get_stats",
    "clear_cache",
    "inspect_cache",
    "CACHE_DIR",
    "CACHE_DB",
    "LEDGER",
]

# --- filesystem layout -----------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = pathlib.Path(os.environ.get("LLM_CACHE_DIR", _REPO_ROOT / "cache"))
CACHE_DB = CACHE_DIR / "llm_cache.db"
LEDGER = CACHE_DIR / "llm_cache_ledger.jsonl"


# --- provider price database ------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProviderConfig:
    """Connection + pricing for an OpenAI-compatible inference provider.

    ``prices`` maps a model name to ``(input_cache_miss, input_cache_hit, output)``
    in USD per 1M tokens. Verified 2026-07-23.
    """

    name: str
    base_url: str
    api_key_env: str
    default_service_tier: str  # "auto" | "standard" | "flex" | "priority"
    supports_service_tier: bool
    # model -> (input_miss, input_hit, output) in USD / 1M tokens
    prices: dict[str, tuple[float, float, float]]


PROVIDERS: dict[str, ProviderConfig] = {
    # Source: api-docs.deepseek.com/quick_start/pricing (fetched 2026-07-23).
    # Legacy deepseek-chat / deepseek-reasoner aliases deprecate 2026-07-24 and
    # map to deepseek-v4-flash non-thinking / thinking modes respectively.
    "deepseek": ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        api_key_env="PERFUME_DEEPSEEK_API_KEY",
        default_service_tier="auto",
        supports_service_tier=False,
        prices={
            "deepseek-v4-flash": (0.14, 0.0028, 0.28),
            "deepseek-v4-pro": (0.435, 0.003625, 0.87),
        },
    ),
    # Source: deepinfra.com/pricing (fetched 2026-07-23, standard tier).
    # Flex is 0.8x, Priority is 1.5x — applied at request time via service_tier.
    "deepinfra": ProviderConfig(
        name="deepinfra",
        base_url="https://api.deepinfra.com/v1/openai",
        api_key_env="DEEPINFRA_API_KEY",
        default_service_tier="standard",
        supports_service_tier=True,
        prices={
            "deepseek-v4-flash": (0.09, 0.018, 0.18),
            "deepseek-v4-pro": (1.30, 0.10, 2.60),
            "zai-org/GLM-5.2": (0.95, 0.18, 3.00),
        },
    ),
}


def _price_for(provider: str, model: str) -> tuple[float, float, float] | None:
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return None
    if model in cfg.prices:
        return cfg.prices[model]
    # case-insensitive fallback (handles "GLM-5.2" vs "zai-org/GLM-5.2")
    key = model.lower()
    for k, v in cfg.prices.items():
        if k.lower() == key:
            return v
    return None


def _service_tier_for(provider: str, requested: str) -> str:
    """Resolve the per-request service tier for the provider, accounting for
    flex / priority multipliers on DeepInfra and the DEEPINFRA_SERVICE_TIER
    environment override.
    """
    cfg = PROVIDERS[provider]
    if not cfg.supports_service_tier:
        return "auto"
    if requested != "auto":
        return requested
    env = os.environ.get("DEEPINFRA_SERVICE_TIER")
    if env in ("standard", "flex", "priority"):
        return env
    return cfg.default_service_tier


def _tier_multiplier(tier: str) -> float:
    return {"standard": 1.0, "flex": 0.8, "priority": 1.5}.get(tier, 1.0)


# --- normalization (maximizes provider prefix cache hits) -------------------


def _normalize_messages(messages: list[dict]) -> str:
    """Canonical message serialization for stable cache keys + provider prefix hits.

    System messages are hoisted to the very front (preserving their input order
    among themselves); non-system turns keep their original order after them.
    This is the stable-prefix structure both DeepSeek and DeepInfra cache on.
    """
    system = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    canonical = system + rest
    return json.dumps(canonical, sort_keys=False, ensure_ascii=False, separators=(",", ":"))


def _normalize_tools(tools: list[dict] | None) -> str:
    if not tools:
        return ""

    def _key(t: dict) -> str:
        return t.get("function", {}).get("name", "")

    return json.dumps(
        sorted(tools, key=_key), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def _cache_key(
    provider: str,
    model: str,
    messages_norm: str,
    tools_norm: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    thinking_mode: str,
    response_format: dict | None,
    service_tier: str,
) -> str:
    parts = [
        provider,
        model.lower().strip(),
        messages_norm,
        tools_norm,
        f"t={temperature!r}",
        f"mt={max_tokens}",
        f"p={top_p!r}",
        f"th={thinking_mode}",
        f"rf={json.dumps(response_format, sort_keys=True) if response_format else 'n'}",
        f"st={service_tier}",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


# --- sqlite ----------------------------------------------------------------


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            messages TEXT NOT NULL,
            response TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            cached_input_tokens INTEGER DEFAULT 0,
            cost_miss_usd REAL DEFAULT 0.0,
            service_tier TEXT DEFAULT 'auto',
            created_at TEXT NOT NULL,
            last_hit_at TEXT,
            hit_count INTEGER DEFAULT 0,
            ttl_days INTEGER DEFAULT 7
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_model ON cache(model)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_provider ON cache(provider)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created ON cache(created_at)")
    conn.commit()


def _connect() -> sqlite3.Connection:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB), isolation_level=None, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 30000")
    except sqlite3.OperationalError:
        pass
    _init_db(conn)
    return conn


def _ledger(entry: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(str(LEDGER), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_expired(row: sqlite3.Row) -> bool:
    ttl = row["ttl_days"]
    if ttl <= 0:
        return False
    created = datetime.fromisoformat(row["created_at"])
    age_seconds = (datetime.now(timezone.utc) - created).total_seconds()
    return age_seconds > ttl * 86400


def _resolve_api_key(provider: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    cfg = PROVIDERS[provider]
    return os.environ.get(cfg.api_key_env, "")


# --- provider call ---------------------------------------------------------


def _extract_cached_input(usage: dict) -> int:
    """Pull provider-cached-input-token count from heterogeneous usage shapes."""
    # DeepSeek-native
    if "prompt_cache_hit_tokens" in usage:
        return int(usage.get("prompt_cache_hit_tokens") or 0)
    # OpenAI / DeepInfra (prompt_tokens_details.cached_tokens)
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict):
        return int(details.get("cached_tokens") or 0)
    return 0


def _build_payload(
    *,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    top_p: float,
    thinking_mode: str,
    response_format: dict | None,
    tools: list[dict] | None,
    service_tier: str,
    supports_service_tier: bool,
) -> dict:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "stream": False,
    }
    if thinking_mode == "disabled":
        # DeepSeek-specific thinking toggle (also accepted by DeepInfra passthrough).
        payload["thinking"] = {"type": "disabled"}
    elif thinking_mode == "enabled":
        payload["thinking"] = {"type": "enabled"}
    if response_format:
        payload["response_format"] = response_format
    if tools:
        payload["tools"] = tools
    if supports_service_tier and service_tier != "auto":
        payload["service_tier"] = service_tier
    return payload


def _live_call(
    *,
    provider: str,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    top_p: float,
    thinking_mode: str,
    response_format: dict | None,
    tools: list[dict] | None,
    api_key: str | None,
    service_tier: str,
    timeout: int,
) -> tuple[dict, dict]:
    """Hit the provider. Returns (parsed_response, usage_dict)."""
    cfg = PROVIDERS[provider]
    resolved_tier = _service_tier_for(provider, service_tier)
    payload = _build_payload(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        thinking_mode=thinking_mode,
        response_format=response_format,
        tools=tools,
        service_tier=resolved_tier,
        supports_service_tier=cfg.supports_service_tier,
    )

    key = _resolve_api_key(provider, api_key)
    if not key:
        raise RuntimeError(
            f"No API key for provider {provider!r} (env: {cfg.api_key_env}); "
            "pass api_key= explicitly."
        )

    req = urllib.request.Request(
        f"{cfg.base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(
            f"Provider {provider} returned HTTP {e.code} for model {model!r}: {detail[:500]}"
        ) from e

    parsed = json.loads(body)
    usage = parsed.get("usage", {}) or {}
    return parsed, usage


# --- savings estimate ------------------------------------------------------


def _estimate_savings(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_input_tokens: int,
    service_tier: str,
) -> float:
    """What a live no-cache call would have cost in USD."""
    price = _price_for(provider, model)
    if not price:
        return 0.0
    in_miss_rate, in_hit_rate, out_rate = price
    # DeepInfra applies tier multiplier; DeepSeek-native does not.
    mult = _tier_multiplier(service_tier) if provider == "deepinfra" else 1.0
    uncached_in = max(0, prompt_tokens - cached_input_tokens)
    return (
        (
            uncached_in * in_miss_rate
            + cached_input_tokens * in_hit_rate
            + completion_tokens * out_rate
        )
        / 1_000_000
    ) * mult


# --- public API ------------------------------------------------------------


def cached_chat(
    *,
    provider: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.0,
    max_tokens: int = 4000,
    top_p: float = 1.0,
    thinking_mode: str = "auto",
    response_format: dict | None = None,
    tools: list[dict] | None = None,
    force_cache: bool = False,
    ttl_days: int = 7,
    api_key: str | None = None,
    service_tier: str = "auto",
    timeout: int = 300,
) -> dict:
    """Return an OpenAI-style chat completion, using local cache when safe.

    By default only ``temperature == 0`` calls are cached (deterministic
    outputs). ``force_cache=True`` overrides this; not recommended for
    temperature > 0 because the cached answer will not match what the provider
    would have produced on a fresh call.

    On cache hit, the provider is NOT called. The hit count and last-hit
    timestamp are updated, and a savings estimate is appended to the ledger.

    On cache miss, the request is made to the provider's
    ``/chat/completions`` endpoint, the response is stored with TTL
    ``ttl_days``, and a miss entry is written to the ledger.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider!r}. Known: {sorted(PROVIDERS)}")

    # Non-deterministic calls bypass the cache entirely unless caller insisted.
    if temperature > 0 and not force_cache:
        response, _usage = _live_call(
            provider=provider,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            thinking_mode=thinking_mode,
            response_format=response_format,
            tools=tools,
            api_key=api_key,
            service_tier=service_tier,
            timeout=timeout,
        )
        _ledger(
            {
                "event": "nocache",
                "provider": provider,
                "model": model,
                "temperature": temperature,
                "timestamp": _now_iso(),
            }
        )
        return response

    resolved_tier = _service_tier_for(provider, service_tier)
    messages_norm = _normalize_messages(messages)
    tools_norm = _normalize_tools(tools)
    key = _cache_key(
        provider,
        model,
        messages_norm,
        tools_norm,
        temperature,
        max_tokens,
        top_p,
        thinking_mode,
        response_format,
        resolved_tier,
    )

    # --- check cache ---
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM cache WHERE key = ?", (key,)).fetchone()
        if row is not None and not _is_expired(row):
            response = json.loads(row["response"])
            new_hit_count = int(row["hit_count"]) + 1
            conn.execute(
                "UPDATE cache SET hit_count = ?, last_hit_at = ? WHERE key = ?",
                (new_hit_count, _now_iso(), key),
            )
            savings = _estimate_savings(
                row["provider"],
                row["model"],
                int(row["prompt_tokens"]),
                int(row["completion_tokens"]),
                int(row["cached_input_tokens"]),
                row["service_tier"],
            )
            _ledger(
                {
                    "event": "hit",
                    "key": key,
                    "provider": row["provider"],
                    "model": row["model"],
                    "prompt_tokens": int(row["prompt_tokens"]),
                    "completion_tokens": int(row["completion_tokens"]),
                    "cached_input_tokens": int(row["cached_input_tokens"]),
                    "savings_usd": round(savings, 6),
                    "hit_count": new_hit_count,
                    "timestamp": _now_iso(),
                }
            )
            return response
        # else: row missing OR expired -> miss path below
        if row is not None and _is_expired(row):
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
    finally:
        conn.close()

    # --- miss: call provider, persist, return ---
    response, usage = _live_call(
        provider=provider,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        thinking_mode=thinking_mode,
        response_format=response_format,
        tools=tools,
        api_key=api_key,
        service_tier=service_tier,
        timeout=timeout,
    )

    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    cached_input_tokens = _extract_cached_input(usage)
    cost_miss = _estimate_savings(
        provider,
        model,
        prompt_tokens,
        completion_tokens,
        cached_input_tokens,
        resolved_tier,
    )

    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO cache
                (key, provider, model, messages, response,
                 prompt_tokens, completion_tokens, cached_input_tokens,
                 cost_miss_usd, service_tier, created_at,
                 last_hit_at, hit_count, ttl_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, ?)
            """,
            (
                key,
                provider,
                model,
                messages_norm,
                json.dumps(response, ensure_ascii=False),
                prompt_tokens,
                completion_tokens,
                cached_input_tokens,
                cost_miss,
                resolved_tier,
                _now_iso(),
                ttl_days,
            ),
        )
    finally:
        conn.close()

    _ledger(
        {
            "event": "miss",
            "key": key,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cached_input_tokens": cached_input_tokens,
            "cost_usd": round(cost_miss, 6),
            "service_tier": resolved_tier,
            "timestamp": _now_iso(),
        }
    )
    return response


# --- introspection / maintenance ------------------------------------------


def get_stats() -> dict:
    """Return aggregate cache health: hit/miss counts, savings, per-model breakdown."""
    conn = _connect()
    try:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS rows,
                COALESCE(SUM(hit_count), 0) AS total_hits,
                COALESCE(SUM(cost_miss_usd), 0) AS total_miss_cost,
                COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                COALESCE(SUM(cached_input_tokens), 0) AS cached_input_tokens
            FROM cache
            """
        ).fetchone()

        # total_calls = every miss produced a row; every hit bumped hit_count.
        # cost saved = sum over (hit_count * cost_miss_usd).
        savings_row = conn.execute(
            "SELECT COALESCE(SUM(hit_count * cost_miss_usd), 0) AS s FROM cache"
        ).fetchone()
        total_savings = float(savings_row["s"] if savings_row else 0.0)

        per_model = conn.execute(
            """
            SELECT model,
                   COUNT(*) AS entries,
                   COALESCE(SUM(hit_count), 0) AS hits,
                   COALESCE(SUM(cost_miss_usd), 0) AS miss_cost,
                   COALESCE(SUM(hit_count * cost_miss_usd), 0) AS savings,
                   COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                   COALESCE(SUM(completion_tokens), 0) AS completion_tokens
            FROM cache
            GROUP BY model
            ORDER BY savings DESC
            """
        ).fetchall()

        # ledger event counts (hits + misses + nocache)
        ledger_hits = ledger_misses = ledger_nocache = 0
        if LEDGER.is_file():
            with open(str(LEDGER), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line).get("event")
                    except json.JSONDecodeError:
                        continue
                    if ev == "hit":
                        ledger_hits += 1
                    elif ev == "miss":
                        ledger_misses += 1
                    elif ev == "nocache":
                        ledger_nocache += 1
    finally:
        conn.close()

    rows = int(totals["rows"] if totals else 0)
    total_hits = int(totals["total_hits"] if totals else 0)
    total_miss_cost = float(totals["total_miss_cost"] if totals else 0.0)
    prompt_tokens = int(totals["prompt_tokens"] if totals else 0)
    completion_tokens = int(totals["completion_tokens"] if totals else 0)
    cached_input_tokens = int(totals["cached_input_tokens"] if totals else 0)

    total_calls = ledger_misses + ledger_hits + ledger_nocache
    hit_rate = (total_hits / total_calls) if total_calls else 0.0

    return {
        "cache_entries": rows,
        "hits": total_hits,
        "misses": ledger_misses,
        "nocache_calls": ledger_nocache,
        "total_calls": total_calls,
        "hit_rate": round(hit_rate, 4),
        "est_savings_usd": round(total_savings, 4),
        "est_miss_cost_usd": round(total_miss_cost, 4),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cached_input_tokens": cached_input_tokens,
        "per_model": [
            {
                "model": r["model"],
                "entries": int(r["entries"]),
                "hits": int(r["hits"]),
                "miss_cost_usd": round(float(r["miss_cost"]), 4),
                "savings_usd": round(float(r["savings"]), 4),
                "prompt_tokens": int(r["prompt_tokens"]),
                "completion_tokens": int(r["completion_tokens"]),
            }
            for r in per_model
        ],
    }


def clear_cache(
    older_than_days: int | None = None, model: str | None = None, provider: str | None = None
) -> int:
    """Remove cache rows. Returns count removed.

    With no args, removes everything (only useful for reset / tests).
    ``older_than_days=N`` removes rows older than N days.
    ``model=...`` / ``provider=...`` further restrict the wipe.
    """
    clauses: list[str] = []
    params: list[Any] = []
    if older_than_days is not None and older_than_days >= 0:
        cutoff = datetime.now(timezone.utc).timestamp() - (older_than_days * 86400)
        clauses.append("julianday(created_at) - julianday('1970-01-01') < ?")
        params.append(cutoff / 86400.0)
    if model:
        clauses.append("model = ?")
        params.append(model)
    if provider:
        clauses.append("provider = ?")
        params.append(provider)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = _connect()
    try:
        cur = conn.execute(f"DELETE FROM cache{where}", params)
        return int(cur.rowcount or 0)
    finally:
        conn.close()


def inspect_cache(
    model: str | None = None, provider: str | None = None, limit: int = 20
) -> list[dict]:
    """Return latest cache entries for inspection (no `response` body — too big)."""
    clauses: list[str] = []
    params: list[Any] = []
    if model:
        clauses.append("model = ?")
        params.append(model)
    if provider:
        clauses.append("provider = ?")
        params.append(provider)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = _connect()
    try:
        rows = conn.execute(
            f"""SELECT key, provider, model, prompt_tokens, completion_tokens,
                       cached_input_tokens, cost_miss_usd, service_tier,
                       created_at, last_hit_at, hit_count, ttl_days
                FROM cache{where}
                ORDER BY created_at DESC
                LIMIT ?""",
            params + [int(limit)],
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
