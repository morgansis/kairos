"""Final-phase report assembly helpers."""

from __future__ import annotations

try:
    from ..metadata.geo_engine import (
        GEO_PERF_STATS,
        collect_media_records,
        finalize_geo_perf_stats,
        save_geo_cache_to_dest,
    )
    from ..reporting.html_builder import generate_html_report
except ImportError:  # pragma: no cover - direct script execution fallback
    from metadata.geo_engine import (
        GEO_PERF_STATS,
        collect_media_records,
        finalize_geo_perf_stats,
        save_geo_cache_to_dest,
    )
    from reporting.html_builder import generate_html_report


def build_final_phase_outputs(
    dest_path,
    dest_dir,
    organize_by_time,
    enable_geo_lookup,
    q,
    stop_event,
    start_time,
    processed_size_bytes,
    performance_mode,
    success_count,
    skipped_count,
):
    """Collect final media records, GEO stats, and monthly HTML report paths."""
    generated_html_reports = []
    geo_stats = {"pass": 0, "fail": 0, "skip": 0}
    geo_fail_by_abs_path = {}
    geo_map_by_abs_path = {}
    geo_fail_reason_counter = {}

    if stop_event.is_set():
        return generated_html_reports, geo_stats, geo_fail_by_abs_path, geo_map_by_abs_path, geo_fail_reason_counter

    (
        monthly_media_map,
        geo_stats,
        geo_fail_by_abs_path,
        geo_map_by_abs_path,
        geo_fail_reason_counter,
    ) = collect_media_records(
        dest_path,
        organize_by_time,
        enable_geo_lookup,
        q,
        stop_event,
        start_time,
        processed_size_bytes,
        performance_mode,
    )

    if enable_geo_lookup:
        save_geo_cache_to_dest(dest_dir, log_callback=lambda m: q.put(("log", m)))

    finalize_geo_perf_stats(
        start_time=start_time,
        copied=success_count,
        skipped=skipped_count,
        stats=GEO_PERF_STATS,
    )

    q.put(("status", "Generating HTML preview reports from final file state..."))
    for m_key, records in monthly_media_map.items():
        generate_html_report(dest_path, m_key, records)
        generated_html_reports.append((m_key, dest_path / f"{m_key}_media_report.html"))

    return generated_html_reports, geo_stats, geo_fail_by_abs_path, geo_map_by_abs_path, geo_fail_reason_counter


__all__ = ["build_final_phase_outputs"]
