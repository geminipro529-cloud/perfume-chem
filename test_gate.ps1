$env:OPENCODE_SESSION_ID = "test-session"
python scripts/formula_release_gate.py --formula-file "formulas/Allure_Extreme_AHSEE_30mL_EdP.md" --expected-concentrate-ul 6000 --brief generic 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "EXIT CODE: $LASTEXITCODE" }
