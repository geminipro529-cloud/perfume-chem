#!/usr/bin/env python3
from pathlib import Path
import json
from chassis import validate_partition, validate_module, validate_anchor_floors

ROOT=Path(__file__).resolve().parents[1]

cases=[
("YSL_LHomme", ROOT/"formulas/YSL_LHomme_chassis_partition.csv", 4500,4200,300),
("YSL_La_Nuit", ROOT/"formulas/YSL_La_Nuit_chassis_partition.csv",4500,4200,300),
("Prada_LHomme", ROOT/"formulas/Prada_LHomme_chassis_partition.csv",4500,4150,350),
]

results=[]
errors=[]
for name,path,t,c,m in cases:
    result=validate_partition(path,t,c,m)
    result["case"]=name
    anchor_errors=validate_anchor_floors(path,ROOT/f"configs/{name}_module_envelope.json")
    result["anchor_errors"]=anchor_errors
    errors.extend(result["errors"])
    errors.extend(anchor_errors)
    results.append(result)

for path in sorted((ROOT/"modules").glob("*.csv")):
    expected=350 if "350" in path.stem else 300
    result=validate_module(path,expected)
    errors.extend(result["errors"])
    results.append(result)

report={"status":"PASS" if not errors else "FAIL","errors":errors,"results":results}
(ROOT/"VALIDATION_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
raise SystemExit(0 if not errors else 1)
