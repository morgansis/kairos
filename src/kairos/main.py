"""Kairos desktop entrypoint.

This module intentionally stays small after the refactor:
- UI/runtime logic lives in ``ui/app.py``
- ``main.py`` only boots the app and wires SIGINT handling
"""

from __future__ import annotations

import signal
import sys
import traceback

import customtkinter as ctk

try:
    from .ui.app import ImageOrganizerAppModern, sigint_handler
except ImportError:  # pragma: no cover - direct script execution fallback
    from ui.app import ImageOrganizerAppModern, sigint_handler


# Accessed by ``ui.app.sigint_handler`` via ``__main__`` globals.
root = None
app = None


def main() -> int:
    """Start Kairos UI and return process exit code."""
    global root, app

    try:
        # Keep legacy visual defaults so refactor does not change UI look.
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        root = ctk.CTk()
        app = ImageOrganizerAppModern(root)

        try:
            signal.signal(signal.SIGINT, sigint_handler)
        except Exception:
            # Some environments may not allow replacing signal handlers.
            pass

        root.mainloop()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        print("[FATAL] Kairos failed to start.", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
