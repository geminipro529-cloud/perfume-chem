# PRE_MIX_OAV_GUARD

## Mandatory revision rule

For every revised formula, compare the immediate parent before compounding.

- `active_ul = raw_ul * stock_fraction`
- `active_equivalent_child_raw_ul = parent_active_ul / child_stock_fraction`
- Stock-strength change with >=3x active-dose discontinuity: **FAIL**
- 1.5x to <3x discontinuity: **WARN**
- Same-stock >=3x dose increase plus >=10x matched-window modeled OAV jump: **WARN**
- Persistent modeled OAV leader >=20x runner-up in at least two windows, leader OAV >=100: **WARN**

OAV is a screening alarm, not a final design gate. It does not mean percent
perceived contribution, exact intensity, target similarity, pleasantness, or
consumer preference.

Regression coverage permanently includes the Prada L'Homme citronellol
10%-to-neat failure pattern and the Lemonile 10%-to-neat failure pattern.

Run revised formulas with:

```powershell
python scripts/formula_release_gate.py `
  --formula-file formulas\CHILD.md `
  --parent-formula-file formulas\PARENT.md `
  --brief auto `
  --json
```
