import sqlite3

conn = sqlite3.connect("data/perfumery_kb.db")
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
print("Tables:", [t[0] for t in tables])
for t in [
    "formulas",
    "formula_materials",
    "pipeline_results",
    "evaluations",
    "failures",
]:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {cur.fetchone()[0]} rows")
conn.close()
