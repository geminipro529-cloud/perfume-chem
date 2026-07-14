---
description: Summarize current inventory stock and availability
agent: build
---

Read inventory.txt and produce a structured summary:

1. List all categories and how many materials are in each
2. Flag any DEPLETED or low-stock markers
3. List dilutions (which materials are pure vs diluted)
4. Note any materials that appear in inventory but are missing from ingredient_intelligence profiles, ODT_DATA, or data/materials YAML files

This is a read-only inventory check. Do not modify any files.
