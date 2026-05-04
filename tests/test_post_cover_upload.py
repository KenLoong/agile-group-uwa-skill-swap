# =============================================================================
# Tests — post cover upload validation (magic bytes, size, filename handling)
# =============================================================================
from __future__ import annotations

import io
import os
import re
import tempfile
import unittest

from api.post_cover_upload import DEFAULT_MAX_BYTES, save_post_cover_image, sniff_image_extension

# Minimal valid PNG (1×1 transparent)
_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500001d0a2db40000000049454e44ae426082"
)


class TestPostCoverUpload(unittest.TestCase):
    def test_sniff_png_jpeg_webp(self) -> None:
        self.assertEqual(sniff_image_extension(_TINY_PNG[:64]), "png")
        self.assertEqual(sniff_image_extension(b"\xff\xd8\xff\x00" * 8), "jpg")
        webp = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 20
        self.assertEqual(sniff_image_extension(webp[:20]), "webp")

    def test_rejects_plain_text(self) -> None:
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        out, err = save_post_cover_image(
            io.BytesIO(b"not a real image"),
            upload_dir=tmp,
            max_bytes=1024,
        )
        self.assertIsNone(out)
        self.assertIsNotNone(err)
        self.assertIn("Unsupported", err or "")

    def test_saves_with_unpredictable_basename(self) -> None:
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        out, err = save_post_cover_image(
            io.BytesIO(_TINY_PNG),
            upload_dir=tmp,
            max_bytes=DEFAULT_MAX_BYTES,
        )
        self.assertIsNone(err)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertRegex(out, r"^[a-f0-9]{32}\.png$")
        full = os.path.join(tmp, out)
        self.assertTrue(os.path.isfile(full))
        with open(full, "rb") as fh:
            self.assertEqual(fh.read()[:8], _TINY_PNG[:8])


if __name__ == "__main__":
    unittest.main()
