# =============================================================================
# Post cover image — validation, size limits, safe storage filename
# =============================================================================
# Stored value on Post.image_filename is a single basename only (no path
# segments). Files live under static/uploads/posts/ at runtime.
# =============================================================================
from __future__ import annotations

import os
import secrets
from typing import BinaryIO

DEFAULT_MAX_BYTES = 2 * 1024 * 1024  # 2 MiB


def sniff_image_extension(header: bytes) -> str | None:
    """Return normalised extension from magic bytes, or None if unsupported."""
    if not header:
        return None
    if header[:3] == b"\xff\xd8\xff":
        return "jpg"
    if len(header) >= 8 and header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(header) >= 6 and header[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    # WebP: RIFF....WEBP
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def _read_all_limited(stream: BinaryIO, max_bytes: int) -> tuple[bytes | None, str | None]:
    """Read entire stream with a hard cap (inclusive). Returns (data, error)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        buf = stream.read(65536)
        if not buf:
            break
        total += len(buf)
        if total > max_bytes:
            return None, (
                f"Cover image is too large (maximum {max_bytes // (1024 * 1024)} MB)."
            )
        chunks.append(buf)
    return b"".join(chunks), None


def save_post_cover_image(
    stream: BinaryIO,
    *,
    upload_dir: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> tuple[str | None, str | None]:
    """
    Validate bytes as a supported raster image and write to ``upload_dir``.

    Returns ``(saved_basename, None)`` on success, or ``(None, human_message)``.
    The basename is ``<32 hex>.<ext>`` with no directory components.
    """
    os.makedirs(upload_dir, exist_ok=True)

    data, err = _read_all_limited(stream, max_bytes)
    if err or data is None:
        return None, err or "Could not read upload."

    if not data:
        return None, "Empty file."

    ext = sniff_image_extension(data[:64])
    if ext is None:
        return (
            None,
            "Unsupported image type. Use JPEG, PNG, GIF, or WebP.",
        )

    basename = f"{secrets.token_hex(16)}.{ext}"
    path = os.path.join(upload_dir, basename)
    try:
        with open(path, "wb") as fh:
            fh.write(data)
    except OSError as exc:
        return None, f"Could not save image ({exc!r})."

    return basename, None


__all__ = [
    "DEFAULT_MAX_BYTES",
    "save_post_cover_image",
    "sniff_image_extension",
]
