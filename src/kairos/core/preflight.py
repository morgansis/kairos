"""Preflight guards and setup helpers for pipeline orchestration."""

from __future__ import annotations


def requires_single_source_without_time_grouping(organize_by_time, selected_folders):
    """Return True when non-time mode receives more than one source folder."""
    return (not organize_by_time) and (len(selected_folders) != 1)


def build_valid_extensions(copy_raw, copy_video, standard_extensions, raw_extensions, video_extensions):
    """Build allowed extension set according to feature flags."""
    valid_extensions = set(standard_extensions)
    if copy_raw:
        valid_extensions.update(raw_extensions)
    if copy_video:
        valid_extensions.update(video_extensions)
    return valid_extensions


__all__ = [
    "requires_single_source_without_time_grouping",
    "build_valid_extensions",
]
