# services/thumbnail_service.py
from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Tuple

from PIL import Image, ImageOps

from app.ports.thumbnail import ThumbnailService


class PillowThumbnailService(ThumbnailService):
    """
    Local thumbnail generator that down‑sizes the longest edge to *size*
    (default 300 px) and encodes as JPEG.

    Running the Pillow work inside `run_in_executor()` keeps your async
    event‑loop unblocked.
    """

    def __init__(self, size: Tuple[int, int] = (800, 800), fmt: str = "JPEG"):
        self.size = size
        self.fmt = fmt

    # public async API -------------------------------------------------------
    async def generate_thumbnail(self, src_path: str) -> bytes:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_make_thumb, src_path)

    # -----------------------------------------------------------------------
    def _sync_make_thumb(self, src_path: str) -> bytes:
        with Image.open(src_path) as img:
            img = ImageOps.exif_transpose(img)

            img.thumbnail(self.size)

            # Ensure JPEG-compatible mode
            if self.fmt.upper() == "JPEG" and img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            buf = BytesIO()
            img.save(buf, self.fmt, quality=85)
            return buf.getvalue()
