"""Declarative rules and priority tables.

Skeleton-only phase:
- Tables here are placeholders for future extraction.
- ``main.py`` currently owns runtime decision logic.
"""

DATE_FALLBACK_CHAIN = ("exifread", "pillow", "hachoir", "mtime")
GEO_FALLBACK_CHAIN = ("exifread", "pillow_heif", "exiftool")
DEDUP_DECISION_ORDER = ("IDENTICAL", "SAME_MS", "BURST", "REPLACE", "KEEP")


def is_kairos_self_file(filename):
    """Return True for Kairos-generated files that should be ignored during scans."""
    if filename.endswith("_media_report.html") or filename == "_index.html":
        return True
    system_prefixes = ("_manifest_", "_kairos_")
    return filename.startswith(system_prefixes)

__all__ = [
    "DATE_FALLBACK_CHAIN",
    "GEO_FALLBACK_CHAIN",
    "DEDUP_DECISION_ORDER",
    "is_kairos_self_file",
]
