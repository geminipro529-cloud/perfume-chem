"""Standalone V20 guardrail candidate.

This package is an implementation and regression-test candidate only. It is not
installed in Perfume-Chem and grants no scientific, physical, inventory, safety,
or release authority.
"""

from .authority import FALSE_AUTHORITY_FLAGS, AuthorityFlags

__all__ = ["FALSE_AUTHORITY_FLAGS", "AuthorityFlags"]
__version__ = "0.1.0-candidate"
