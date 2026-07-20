"""Geo performance counter helpers."""

from __future__ import annotations

import time


def reset_geo_perf_stats(stats):
    """Reset geo performance counters to startup defaults."""
    stats["queries"] = 0
    stats["cache_hits"] = 0
    stats["new_lookups"] = 0
    stats["copied"] = 0
    stats["skipped"] = 0
    stats["total_time"] = 0.0


def finalize_geo_perf_stats(start_time, copied, skipped, stats):
    """Persist end-of-run geo performance values."""
    stats["total_time"] = time.time() - start_time
    stats["copied"] = copied
    stats["skipped"] = skipped


__all__ = ["reset_geo_perf_stats", "finalize_geo_perf_stats"]
