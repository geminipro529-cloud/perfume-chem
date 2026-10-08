"""Verify the live Build D0 claim matrix without mutating repository state."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.scientific_validation.claim_registry import (  # noqa: E402
    CLAIM_FAMILY_POLICIES,
    validate_claim_method_alignment,
)
from engine.scientific_validation.contracts import (  # noqa: E402
    BindingAuthorityState,
    BindingState,
    ClaimFamily,
    MarginAuthority,
    VersionBinding,
)
from engine.scientific_validation.first_claim import (  # noqa: E402
    build_prada_orris_first_claim,
)

CONTROL_RELATIVE = Path(
    "formulas/Prada_LHomme_Architecture_Control_30mL_EdT.md"
)
INTERVENTION_RELATIVE = Path(
    "formulas/Prada_LHomme_Luxury_Orris_30mL_EdT.md"
)
EXPECTED_CONTROL_SHA256 = (
    "151de70b2983a7902a67daf8ddd43e0692bfea4ee5f8c92e553c3174827e1d00"
)
EXPECTED_INTERVENTION_SHA256 = (
    "c05661384d53c27aa7a50b50e14e62cf245ee5aa8d3974e0829a56f873d5eb4d"
)
# Verified LF/Windows-CRLF byte variants of the same quarantined texts. Keep
# historical pins; do not normalize arbitrary input or report a normalized hash
# as though it identifies the physical source bytes.
CONTROL_BYTE_SHA256S = frozenset({
    EXPECTED_CONTROL_SHA256,
    "10c0ad9651c84938abc436e626eab1e35ff1bc06b3e7c8bf708b80fcd89037c6",
})
INTERVENTION_BYTE_SHA256S = frozenset({
    EXPECTED_INTERVENTION_SHA256,
    "b4b4d19b06614eceee0ff46eb4f08ba4542a3e189e706807fc0b2282ae0743a8",
})
_GIT_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _require_quarantined(path: Path, *, require_orris_carrier_gap: bool) -> None:
    with path.open("r", encoding="utf-8-sig", errors="strict") as stream:
        header = "".join(stream.readline() for _ in range(20))
    if "**Status:** QUARANTINED" not in header:
        raise ValueError("formula status is not quarantined")
    if require_orris_carrier_gap and "Orris Liquid carrier is not recorded" not in header:
        raise ValueError("Orris Liquid carrier gap is not recorded")


def _repository_head(repository_root: Path) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repository_root.as_posix()}",
            "-C",
            str(repository_root),
            "rev-parse",
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=30,
    )
    if result.returncode != 0 or result.stderr:
        raise ValueError("Git head could not be resolved cleanly")
    head = result.stdout.strip()
    if not _GIT_SHA1_RE.fullmatch(head):
        raise ValueError("Git head is malformed")
    return head


def _formula_binding(relative: Path, digest: str) -> VersionBinding:
    return VersionBinding(
        kind="formula",
        identifier=relative.as_posix(),
        version="authoritative-overlay-sha256",
        sha256=digest,
        authority_state=BindingAuthorityState.QUARANTINED,
    )


def build_gate_payload(repository_root: Path) -> dict[str, Any]:
    """Build a deterministic live D0 gate packet from bounded repository reads."""

    root = repository_root.resolve()
    if not root.is_dir() or not (root / ".git").exists():
        raise ValueError("repository root is not an authoritative Git checkout")
    control_path = (root / CONTROL_RELATIVE).resolve()
    intervention_path = (root / INTERVENTION_RELATIVE).resolve()
    for path in (control_path, intervention_path):
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("formula path escaped the repository") from error
        if not path.is_file():
            raise ValueError("required formula binding is missing")

    control_sha256 = _sha256_path(control_path)
    intervention_sha256 = _sha256_path(intervention_path)
    if control_sha256 not in CONTROL_BYTE_SHA256S:
        raise ValueError("control formula binding changed")
    if intervention_sha256 not in INTERVENTION_BYTE_SHA256S:
        raise ValueError("intervention formula binding changed")
    _require_quarantined(control_path, require_orris_carrier_gap=False)
    _require_quarantined(intervention_path, require_orris_carrier_gap=True)

    head = _repository_head(root)
    software_sha256 = hashlib.sha256(
        f"git-commit:{head}".encode("ascii")
    ).hexdigest()
    control_binding = _formula_binding(CONTROL_RELATIVE, control_sha256)
    intervention_binding = _formula_binding(
        INTERVENTION_RELATIVE,
        intervention_sha256,
    )
    software_binding = VersionBinding(
        kind="software",
        identifier="perfume-chem",
        version=head,
        sha256=software_sha256,
        authority_state=BindingAuthorityState.REFERENCE_ONLY,
    )
    claim = build_prada_orris_first_claim(
        control_binding=control_binding,
        intervention_binding=intervention_binding,
        software_binding=software_binding,
    )
    validate_claim_method_alignment(claim)

    exit_fields = {
        "claim": bool(claim.claim_id and claim.version > 0),
        "comparator": bool(claim.comparator.comparator_id),
        "endpoint": bool(claim.primary_endpoint.endpoint_id),
        "margin": (
            claim.primary_endpoint.criterion.margin_authority
            is MarginAuthority.PROVISIONAL_PREPILOT
        ),
        "assessor_population": (
            claim.scope.population.state is BindingState.BOUND
            and claim.scope.population.value is not None
        ),
        "required_evidence": len(claim.required_evidence) == 12,
    }
    if tuple(policy.family for policy in CLAIM_FAMILY_POLICIES) != tuple(
        ClaimFamily
    ):
        raise ValueError("claim-family registry order or completeness changed")
    if not all(exit_fields.values()):
        raise ValueError("D0 exit fields are incomplete")

    return {
        "schema": "d0-claim-matrix-gate-v1",
        "status": "PASS",
        "repository_head": head,
        "claim_family_count": len(CLAIM_FAMILY_POLICIES),
        "claim_families": [family.value for family in ClaimFamily],
        "claim_id": claim.claim_id,
        "claim_version": claim.version,
        "claim_sha256": claim.content_sha256,
        "formula_bindings": [
            {
                "role": "control",
                "path": CONTROL_RELATIVE.as_posix(),
                "sha256": control_sha256,
                "status": "QUARANTINED",
            },
            {
                "role": "intervention",
                "path": INTERVENTION_RELATIVE.as_posix(),
                "sha256": intervention_sha256,
                "status": "QUARANTINED",
            },
        ],
        "software_binding": {
            "identifier": software_binding.identifier,
            "version": software_binding.version,
            "sha256": software_binding.sha256,
            "authority_state": software_binding.authority_state.value,
        },
        "d0_exit_fields": exit_fields,
        "d0_exit_fields_complete": all(exit_fields.values()),
        "primary_margin": {
            "lower": str(claim.primary_endpoint.criterion.lower_margin),
            "upper": None,
            "authority": claim.primary_endpoint.criterion.margin_authority.value,
        },
        "protected_margin": {
            "lower": str(claim.secondary_endpoints[0].criterion.lower_margin),
            "upper": str(claim.secondary_endpoints[0].criterion.upper_margin),
            "authority": (
                claim.secondary_endpoints[0].criterion.margin_authority.value
            ),
        },
        "required_evidence_count": len(claim.required_evidence),
        "required_unbound_scope": [
            field_name
            for field_name in ("formula", "lot", "matrix", "condition")
            if getattr(claim.scope, field_name).state
            is BindingState.REQUIRED_UNBOUND
        ],
        "study_authorized": claim.study_authorized,
        "release_authority": claim.release_authority,
        "scientific_outcome": claim.observed_outcome,
        "blockers": [
            "formula artifacts are stale and quarantined",
            (
                "exact formula builds, lots, matrix, and controlled condition "
                "are unbound"
            ),
            "Orris Liquid carrier is unrecorded",
            (
                "trained panel, pilot, power, protocol, and confirmatory "
                "evidence do not exist"
            ),
            "authorized human scientific release has not occurred",
        ],
        "d1_started": False,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=PROJECT_ROOT,
    )
    return parser.parse_args()


def main() -> int:
    arguments = _parse_arguments()
    try:
        payload = build_gate_payload(arguments.repository_root)
    except (
        OSError,
        UnicodeError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        failure = {
            "schema": "d0-claim-matrix-gate-v1",
            "status": "FAIL",
            "error_category": type(error).__name__,
        }
        print(
            json.dumps(failure, sort_keys=True, separators=(",", ":")),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
