# Perfume Meaningful Complexity Audit v2 Pack

This pack is designed to plug into an OpenCode / DeepSeek worker system after the user finishes configuring it.

It does not start or claim an external orchestration run.

## Files

- `Meaningful_Complexity_Audit_v2.md`
  - Governing 50-plus-row accord and 65-plus-row perfume standard.
- `meaningful_complexity_schema.json`
  - Machine-readable formula, row, interaction, gate, and summary schema.
- `interaction_matrix_schema.json`
  - Machine-readable aroma-group correlation schema.
- `DeepSeek_Formula_Worker_Packet_Template.md`
  - Bounded worker packet for one formula.
- `Independent_Adversarial_Audit_Checklist.md`
  - Read-only reviewer checklist.

## Recommended use

1. Put this directory under the OpenCode project.
2. Make the schemas read-only.
3. Require each formula worker to validate its outputs against the schema.
4. Give the adversarial reviewer no edit permission.
5. Merge only artifacts that pass the hard gates.
6. Preserve physical validation as a separate phase.
