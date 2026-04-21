import sqlite3
conn = sqlite3.connect('perfume_chem.db')
c = conn.cursor()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])
for t in tables:
    count = c.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
    print(f"  {t[0]}: {count} rows")

# Sample material
row = c.execute("SELECT name, mw, completeness_pct, source FROM materials LIMIT 3").fetchall()
print("\nSample materials:")
for r in row:
    print(f"  {r}")

# Check corrupted synergy entries
corrupted = c.execute("SELECT material_a_name, is_corrupted, corruption_notes FROM synergy_rules WHERE is_corrupted = 1").fetchall()
print(f"\nCorrupted synergy entries: {len(corrupted)}")
for r in corrupted:
    print(f"  {r[0][:60]}... | {r[2]}")

conn.close()
