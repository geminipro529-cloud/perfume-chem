import unittest
from perfume_chem_v20_guardrails.authority import FALSE_AUTHORITY_FLAGS


class AuthorityTests(unittest.TestCase):
    def test_all_authorities_false(self) -> None:
        mapping = FALSE_AUTHORITY_FLAGS.as_mapping()
        self.assertTrue(mapping)
        self.assertFalse(any(mapping.values()))


if __name__ == "__main__":
    unittest.main()
