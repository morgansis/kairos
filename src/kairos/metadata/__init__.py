"""Metadata engine boundary.

Goal: isolate all media parsing and dedup arbitration logic.
"""

__all__ = ["exif_parser", "video_parser", "geo_engine", "arbiter"]