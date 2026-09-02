from decimal import Decimal
import unittest

from perfume_chem_v20_guardrails.canonical import (
    CanonicalizationError,
    canonical_decimal,
    canonical_json_bytes,
    parse_decimal,
    sha256_payload,
)


class CanonicalTests(unittest.TestCase):
    def test_float_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            parse_decimal(0.1)  # type: ignore[arg-type]

    def test_decimal_string_is_exact(self) -> None:
        self.assertEqual(parse_decimal("0.1000"), Decimal("0.1000"))
        self.assertEqual(canonical_decimal(Decimal("1.2300")), "1.23")

    def test_hash_is_deterministic(self) -> None:
        a = sha256_payload({"b": Decimal("2.0"), "a": "x"}, domain="D")
        b = sha256_payload({"a": "x", "b": Decimal("2")}, domain="D")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_float_in_payload_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonical_json_bytes({"bad": 1.25})


if __name__ == "__main__":
    unittest.main()
