import unittest

from perfume_chem_v20_guardrails.source_admission import (
    SourceOperation,
    SourceRights,
    SourceUseRequest,
    decide_source_use,
)


class SourceAdmissionTests(unittest.TestCase):
    def request(self, operation, **overrides):
        values = dict(
            source_id="QUARANTINED-SOURCE",
            rights=SourceRights.UNRESOLVED,
            operation=operation,
            exact_bytes_present=True,
            hash_verified=True,
            quarantine_manifest_read_allowed=True,
            operation_explicitly_approved=False,
        )
        values.update(overrides)
        return SourceUseRequest(**values)

    def test_verify_bytes_allowed_with_unresolved_rights(self) -> None:
        decision = decide_source_use(self.request(SourceOperation.VERIFY_BYTES))
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.authority_promoted)

    def test_manifest_read_allowed_only_for_quarantine(self) -> None:
        decision = decide_source_use(self.request(SourceOperation.READ_MANIFEST_FOR_QUARANTINE))
        self.assertTrue(decision.allowed)
        self.assertIn("QUARANTINE", decision.state)

    def test_import_module_denied_even_when_hash_matches(self) -> None:
        decision = decide_source_use(self.request(SourceOperation.IMPORT_MODULE))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.state, "DENY_UNRESOLVED_SOURCE_RIGHTS")

    def test_all_promoting_operations_denied_for_unresolved_rights(self) -> None:
        operations = [
            SourceOperation.IMPORT_SCHEMA,
            SourceOperation.IMPORT_REGISTRY,
            SourceOperation.IMPORT_FORMULA,
            SourceOperation.IMPORT_EVIDENCE_LEDGER,
            SourceOperation.EXECUTE,
            SourceOperation.PROMOTE,
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                self.assertFalse(decide_source_use(self.request(operation)).allowed)

    def test_missing_exact_bytes_hold_verification(self) -> None:
        decision = decide_source_use(
            self.request(SourceOperation.VERIFY_BYTES, exact_bytes_present=False)
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.state, "HOLD_SOURCE_BYTES")

    def test_resolved_rights_still_require_hash_and_explicit_operation(self) -> None:
        request = self.request(
            SourceOperation.IMPORT_MODULE,
            rights=SourceRights.RESOLVED,
            hash_verified=True,
            operation_explicitly_approved=False,
        )
        self.assertEqual(decide_source_use(request).state, "DENY_OPERATION_NOT_APPROVED")

    def test_resolved_scoped_operation_does_not_promote_authority(self) -> None:
        request = self.request(
            SourceOperation.IMPORT_MODULE,
            rights=SourceRights.RESOLVED,
            hash_verified=True,
            operation_explicitly_approved=True,
        )
        decision = decide_source_use(request)
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.authority_promoted)


if __name__ == "__main__":
    unittest.main()
