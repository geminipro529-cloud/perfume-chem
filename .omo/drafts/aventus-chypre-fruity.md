---
slug: aventus-chypre-fruity
status: approved
intent: clear
approach: Adapt Pineapple_Chypre_Luxe_30mL_Extrait.md → 30mL EdP 20% (6,000 µL), ~47 core materials. Substitute Hydroxycitronellal → Mayol + Farnesol (specific doses). Correct Ambrox target (3-5%, constrained by 33% dilution). Retain structural green notes (Galbanum, Beta-Pinene, Cedrat). Reduce Damascone Beta for IFRA (≤12 µL). Document Ylang ≠ Cassis character shift, Coranol gap. Gate with --brief generic.
momaus_review: 8 issues found, all 8 fixed in plan v2
review_verdict: APPROVED (conditional on applying all fixes in the plan)
---

# Draft: aventus-chypre-fruity

## Approval gate
status: approved
pending-action: execute plan (5 tasks, 3 waves)
approach: Fully-reviewed Aventus reformulation. 8 Momus issues fixed. Ready for execution.

## Known issue: subagent models
oh-my-openagent.json agent models (explore, librarian, momus) reference `deepseek-chat` which resolves with trailing slash (`deepseek-chat/`) causing model-not-found errors. Worker should either fix the model IDs or proceed without subagents (all research already completed inline).
