"""Photo and hybrid media metadata parsing helpers."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

try:
    import exifread

    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from ..config.constants import DATE_TIME_ORIGINAL_TAG, VIDEO_EXTENSIONS
    from .video_parser import video_camera_model, video_creation_date
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import DATE_TIME_ORIGINAL_TAG, VIDEO_EXTENSIONS
    from metadata.video_parser import video_camera_model, video_creation_date


def get_media_date_with_source(file_path):
    """Return media datetime plus metadata source."""
    ext = Path(file_path).suffix.lower()

    if ext in VIDEO_EXTENSIONS:
        creation_dt = video_creation_date(file_path)
        if creation_dt is not None:
            return creation_dt, "hachoir"
        return datetime.fromtimestamp(os.path.getmtime(file_path)), "mtime"

    if EXIFREAD_AVAILABLE:
        try:
            with open(file_path, "rb") as f:
                tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
                if "EXIF DateTimeOriginal" in tags:
                    return datetime.strptime(str(tags["EXIF DateTimeOriginal"]), "%Y:%m:%d %H:%M:%S"), "exifread"
        except Exception:
            pass

    if PIL_AVAILABLE:
        try:
            with Image.open(file_path) as img:
                exif = img._getexif()
                if exif and DATE_TIME_ORIGINAL_TAG in exif:
                    return datetime.strptime(exif[DATE_TIME_ORIGINAL_TAG], "%Y:%m:%d %H:%M:%S"), "pillow"
        except Exception:
            pass

    return datetime.fromtimestamp(os.path.getmtime(file_path)), "mtime"


def get_media_date(file_path):
    media_dt, _source = get_media_date_with_source(file_path)
    return media_dt


def get_camera_model(file_path):
    ext = Path(file_path).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        model = video_camera_model(file_path)
        if model:
            return model
    else:
        if EXIFREAD_AVAILABLE:
            try:
                with open(file_path, "rb") as f:
                    tags = exifread.process_file(f, stop_tag="Image Model", details=False)
                    model = str(tags.get("Image Model", "")).strip()
                    make = str(tags.get("Image Make", "")).strip()
                    if model and make:
                        if make.lower() in model.lower():
                            return model
                        return f"{make} {model}"
                    if model:
                        return model
                    if make:
                        return make
            except Exception:
                pass
    return "-"


__all__ = [
    "EXIFREAD_AVAILABLE",
    "PIL_AVAILABLE",
    "get_media_date_with_source",
    "get_media_date",
    "get_camera_model",
]
