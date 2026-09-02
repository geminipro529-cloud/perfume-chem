"""Exact-byte dependency registry and fail-closed verifier."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import stat
from zipfile import ZipFile, BadZipFile


@dataclass(frozen=True)
class DependencySpec:
    filename: str
    expected_bytes: int
    expected_sha256: str
    expected_members: int | None = None
    stale_sha256: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExactByteDecision:
    state: str
    exact_match: bool
    observed_filename: str | None
    observed_bytes: int | None
    observed_sha256: str | None
    archive_safety: str
    reason: str
    installation_authority: bool = False
    scientific_authority: bool = False


DEPENDENCIES: tuple[DependencySpec, ...] = (
    DependencySpec(
        filename="UNIVERSAL_ACCORD_INTELLIGENCE_MODULE_v1.zip",
        expected_bytes=539050,
        expected_sha256="8dd04ea6c69e5e3bd72b03e0ae15cb66ad66e9ac5581cf97666249e869c5a998",
        expected_members=27,
        stale_sha256=("8a9cbdfb9f28c489b56a8c6391757854def53feb77e70c2dc3e81cc6696cd05a",),
    ),
    DependencySpec(
        filename="PERFUME_CHEM_CANONICAL_CUTOVER_READY_20260808_v2.zip",
        expected_bytes=1228587,
        expected_sha256="e9e325bea9117dbe2a97ff67e77d57705a54244591278fac7a34915a7f0ae523",
        expected_members=198,
    ),
    DependencySpec(
        filename="Perfume_Chem_Physics_OAV_Decision_Model_v3_4_0_CALIBRATION_READY.zip",
        expected_bytes=540402,
        expected_sha256="8224f8a1609deb22b43651da825b9bf653a92143f00ee1d5d592130d162f97db",
    ),
    DependencySpec(
        filename="perfume_chem_physics_oav_v3-3.4.0-py3-none-any.whl",
        expected_bytes=65724,
        expected_sha256="582ae9902e47807f085a61b7add113c9239a2860445e8171fcf569b3ad6d28c5",
    ),
)


def dependency_by_filename(filename: str) -> DependencySpec:
    for spec in DEPENDENCIES:
        if spec.filename == filename:
            return spec
    raise KeyError(filename)


def verify_exact_path(path: str | Path, spec: DependencySpec) -> ExactByteDecision:
    candidate = Path(path)
    if not candidate.is_file():
        return ExactByteDecision(
            state="HOLD_EXACT_BYTES_UNAVAILABLE",
            exact_match=False,
            observed_filename=(candidate.name if candidate.name else None),
            observed_bytes=None,
            observed_sha256=None,
            archive_safety="NOT_RUN",
            reason="exact source byte stream is not materialized",
        )
    data = candidate.read_bytes()
    return verify_exact_bytes(data=data, observed_filename=candidate.name, spec=spec)


def verify_exact_bytes(
    *, data: bytes, observed_filename: str, spec: DependencySpec
) -> ExactByteDecision:
    digest = hashlib.sha256(data).hexdigest()
    size = len(data)
    if digest in spec.stale_sha256:
        return ExactByteDecision(
            state="REJECT_STALE_SAME_NAME_VARIANT",
            exact_match=False,
            observed_filename=observed_filename,
            observed_bytes=size,
            observed_sha256=digest,
            archive_safety="NOT_RUN",
            reason="same-name stale lineage cannot satisfy the current exact-byte dependency",
        )
    if observed_filename != spec.filename:
        return ExactByteDecision(
            state="REJECT_FILENAME_MISMATCH",
            exact_match=False,
            observed_filename=observed_filename,
            observed_bytes=size,
            observed_sha256=digest,
            archive_safety="NOT_RUN",
            reason="exact dependency requires the specified filename and bytes",
        )
    if size != spec.expected_bytes or digest != spec.expected_sha256:
        return ExactByteDecision(
            state="REJECT_SIZE_OR_HASH_MISMATCH",
            exact_match=False,
            observed_filename=observed_filename,
            observed_bytes=size,
            observed_sha256=digest,
            archive_safety="NOT_RUN",
            reason="regenerated, reconstructed, compatible, or corrupted bytes are not substitutes",
        )

    safety, member_count, reason = inspect_zip_safety(data)
    if safety != "PASS":
        return ExactByteDecision(
            state="REJECT_ARCHIVE_SAFETY",
            exact_match=False,
            observed_filename=observed_filename,
            observed_bytes=size,
            observed_sha256=digest,
            archive_safety=safety,
            reason=reason,
        )
    if spec.expected_members is not None and member_count != spec.expected_members:
        return ExactByteDecision(
            state="REJECT_MEMBER_COUNT_MISMATCH",
            exact_match=False,
            observed_filename=observed_filename,
            observed_bytes=size,
            observed_sha256=digest,
            archive_safety="PASS",
            reason=f"expected {spec.expected_members} members, observed {member_count}",
        )
    return ExactByteDecision(
        state="EXACT_BYTES_VERIFIED__QUARANTINE_ONLY",
        exact_match=True,
        observed_filename=observed_filename,
        observed_bytes=size,
        observed_sha256=digest,
        archive_safety="PASS",
        reason="exact recovery permits quarantine review only; no installation or scientific promotion",
    )


def inspect_zip_safety(data: bytes) -> tuple[str, int | None, str]:
    from io import BytesIO

    try:
        with ZipFile(BytesIO(data)) as archive:
            names: list[str] = []
            casefolded: set[str] = set()
            for info in archive.infolist():
                name = info.filename
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    return "FAIL_UNSAFE_PATH", None, f"unsafe archive path: {name}"
                folded = name.casefold()
                if name in names:
                    return "FAIL_DUPLICATE_PATH", None, f"duplicate archive path: {name}"
                if folded in casefolded:
                    return "FAIL_CASEFOLD_COLLISION", None, f"case-fold collision: {name}"
                names.append(name)
                casefolded.add(folded)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    return "FAIL_SYMLINK", None, f"symlink archive member: {name}"
            bad = archive.testzip()
            if bad is not None:
                return "FAIL_CRC", None, f"CRC failure: {bad}"
            return "PASS", len(archive.infolist()), "archive safety and CRC checks passed"
    except BadZipFile:
        return "FAIL_NOT_ZIP", None, "candidate is not a valid ZIP/WHL container"
