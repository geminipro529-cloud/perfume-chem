from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from chassis import validate_partition, validate_module

def test_partitions():
    cases=[
        (ROOT/"formulas/YSL_LHomme_chassis_partition.csv",4500,4200,300),
        (ROOT/"formulas/YSL_La_Nuit_chassis_partition.csv",4500,4200,300),
        (ROOT/"formulas/Prada_LHomme_chassis_partition.csv",4500,4150,350),
    ]
    for path,t,c,m in cases:
        assert not validate_partition(path,t,c,m)["errors"]

def test_modules():
    for path in (ROOT/"modules").glob("*.csv"):
        expected=350 if "350" in path.stem else 300
        assert not validate_module(path,expected)["errors"]
