import json, sys

sys.stdout.reconfigure(encoding='utf-8')
data = json.load(open('data/knowledge_graph/material_properties.json', 'r', encoding='utf-8'))

lines = []
lines.append('# Perfumery Material Properties — Scientific Dump (verified 2026-05-10)')
lines.append('')
lines.append(f'**{len(data)} entries**. PubChem auto-override active. VP corrections Rounds 1–3 applied.')
lines.append('')
lines.append('## Legend')
lines.append('')
lines.append('| Smell | ODT ethanol ppm |')
lines.append('|---|---|')
lines.append('| strong | < 0.01 |')
lines.append('| medium | 0.01–1.0 |')
lines.append('| low | 1.0–100 |')
lines.append('| sub | > 100 |')
lines.append('')
lines.append('| OAV Effect | OAV concentrate |')
lines.append('|---|---|')
lines.append('| sub-threshold | < 10 |')
lines.append('| near-threshold | 10–100 |')
lines.append('| perceptible | 100–1,000 |')
lines.append('| characteristic | 1,000–10,000 |')
lines.append('| dominant | 10,000–100,000 |')
lines.append('| overwhelming | > 100,000 |')
lines.append('')
lines.append('| Source | Module |')
lines.append('|---|---|')
lines.append('| II | ingredient_intelligence.py |')
lines.append('| ODT | odor_thresholds.py |')
lines.append('| PC | PubChem (auto-override MW/cLogP) |')
lines.append('| HEUR | Heuristic computed |')
lines.append('| MP | Hand-crafted knowledge graph |')
lines.append('| HILL/CS | dose_response.py |')
lines.append('| IFRA | ifra_safety.py |')
lines.append('')
lines.append('---')

for i, m in enumerate(data, 1):
    name = m['name']
    lines.append(f'## {i} — {name}')
    lines.append('')
    lines.append('| Field | Value | Source |')
    lines.append('|---|---|---|')

    fields = [
        ('cas', 'CAS', 'CAS_MAP'),
        ('formula_str', 'Formula', 'PC'),
        ('pubchem_cid', 'PubChem CID', 'PC'),
        ('mw', 'MW g/mol', 'II/PC'),
        ('vp', 'VP Pa', 'II'),
        ('clp', 'cLogP', 'II/PC'),
        ('odt', 'ODT air ppb', 'ODT'),
        ('odt_ethanol_ppm', 'ODT ethanol ppm', 'ODT'),
        ('oav_typical', 'OAV concentrate', 'HEUR'),
        ('oav_effect', 'OAV effect', 'HEUR'),
        ('oav_dose_pct', 'Dose % conc', 'HEUR'),
        ('smell_strength', 'Smell strength', 'HEUR'),
        ('anosmic_risk', 'Anosmic', 'HEUR'),
        ('hill_ec50', 'Hill EC50', 'HILL'),
        ('hill_n', 'Hill n', 'HILL'),
        ('hill_response', 'Hill type', 'HILL'),
        ('note', 'Note', 'II'),
        ('role', 'Role', 'II'),
        ('texture', 'Texture', 'II'),
        ('or_family', 'OR family', 'II'),
        ('activity_coef', 'Act coeff', 'II/UNIFAC'),
        ('synergies', 'Synergies', 'II'),
        ('ifra_cat4_limit_pct', 'IFRA limit %', 'IFRA'),
        ('ifra_standard_type', 'IFRA type', 'IFRA'),
        ('ifra_banned', 'IFRA banned', 'IFRA'),
        ('dilution_pct', 'Dilution %', 'INV'),
        ('sar_class', 'SAR class', 'MP'),
        ('arctander_character', 'Arctander', 'MP'),
        ('carles_position', 'Carles', 'MP'),
        ('jellinek_axis', 'Jellinek', 'MP'),
        ('odor_family', 'Odor family', 'HEUR'),
        ('odor_profile', 'Odor profile', 'HEUR'),
    ]
    for f, label, src in fields:
        v = m.get(f)
        if v is None or v == '' or v == [] or v is False:
            lines.append(f'| {label} | — | — |')
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            items = []
            for z in v:
                items.append(f'max {z.get("max_conc_pct")}%: {z.get("character")} ({z.get("quality")})')
            lines.append(f'| {label} | {"; ".join(items)} | CS |')
        elif isinstance(v, list):
            joined = ', '.join(str(x) for x in v)
            lines.append(f'| {label} | {joined} | {src} |')
        elif isinstance(v, bool):
            yn = 'YES' if v else 'NO'
            lines.append(f'| {label} | {yn} | {src} |')
        else:
            lines.append(f'| {label} | {v} | {src} |')

    af = m.get('audit_flags')
    if af:
        lines.append('')
        lines.append('**PubChem override:**')
        for flag in af:
            lines.append(f'- {flag["field"]}: II={flag.get("db_value")} -> PC={flag.get("pubchem_value")}')

    pw = m.get('pubchem_warnings')
    if pw:
        lines.append('')
        lines.append(f'**PubChem warning:** {"; ".join(pw)}')

    lines.append('')
    lines.append('---')
    lines.append('')

out = '\n'.join(lines)
with open('_material_properties_full_dump.md', 'w', encoding='utf-8') as f:
    f.write(out)
print(f'_material_properties_full_dump.md — {len(out):,} chars, {len(data)} entries')
