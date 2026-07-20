"""Deduplication and collision arbitration boundary.

Planned migration targets from main.py:
- is_same_millisecond_capture
- is_burst_shot
- compare_and_decide
- second_pass_month
"""

DECISIONS = ("IDENTICAL", "SAME_MS", "BURST", "REPLACE", "KEEP")

__all__ = ["DECISIONS"]