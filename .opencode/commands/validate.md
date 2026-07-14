---
description: Fast pre-gate formula validation — structure, names, dilutions, math, dosing sanity
agent: build
---

Read inventory.txt first, then validate the formula file at $ARGUMENTS.

If the user provides a formula file path as $1, validate that file:
1. **Structure**: Check table format, section dividers, batch size
2. **Names**: Normalize material names, check against inventory, flag typos
3. **Dilutions**: Verify each dilution matches inventory.txt
4. **Math**: Sum active µL, calculate concentrate %, compare to stated
5. **Dosing**: Flag trace overdoses, fixative gaps, musk chord completeness

If no file path given, ask the user which formula to validate.

Present results as:
- [✓] passing checks in green
- [⚠️] warnings in yellow  
- [✗] failures in red

This is a FAST pre-check — it does NOT run the full pipeline. Use `/gate` for full OAV/physics analysis.
