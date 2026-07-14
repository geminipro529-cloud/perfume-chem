import sys, os, json, re, yaml, math
from pathlib import Path
from collections import defaultdict

repo = Path(r"D:\chatbots\perfume-chem")
sys.path.insert(0, str(repo))
from engine.name_utils import normalize_name as norm_name

print("=== COMPREHENSIVE DATA QUALITY AUDIT ===")
print()
