"""Logging and warning interception helpers."""

from __future__ import annotations

import io
import sys
import logging


class PluginWarningCapturer:
    """Capture third-party parser warnings from exifread/hachoir and stderr."""

    def __init__(self):
        self.output = io.StringIO()
        self.handler = logging.StreamHandler(self.output)
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.old_stderr = sys.stderr
        self.old_hachoir_handler = None

    def __enter__(self):
        sys.stderr = self.output
        exifread_logger = logging.getLogger("exifread")
        exifread_logger.addHandler(self.handler)
        exifread_logger.setLevel(logging.WARNING)
        try:
            import hachoir.core.warning as h_warn

            self.old_hachoir_handler = h_warn.logWarning
            h_warn.logWarning = self._hachoir_warn_callback
        except Exception:
            pass
        return self

    def _hachoir_warn_callback(self, msg, *args, **kwargs):
        self.output.write(f"[hachoir] {msg}\n")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr = self.old_stderr
        logging.getLogger("exifread").removeHandler(self.handler)
        try:
            import hachoir.core.warning as h_warn

            if self.old_hachoir_handler:
                h_warn.logWarning = self.old_hachoir_handler
        except Exception:
            pass

    def get_messages(self):
        content = self.output.getvalue().strip()
        if not content:
            return []
        return [line.strip() for line in content.split("\n") if line.strip()]
