import unittest

from perfume_chem_v20_guardrails.runtime_policy import (
    RuntimeRequest,
    provider_outcome,
    validate_runtime_request,
)


def valid_request(**changes):
    values = dict(
        project_id="perfume-chem-cheapluna-isolated",
        profile="cheapluna-chat",
        route="DIRECT_PRO",
        luna_mode="NO_LUNA",
        deep_luna_fast_enabled=False,
        alternate_fallbacks_enabled=False,
    )
    values.update(changes)
    return RuntimeRequest(**values)


class RuntimePolicyTests(unittest.TestCase):
    def test_exact_policy_matches(self) -> None:
        decision = validate_runtime_request(valid_request())
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.fallback_used)

    def test_project_mismatch_rejected(self) -> None:
        decision = validate_runtime_request(valid_request(project_id="other"))
        self.assertFalse(decision.allowed)
        self.assertIn("project-id mismatch", decision.reasons)

    def test_fast_rejected(self) -> None:
        decision = validate_runtime_request(valid_request(deep_luna_fast_enabled=True))
        self.assertFalse(decision.allowed)
        self.assertIn("DeepLuna Fast is disabled", decision.reasons)

    def test_alternate_fallback_rejected(self) -> None:
        decision = validate_runtime_request(valid_request(alternate_fallbacks_enabled=True))
        self.assertFalse(decision.allowed)

    def test_unapproved_route_rejected(self) -> None:
        decision = validate_runtime_request(valid_request(route="FALLBACK_ROUTE"))
        self.assertFalse(decision.allowed)
        self.assertIn("unapproved route", decision.reasons)

    def test_provider_failure_remains_failure(self) -> None:
        decision = provider_outcome(request=valid_request(), provider_succeeded=False)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.state, "PROVIDER_FAILURE_NO_FALLBACK")
        self.assertFalse(decision.fallback_used)

    def test_provider_success_does_not_imply_deployment(self) -> None:
        decision = provider_outcome(request=valid_request(), provider_succeeded=True)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.state, "PROVIDER_SUCCESS")
        self.assertFalse(decision.fallback_used)


if __name__ == "__main__":
    unittest.main()
