from __future__ import annotations

from typing import Any

from consultant_core import KNOWLEDGE_DIR, load_json, split_terms
from complexity_engine.ontology import validate_model_definition


class ModelRegistry:
    def __init__(self, path=None) -> None:
        self.path = path or (KNOWLEDGE_DIR / "complexity_model_v1_2" / "model_registry_seed.json")
        payload = load_json(self.path)
        self.models = list(payload.get("models") or [])

    def get(self, model_id: str) -> dict[str, Any]:
        for model in self.models:
            if model.get("model_id") == model_id:
                return {"state": "FOUND", "record": model, "validation": validate_model_definition(model)}
        return {"state": "NOT_FOUND", "model_id": model_id}

    def search(self, query: str, limit: int = 20) -> dict[str, Any]:
        terms = split_terms(query)
        scored = []
        for model in self.models:
            text = " ".join(str(model.get(k) or "") for k in (
                "model_id", "name", "artistic_contract", "example_direction", "why_new_or_under_modeled"
            ))
            model_terms = split_terms(text)
            score = len(terms & model_terms)
            if terms and score == 0:
                continue
            scored.append((score, model))
        scored.sort(key=lambda x: (-x[0], str(x[1].get("model_id"))))
        records = [m for _, m in scored[:limit]]
        return {
            "state": "FOUND" if records else "NOT_FOUND",
            "query": query,
            "records": records,
            "canonical_records": 0,
            "boundary": "Registry seeds are design candidates and never canonical promotion by search result.",
        }

    def validate_all(self) -> dict[str, Any]:
        results = [validate_model_definition(m) for m in self.models]
        return {
            "state": "PASS" if all(r["state"] == "PASS" for r in results) else "REVIEW",
            "record_count": len(results),
            "pass_count": sum(r["state"] == "PASS" for r in results),
            "results": results,
        }
