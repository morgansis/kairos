"""Video metadata parsing helpers."""

from __future__ import annotations

from pathlib import Path

try:
    from hachoir.metadata import extractMetadata
    from hachoir.parser import createParser

    HACHOIR_AVAILABLE = True
except ImportError:
    HACHOIR_AVAILABLE = False

try:
    from ..config.constants import VIDEO_EXTENSIONS
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import VIDEO_EXTENSIONS


def video_creation_date(file_path):
    """Read video creation timestamp via hachoir when available."""
    ext = Path(file_path).suffix.lower()
    if ext not in VIDEO_EXTENSIONS or not HACHOIR_AVAILABLE:
        return None
    try:
        parser = createParser(str(file_path))
        if parser:
            with parser:
                metadata = extractMetadata(parser)
                if metadata and metadata.has("creation_date"):
                    return metadata.get("creation_date")
    except Exception:
        pass
    return None


def video_camera_model(file_path):
    """Read video camera model via hachoir when available."""
    ext = Path(file_path).suffix.lower()
    if ext not in VIDEO_EXTENSIONS or not HACHOIR_AVAILABLE:
        return None
    try:
        parser = createParser(str(file_path))
        if parser:
            with parser:
                metadata = extractMetadata(parser)
                if metadata and metadata.has("camera_model"):
                    value = str(metadata.get("camera_model")).strip()
                    if value:
                        return value
    except Exception:
        pass
    return None


__all__ = ["HACHOIR_AVAILABLE", "video_creation_date", "video_camera_model"]
