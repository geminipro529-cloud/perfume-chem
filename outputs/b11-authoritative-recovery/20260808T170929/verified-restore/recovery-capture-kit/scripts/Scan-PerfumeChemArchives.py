#!/usr/bin/env python3
"""Recursively index ZIP archives without extracting or rewriting source bytes.

The scanner preserves archive chains, hashes readable members, reports CRC and
path defects, finds exact or wildcard recovery targets, and searches for the
18 CP6 PRE_DEF fragment files and full SHA-256 ledgers.

Only Python's standard library is used. Source files are opened read-only.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterable, Sequence

CHUNK = 1024 * 1024
TEXT_SCAN_LIMIT = 8 * 1024 * 1024
DEFAULT_MAX_MEMBER_BYTES = 4 * 1024 * 1024 * 1024
DEFAULT_MAX_NESTED_ARCHIVE_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 64 * 1024 * 1024 * 1024
DEFAULT_EXCLUDED_DIRS = {
    "00_METADATA",
    "04_MANIFESTS",
    "06_UPLOAD_STAGING",
    "07_UPLOAD_CHUNKS",
    "99_PRIVATE_LOCAL_ONLY_DO_NOT_UPLOAD",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
}

PREDEF_FRAGMENT_RE = re.compile(
    r"(?:^|/)runs/2026-08-05_055546/workers/(PIL-\d{2}-[A-Za-z])/fragment\.json$",
    re.IGNORECASE,
)
FULL_SHA_RE = re.compile(rb"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


@dataclass(slots=True)
class ArchiveRecord:
    outer_file: str
    archive_chain: str
    depth: int
    member_path: str
    member_leaf: str
    member_size: int
    compressed_size: int
    compression_ratio: float | None
    crc32_hex: str
    sha256: str
    is_zip: bool
    nested_scan_state: str
    unsafe_path: bool
    duplicate_member_path: bool
    suspicious_compression_ratio: bool
    predef_candidate: bool
    full_sha256_count: int


@dataclass(slots=True)
class ErrorRecord:
    outer_file: str
    archive_chain: str
    depth: int
    member_path: str
    error_type: str
    message: str


@dataclass(slots=True)
class Target:
    source: str
    name_or_pattern: str
    expected_sha256: str


@dataclass(slots=True)
class TargetMatch:
    target_source: str
    target_name_or_pattern: str
    expected_sha256: str
    match_state: str
    location_type: str
    outer_file: str
    archive_chain: str
    member_path: str
    found_sha256: str
    found_size: int | None


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            hasher.update(chunk)
    return hasher.hexdigest()


def unsafe_member_path(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return True
    parts = PurePosixPath(normalized).parts
    return ".." in parts


def is_zip_magic(data: bytes) -> bool:
    return any(data.startswith(magic) for magic in ZIP_MAGIC)


def should_skip_path(path: Path, root: Path, excluded: set[str]) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part in excluded for part in relative.parts[:-1])


def iter_top_level_zips(root: Path, excluded: set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".zip":
            continue
        if should_skip_path(path, root, excluded):
            continue
        yield path


def read_member_once(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    capture_full: bool,
    total_budget: list[int],
    max_total_bytes: int,
) -> tuple[str, bytes, bytes, int]:
    hasher = hashlib.sha256()
    prefix = bytearray()
    full = bytearray() if capture_full else None
    total = 0
    with archive.open(info, "r") as stream:
        while True:
            chunk = stream.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            total_budget[0] += len(chunk)
            if total_budget[0] > max_total_bytes:
                raise RuntimeError(f"TOTAL_SCAN_BUDGET_EXCEEDED:{max_total_bytes}")
            hasher.update(chunk)
            if len(prefix) < TEXT_SCAN_LIMIT:
                prefix.extend(chunk[: TEXT_SCAN_LIMIT - len(prefix)])
            if full is not None:
                full.extend(chunk)
    return hasher.hexdigest(), bytes(prefix), bytes(full) if full is not None else b"", total


def load_targets(registers: Path | None) -> list[Target]:
    if registers is None or not registers.exists():
        return []
    targets: list[Target] = []

    def read_csv(name: str) -> list[dict[str, str]]:
        path = registers / name
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    for row in read_csv("MISSING_EXACT_BYTES_REGISTER.csv"):
        name = (row.get("filename") or "").strip()
        if name:
            targets.append(Target("MISSING_EXACT_BYTES_REGISTER", name, (row.get("known_sha256") or "").strip().lower()))
    for row in read_csv("VISIBLE_UNMOUNTED_BATCHES_REGISTER.csv"):
        name = (row.get("filename_or_pattern") or "").strip()
        if name:
            targets.append(Target("VISIBLE_UNMOUNTED_BATCHES_REGISTER", name, ""))
    for row in read_csv("FILE_LIBRARY_EXACT_PACKAGE_RECOVERY_QUEUE.csv"):
        name = (row.get("filename") or "").strip()
        if name:
            targets.append(Target("FILE_LIBRARY_EXACT_PACKAGE_RECOVERY_QUEUE", name, (row.get("sha256") or "").strip().lower()))
    return targets


def name_matches(pattern: str, candidate_leaf: str) -> bool:
    p = pattern.casefold()
    c = candidate_leaf.casefold()
    if any(char in pattern for char in "*?["):
        return fnmatch.fnmatchcase(c, p)
    return c == p


def write_csv(path: Path, rows: Sequence[dict], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def scan_archive(
    *,
    archive: zipfile.ZipFile,
    outer_file: str,
    archive_chain: list[str],
    depth: int,
    max_depth: int,
    max_member_bytes: int,
    max_nested_archive_bytes: int,
    total_budget: list[int],
    max_total_bytes: int,
    records: list[ArchiveRecord],
    errors: list[ErrorRecord],
) -> None:
    names = Counter(info.filename for info in archive.infolist() if not info.is_dir())

    for info in archive.infolist():
        if info.is_dir():
            continue
        chain_text = "!".join(archive_chain)
        duplicate = names[info.filename] > 1
        ratio = None if info.compress_size == 0 else info.file_size / info.compress_size
        suspicious_ratio = bool(ratio is not None and ratio > 10000 and info.file_size > 10 * 1024 * 1024)
        if duplicate:
            errors.append(ErrorRecord(outer_file, chain_text, depth, info.filename, "DUPLICATE_MEMBER_PATH", "Duplicate path inside one ZIP"))
        if unsafe_member_path(info.filename):
            errors.append(ErrorRecord(outer_file, chain_text, depth, info.filename, "UNSAFE_MEMBER_PATH", "Absolute or parent-traversal path"))
        if suspicious_ratio:
            errors.append(ErrorRecord(outer_file, chain_text, depth, info.filename, "SUSPICIOUS_COMPRESSION_RATIO", f"ratio={ratio:.2f}"))
        if info.file_size > max_member_bytes:
            errors.append(ErrorRecord(outer_file, chain_text, depth, info.filename, "MEMBER_TOO_LARGE", f"{info.file_size}>{max_member_bytes}"))
            continue

        zip_by_name = info.filename.lower().endswith(".zip")
        capture_full = zip_by_name and info.file_size <= max_nested_archive_bytes
        try:
            digest, prefix, full_data, actual = read_member_once(
                archive,
                info,
                capture_full=capture_full,
                total_budget=total_budget,
                max_total_bytes=max_total_bytes,
            )
        except Exception as exc:
            errors.append(ErrorRecord(outer_file, chain_text, depth, info.filename, type(exc).__name__, str(exc)))
            if "TOTAL_SCAN_BUDGET_EXCEEDED" in str(exc):
                return
            continue

        zip_by_magic = is_zip_magic(prefix)
        is_zip = zip_by_name or zip_by_magic
        nested_state = "NOT_ZIP"
        if is_zip:
            if depth >= max_depth:
                nested_state = "MAX_DEPTH_HOLD"
            elif info.file_size > max_nested_archive_bytes:
                nested_state = "NESTED_ARCHIVE_TOO_LARGE_HOLD"
            else:
                if not full_data:
                    try:
                        with archive.open(info, "r") as nested_stream:
                            full_data = nested_stream.read()
                            total_budget[0] += len(full_data)
                            if total_budget[0] > max_total_bytes:
                                raise RuntimeError(f"TOTAL_SCAN_BUDGET_EXCEEDED:{max_total_bytes}")
                    except Exception as exc:
                        nested_state = "NESTED_READ_ERROR"
                        errors.append(ErrorRecord(outer_file, chain_text, depth, info.filename, type(exc).__name__, str(exc)))
                if full_data:
                    try:
                        with zipfile.ZipFile(io.BytesIO(full_data)) as nested_archive:
                            nested_state = "SCANNED"
                            scan_archive(
                                archive=nested_archive,
                                outer_file=outer_file,
                                archive_chain=[*archive_chain, info.filename],
                                depth=depth + 1,
                                max_depth=max_depth,
                                max_member_bytes=max_member_bytes,
                                max_nested_archive_bytes=max_nested_archive_bytes,
                                total_budget=total_budget,
                                max_total_bytes=max_total_bytes,
                                records=records,
                                errors=errors,
                            )
                    except Exception as exc:
                        nested_state = "NESTED_ZIP_ERROR"
                        errors.append(ErrorRecord(outer_file, chain_text, depth, info.filename, type(exc).__name__, str(exc)))

        normalized_member = info.filename.replace("\\", "/")
        predef = bool(PREDEF_FRAGMENT_RE.search(normalized_member)) or any(
            token in normalized_member.upper() for token in ("PREQUALIFICATION_SNAPSHOT", "PRE_DEF")
        )
        full_sha_count = len(FULL_SHA_RE.findall(prefix))
        records.append(
            ArchiveRecord(
                outer_file=outer_file,
                archive_chain=chain_text,
                depth=depth,
                member_path=info.filename,
                member_leaf=PurePosixPath(normalized_member).name,
                member_size=actual,
                compressed_size=info.compress_size,
                compression_ratio=round(ratio, 6) if ratio is not None else None,
                crc32_hex=f"{info.CRC:08x}",
                sha256=digest,
                is_zip=is_zip,
                nested_scan_state=nested_state,
                unsafe_path=unsafe_member_path(info.filename),
                duplicate_member_path=duplicate,
                suspicious_compression_ratio=suspicious_ratio,
                predef_candidate=predef,
                full_sha256_count=full_sha_count,
            )
        )


def build_target_matches(
    *,
    root: Path,
    top_level_paths: Sequence[Path],
    records: Sequence[ArchiveRecord],
    targets: Sequence[Target],
) -> list[TargetMatch]:
    matches: list[TargetMatch] = []
    top_candidates: list[tuple[str, str, int, str]] = []
    for path in top_level_paths:
        relative = path.relative_to(root).as_posix()
        try:
            digest = sha256_file(path)
            size = path.stat().st_size
        except Exception:
            continue
        top_candidates.append((path.name, relative, size, digest))

    for target in targets:
        found: list[TargetMatch] = []
        for leaf, relative, size, digest in top_candidates:
            if not name_matches(target.name_or_pattern, leaf):
                continue
            state = "EXACT_NAME_AND_HASH" if target.expected_sha256 and digest == target.expected_sha256 else (
                "NAME_FOUND_HASH_MISMATCH" if target.expected_sha256 else "NAME_OR_PATTERN_FOUND"
            )
            found.append(TargetMatch(target.source, target.name_or_pattern, target.expected_sha256, state, "TOP_LEVEL_FILE", relative, relative, "", digest, size))
        for record in records:
            if not name_matches(target.name_or_pattern, record.member_leaf):
                continue
            state = "EXACT_NAME_AND_HASH" if target.expected_sha256 and record.sha256 == target.expected_sha256 else (
                "NAME_FOUND_HASH_MISMATCH" if target.expected_sha256 else "NAME_OR_PATTERN_FOUND"
            )
            found.append(TargetMatch(target.source, target.name_or_pattern, target.expected_sha256, state, "ARCHIVE_MEMBER", record.outer_file, record.archive_chain, record.member_path, record.sha256, record.member_size))
        if found:
            matches.extend(found)
        else:
            matches.append(TargetMatch(target.source, target.name_or_pattern, target.expected_sha256, "NOT_FOUND", "", "", "", "", "", None))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--registers", type=Path)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--max-member-bytes", type=int, default=DEFAULT_MAX_MEMBER_BYTES)
    parser.add_argument("--max-nested-archive-bytes", type=int, default=DEFAULT_MAX_NESTED_ARCHIVE_BYTES)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    excluded = set(DEFAULT_EXCLUDED_DIRS)

    top_level = sorted(iter_top_level_zips(root, excluded))
    records: list[ArchiveRecord] = []
    errors: list[ErrorRecord] = []
    total_budget = [0]

    for zip_path in top_level:
        relative = zip_path.relative_to(root).as_posix()
        try:
            with zipfile.ZipFile(zip_path) as archive:
                scan_archive(
                    archive=archive,
                    outer_file=relative,
                    archive_chain=[relative],
                    depth=1,
                    max_depth=args.max_depth,
                    max_member_bytes=args.max_member_bytes,
                    max_nested_archive_bytes=args.max_nested_archive_bytes,
                    total_budget=total_budget,
                    max_total_bytes=args.max_total_bytes,
                    records=records,
                    errors=errors,
                )
        except Exception as exc:
            errors.append(ErrorRecord(relative, relative, 0, "", type(exc).__name__, str(exc)))
            if "TOTAL_SCAN_BUDGET_EXCEEDED" in str(exc):
                break

    record_fields = list(ArchiveRecord.__dataclass_fields__)
    error_fields = list(ErrorRecord.__dataclass_fields__)
    write_csv(output / "ARCHIVE_MEMBER_INDEX.csv", [asdict(r) for r in records], record_fields)
    write_csv(output / "ARCHIVE_ERRORS.csv", [asdict(e) for e in errors], error_fields)

    by_hash: dict[str, list[ArchiveRecord]] = defaultdict(list)
    for record in records:
        by_hash[record.sha256].append(record)
    duplicate_rows: list[dict] = []
    for digest, aliases in sorted(by_hash.items()):
        if len(aliases) < 2:
            continue
        for alias in aliases:
            duplicate_rows.append({
                "sha256": digest,
                "alias_count": len(aliases),
                "outer_file": alias.outer_file,
                "archive_chain": alias.archive_chain,
                "member_path": alias.member_path,
                "member_size": alias.member_size,
            })
    write_csv(output / "ARCHIVE_DUPLICATE_ALIASES.csv", duplicate_rows, ["sha256", "alias_count", "outer_file", "archive_chain", "member_path", "member_size"])

    predef_rows = [
        asdict(record)
        for record in records
        if record.predef_candidate
        or PREDEF_FRAGMENT_RE.search(record.member_path.replace("\\", "/"))
        or (
            record.full_sha256_count > 0
            and any(token in record.member_path.upper() for token in ("SHA", "LEDGER", "MANIFEST", "RECEIPT"))
        )
    ]
    write_csv(output / "PRE_DEF_RECOVERY_CANDIDATES.csv", predef_rows, record_fields)

    targets = load_targets(args.registers.resolve() if args.registers else None)
    target_matches = build_target_matches(root=root, top_level_paths=top_level, records=records, targets=targets)
    target_fields = list(TargetMatch.__dataclass_fields__)
    write_csv(output / "NESTED_RECOVERY_TARGET_MATCHES.csv", [asdict(m) for m in target_matches], target_fields)

    branch_hits = sorted({
        match.group(1).upper()
        for record in records
        if (match := PREDEF_FRAGMENT_RE.search(record.member_path.replace("\\", "/")))
    })
    summary = {
        "root": str(root),
        "scanned_utc": datetime.now(timezone.utc).isoformat(),
        "excluded_directory_names": sorted(excluded),
        "top_level_zip_files": len(top_level),
        "archive_member_records": len(records),
        "unique_member_sha256": len(by_hash),
        "duplicate_hash_groups": sum(1 for aliases in by_hash.values() if len(aliases) > 1),
        "unsafe_member_paths": sum(record.unsafe_path for record in records),
        "duplicate_member_paths": sum(record.duplicate_member_path for record in records),
        "suspicious_compression_ratio_records": sum(record.suspicious_compression_ratio for record in records),
        "scan_errors": len(errors),
        "nested_bytes_read": total_budget[0],
        "predef_candidate_records": len(predef_rows),
        "authentic_predef_branch_ids_found": branch_hits,
        "authentic_predef_branch_count": len(branch_hits),
        "prequalification_snapshot_name_hits": sum("PREQUALIFICATION_SNAPSHOT" in record.member_path.upper() for record in records),
        "full_sha_ledger_candidate_records": sum(
            record.full_sha256_count > 0 and any(token in record.member_path.upper() for token in ("SHA", "LEDGER", "MANIFEST", "RECEIPT"))
            for record in records
        ),
        "recovery_targets": len(targets),
        "target_exact_hash_matches": sum(match.match_state == "EXACT_NAME_AND_HASH" for match in target_matches),
        "target_name_or_pattern_matches": sum("FOUND" in match.match_state or match.match_state == "EXACT_NAME_AND_HASH" for match in target_matches),
        "targets_not_found": sum(match.match_state == "NOT_FOUND" for match in target_matches),
        "source_mutations": 0,
    }
    (output / "ARCHIVE_SCAN_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))

    # Errors are reported but do not erase all useful results. Return 2 for partial scan.
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
