"""Audit summary helpers and assertion boundary."""

from __future__ import annotations


class AuditError(Exception):
    """Raised when strict ledger vs physical checks fail."""


def build_summary_message(success_count, skipped_count, failed_count, report_msg_append, interrupted):
    """Build completion/interruption summary message text."""
    if interrupted:
        return (
            f"中斷前已處理數量統計\n\n"
            f"✅ PASS: {success_count}\n"
            f"⏭️ SKIP: {skipped_count}\n"
            f"❌ FAIL: {failed_count}{report_msg_append}"
        )
    return (
        f"本次處理檔案數量統計\n\n"
        f"✅ PASS: {success_count}\n"
        f"⏭️ SKIP: {skipped_count}\n"
        f"❌ FAIL: {failed_count}{report_msg_append}"
    )


def emit_completion_dialog(
    q,
    interrupted,
    success_count,
    skipped_count,
    failed_count,
    report_msg_append,
    generated_html_reports,
    index_report_path,
):
    """Emit message-box queue event for completion/interruption."""
    msg = build_summary_message(
        success_count=success_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        report_msg_append=report_msg_append,
        interrupted=interrupted,
    )
    if interrupted:
        q.put(("msgbox", ("中斷", msg), "warning", None, index_report_path))
    else:
        q.put(("msgbox", ("完成", msg), "info", generated_html_reports, index_report_path))


__all__ = ["AuditError", "build_summary_message", "emit_completion_dialog"]
