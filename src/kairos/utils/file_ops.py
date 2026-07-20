"""Filesystem and hashing helpers."""

from __future__ import annotations

import os
import hashlib
from pathlib import Path

try:
    from ..config.constants import TIMESTAMP_STEM_RE
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import TIMESTAMP_STEM_RE


def file_sha256(file_path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_identical_file(src_path, target_path):
    """Fast header/tail check + full SHA-256 verification."""
    try:
        if os.path.getsize(src_path) != os.path.getsize(target_path):
            return False
        with open(src_path, "rb") as f1, open(target_path, "rb") as f2:
            chunk1 = f1.read(65536)
            chunk2 = f2.read(65536)
            if chunk1 != chunk2:
                return False
            file_size = os.path.getsize(src_path)
            if file_size > 65536:
                f1.seek(-min(65536, file_size), os.SEEK_END)
                f2.seek(-min(65536, file_size), os.SEEK_END)
                if f1.read() != f2.read():
                    return False
        return file_sha256(src_path) == file_sha256(target_path)
    except Exception:
        return False


def find_identical_in_target(src_path, target_dir, stem, ext):
    """Find identical file among stem base and stem-suffixed candidates."""
    base_file = target_dir / f"{stem}{ext}"
    if base_file.exists() and is_identical_file(src_path, base_file):
        return base_file
    for candidate in target_dir.glob(f"{stem}-*{ext}"):
        if candidate.is_file() and is_identical_file(src_path, candidate):
            return candidate
    return None


def timestamp_parts(stem):
    """Parse only Kairos timestamp naming pattern."""
    match = TIMESTAMP_STEM_RE.fullmatch(stem)
    if not match:
        return None, None
    return match.group("base"), match.group("suffix")


def unique_path(directory, stem, ext):
    candidate = directory / f"{stem}{ext}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{ext}"
        counter += 1
    return candidate


def unique_indexed_path(directory, stem, ext, start=1):
    """Always add numeric suffix starting from `start` (e.g. -1, -2, ...)."""
    counter = max(int(start), 1)
    candidate = directory / f"{stem}-{counter}{ext}"
    while candidate.exists():
        counter += 1
        candidate = directory / f"{stem}-{counter}{ext}"
    return candidate


def candidate_path_for(month_dir, stem, ext):
    candidate_dir = month_dir / "candidate"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    return unique_indexed_path(candidate_dir, stem, ext, start=1)
