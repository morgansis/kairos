"""Strict audit and assertion boundary.

Target responsibility:
- volume conservation assert
- bi-directional physical vs ledger validation
- verbose/performance mode split checks
"""

class AuditError(Exception):
    """Raised when strict ledger vs physical checks fail."""


# TODO: implement auditor checks in later extraction phase.