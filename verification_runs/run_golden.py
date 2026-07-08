"""Run golden-set: prints PASS/FAIL per case."""
from __future__ import annotations

import importlib
import sys

from .golden_cases import GOLDEN_CASES


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    n_pass = 0
    n_fail = 0
    for case in GOLDEN_CASES:
        mod = importlib.import_module(case["module"])
        fn = getattr(mod, case["fn"])
        args = case.get("args", [])
        kwargs = case.get("kwargs", {})
        try:
            out = fn(*args, **kwargs)
        except Exception as e:
            print(f"FAIL  {case['name']}: raised {e!r}")
            n_fail += 1
            continue
        lo, hi = case["expect_range"]
        if lo <= out <= hi:
            print(f"PASS  {case['name']}: {out:.3e} ∈ [{lo:.3e}, {hi:.3e}]")
            n_pass += 1
        else:
            print(f"FAIL  {case['name']}: {out:.3e} ∉ [{lo:.3e}, {hi:.3e}]")
            n_fail += 1
    print(f"\n{n_pass}/{n_pass+n_fail} passed.")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
