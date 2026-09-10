from io import BytesIO
import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from perfume_chem_v20_guardrails.exact_bytes import (
    DependencySpec,
    dependency_by_filename,
    inspect_zip_safety,
    verify_exact_bytes,
    verify_exact_path,
)


def zip_bytes(entries):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return buffer.getvalue()


class ExactByteTests(unittest.TestCase):
    def test_missing_dependency_is_hold(self) -> None:
        spec = dependency_by_filename("UNIVERSAL_ACCORD_INTELLIGENCE_MODULE_v1.zip")
        result = verify_exact_path("/definitely/not/present.zip", spec)
        self.assertEqual(result.state, "HOLD_EXACT_BYTES_UNAVAILABLE")
        self.assertFalse(result.exact_match)

    def test_size_or_hash_mismatch_rejected(self) -> None:
        data = zip_bytes([("x", b"y")])
        spec = DependencySpec("target.zip", len(data), "0" * 64)
        result = verify_exact_bytes(data=data, observed_filename="target.zip", spec=spec)
        self.assertEqual(result.state, "REJECT_SIZE_OR_HASH_MISMATCH")

    def test_stale_same_name_hash_rejected(self) -> None:
        data = zip_bytes([("x", b"y")])
        digest = hashlib.sha256(data).hexdigest()
        spec = DependencySpec(
            filename="target.zip",
            expected_bytes=len(data),
            expected_sha256="f" * 64,
            stale_sha256=(digest,),
        )
        result = verify_exact_bytes(data=data, observed_filename="target.zip", spec=spec)
        self.assertEqual(result.state, "REJECT_STALE_SAME_NAME_VARIANT")

    def test_exact_safe_zip_passes_quarantine_only(self) -> None:
        data = zip_bytes([("a.txt", b"a"), ("b.txt", b"b")])
        spec = DependencySpec(
            filename="target.zip",
            expected_bytes=len(data),
            expected_sha256=hashlib.sha256(data).hexdigest(),
            expected_members=2,
        )
        result = verify_exact_bytes(data=data, observed_filename="target.zip", spec=spec)
        self.assertTrue(result.exact_match)
        self.assertEqual(result.state, "EXACT_BYTES_VERIFIED__QUARANTINE_ONLY")
        self.assertFalse(result.installation_authority)
        self.assertFalse(result.scientific_authority)

    def test_member_count_mismatch_rejected(self) -> None:
        data = zip_bytes([("a.txt", b"a")])
        spec = DependencySpec(
            filename="target.zip",
            expected_bytes=len(data),
            expected_sha256=hashlib.sha256(data).hexdigest(),
            expected_members=2,
        )
        result = verify_exact_bytes(data=data, observed_filename="target.zip", spec=spec)
        self.assertEqual(result.state, "REJECT_MEMBER_COUNT_MISMATCH")

    def test_unsafe_parent_path_rejected(self) -> None:
        data = zip_bytes([("../escape.txt", b"x")])
        state, _, _ = inspect_zip_safety(data)
        self.assertEqual(state, "FAIL_UNSAFE_PATH")

    def test_filename_mismatch_rejected(self) -> None:
        data = zip_bytes([("a", b"b")])
        spec = DependencySpec(
            filename="expected.zip",
            expected_bytes=len(data),
            expected_sha256=hashlib.sha256(data).hexdigest(),
        )
        result = verify_exact_bytes(data=data, observed_filename="other.zip", spec=spec)
        self.assertEqual(result.state, "REJECT_FILENAME_MISMATCH")

    def test_path_verification_hashes_actual_file(self) -> None:
        data = zip_bytes([("a", b"b")])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "target.zip"
            path.write_bytes(data)
            spec = DependencySpec(
                filename="target.zip",
                expected_bytes=len(data),
                expected_sha256=hashlib.sha256(data).hexdigest(),
                expected_members=1,
            )
            result = verify_exact_path(path, spec)
            self.assertTrue(result.exact_match)


if __name__ == "__main__":
    unittest.main()
