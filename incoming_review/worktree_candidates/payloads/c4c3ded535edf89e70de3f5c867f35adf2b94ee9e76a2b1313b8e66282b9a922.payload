from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from consultant_core import KNOWLEDGE_DIR, load_json, split_terms


class ResearchSourceGraph:
    def __init__(self, ledger_path=None, graph_path=None) -> None:
        base = KNOWLEDGE_DIR / "complexity_model_v1_2"
        ledger = load_json(ledger_path or base / "research_source_ledger.json")
        graph = load_json(graph_path or base / "research_source_graph.json")
        self.records = {r["source_id"]: r for r in ledger.get("records", [])}
        self.edges = list(graph.get("edges", []))
        self.outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in self.edges:
            self.outgoing[edge["from"]].append(edge)

    def search(self, query: str, limit: int = 20) -> dict[str, Any]:
        terms = split_terms(query)
        scored=[]
        for r in self.records.values():
            text=" ".join(str(v) for v in r.values())
            score=len(terms & split_terms(text))
            if not terms or score:
                scored.append((score,r))
        scored.sort(key=lambda x:(-x[0],x[1]["source_id"]))
        records=[r for _,r in scored[:limit]]
        return {"state":"FOUND" if records else "NOT_FOUND","records":records}

    def neighborhood(self, source_id: str, depth: int = 2) -> dict[str, Any]:
        seen={source_id}; q=deque([(source_id,0)]); edges=[]
        while q:
            node,d=q.popleft()
            if d>=depth: continue
            for edge in self.outgoing.get(node,[]):
                edges.append(edge)
                nxt=edge["to"]
                if nxt not in seen:
                    seen.add(nxt); q.append((nxt,d+1))
        return {
            "state":"FOUND" if source_id in self.records else "NOT_FOUND",
            "root":self.records.get(source_id),
            "nodes":[self.records[x] for x in sorted(seen) if x in self.records],
            "edges":edges,
            "boundary":"Neighborhood discovery does not automatically admit downstream claims."
        }
