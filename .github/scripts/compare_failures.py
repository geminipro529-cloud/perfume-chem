"""Compare a pytest JUnit report with the committed list of known failures.

CI helper only (not a pipeline entry point).  Exit 1 when a test fails that is
not on the list; a listed test that now passes is reported so the list can be
shrunk in that PR.

    python .github/scripts/compare_failures.py <junit.xml> <known_failures.txt> <test root>
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


def node_id(classname: str, name: str, root: Path) -> str:
    """``tests.unit.test_x.TestY`` + ``test_z`` -> ``tests/unit/test_x.py::TestY::test_z``."""
    parts = classname.split(".")
    for cut in range(len(parts), 0, -1):
        module = Path(*parts[:cut]).with_suffix(".py")
        if (root / module).is_file():
            return "::".join([module.as_posix(), *parts[cut:], name])
    return "::".join([classname, name])


def failed_tests(report: Path, root: Path) -> set[str]:
    failed = set()
    for case in ElementTree.parse(report).iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            failed.add(node_id(case.get("classname", ""), case.get("name", ""), root))
    return failed


def known_failures(listing: Path) -> set[str]:
    lines = listing.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def main(argv: list[str]) -> int:
    report, listing, root = Path(argv[1]), Path(argv[2]), Path(argv[3])
    failed = failed_tests(report, root)
    known = known_failures(listing)
    new = sorted(failed - known)
    fixed = sorted(known - failed)
    for test in fixed:
        print(f"::notice::Now passing, remove it from {listing.as_posix()}: {test}")
    for test in new:
        print(f"::error::New failing test (not in {listing.as_posix()}): {test}")
    print(
        f"{len(failed)} failing, {len(known)} known, {len(new)} new, "
        f"{len(fixed)} known ones now pass."
    )
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
