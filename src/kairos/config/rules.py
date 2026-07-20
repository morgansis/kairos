"""Declarative rules and priority tables.

Skeleton-only phase:
- Tables here are placeholders for future extraction.
- ``main.py`` currently owns runtime decision logic.
"""

DATE_FALLBACK_CHAIN = ("exifread", "pillow", "hachoir", "mtime")
GEO_FALLBACK_CHAIN = ("exifread", "pillow_heif", "exiftool")
DEDUP_DECISION_ORDER = ("IDENTICAL", "SAME_MS", "BURST", "REPLACE", "KEEP")

__all__ = [
    "DATE_FALLBACK_CHAIN",
    "GEO_FALLBACK_CHAIN",
    "DEDUP_DECISION_ORDER",
]