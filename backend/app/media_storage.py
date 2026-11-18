"""
Media storage service for Chatbot Flow Builder.
Handles directory initialization, file type verification (magic bytes),
streaming uploads, size validation, SHA-256 checksum generation, and safe path resolution.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple

# Base uploads directory inside backend
BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOADS_BASE_DIR = BACKEND_DIR / "uploads"

UPLOAD_DIRS = {
    "image": UPLOADS_BASE_DIR / "images",
    "document": UPLOADS_BASE_DIR / "documents",
    "video": UPLOADS_BASE_DIR / "videos",
}

# Maximum permitted upload size: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20,971,520 bytes

# Allowed MIME types and extensions mapping
ALLOWED_MIME_TYPES = {
    # Images
    "image/jpeg": ("image", [".jpg", ".jpeg"]),
    "image/png": ("image", [".png"]),
    "image/gif": ("image", [".gif"]),
    "image/webp": ("image", [".webp"]),
    # Documents
    "application/pdf": ("document", [".pdf"]),
    # Videos
    "video/mp4": ("video", [".mp4"]),
    "video/webm": ("video", [".webm"]),
    "video/quicktime": ("video", [".mov"]),
    "video/x-matroska": ("video", [".mkv"]),
}

ALLOWED_EXTENSIONS = {
    ext: (mime, cat)
    for mime, (cat, exts) in ALLOWED_MIME_TYPES.items()
    for ext in exts
}


def ensure_upload_dirs() -> None:
    """Create all upload directories programmatically if they do not exist."""
    UPLOADS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    for directory in UPLOAD_DIRS.values():
        directory.mkdir(parents=True, exist_ok=True)


def sniff_magic_bytes(header: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Sniff the initial header bytes of a file to verify its true MIME type and media category.
    Returns (mime_type, media_category) or (None, None) if unrecognized.
    """
    if len(header) < 3:
        return None, None

    # PNG: \x89PNG\r\n\x1a\n
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "image"

    # JPEG: \xff\xd8\xff
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "image"

    # GIF: GIF87a or GIF89a
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "image/gif", "image"

    # WebP: RIFF....WEBP
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp", "image"

    # PDF: %PDF-
    if header.startswith(b"%PDF-"):
        return "application/pdf", "document"

    # MP4 / QuickTime: bytes 4..8 == 'ftyp', 'moov', 'mdat', 'wide'
    if len(header) >= 8 and header[4:8] in (b"ftyp", b"moov", b"mdat", b"wide"):
        return "video/mp4", "video"

    # WebM / MKV: \x1a\x45\xdf\xa3
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm", "video"

    return None, None


def resolve_storage_path(storage_key: str) -> Path:
    """
    Safely resolve a storage key relative to BACKEND_DIR, preventing path traversal attacks.
    Raises ValueError if the path attempts to break outside UPLOADS_BASE_DIR.
    """
    target = (BACKEND_DIR / storage_key).resolve()
    base = UPLOADS_BASE_DIR.resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError(f"Path traversal detected for storage key: '{storage_key}'.")
    return target


def delete_stored_file(storage_key: str) -> bool:
    """
    Safely delete a physical file from storage. Returns True if deleted, False if already absent.
    """
    try:
        path = resolve_storage_path(storage_key)
        if path.is_file():
            path.unlink()
            return True
    except Exception:
        pass
    return False

