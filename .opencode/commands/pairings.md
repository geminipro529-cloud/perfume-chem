---
description: Query pairing rules knowledge graph for material combinations and synergies
agent: build
---

Search the pairing rules knowledge graph for a material or combination.

Format: `/pairings <material_name>` or `/pairings <material_a> + <material_b>`

1. Read `data/knowledge_graph/pairing_rules.json` and `data/knowledge_graph/pairing_rules_discovered.json`
2. Search for the specified material(s) in both `material_a` and `material_b` fields
3. Also search `data/knowledge_graph/synergy_matrix.json` for documented synergies

For a single material search:
- List all known pairings with effect descriptions
- Group by type: synergy vs pairing
- Show source agent for traceability

For a material pair search:
- Check if the pair is already documented
- Show the documented effect if found
- If not found, suggest checking agent compatibility rules

Present results as:
```
🔗 PAIRINGS FOR: Bergamot FCF (9 found)

SYNERGIES (amplification documented):
| Paired With | Effect | Source |
|-------------|--------|--------|

PAIRINGS (complementary):
| Paired With | Effect | Source |
|-------------|--------|--------|

NOT YET DOCUMENTED — consider running agent-* for this material:
- agent-citrus-top (citrus category)
```

If no pairings found, suggest running the appropriate pairing discovery agent.
