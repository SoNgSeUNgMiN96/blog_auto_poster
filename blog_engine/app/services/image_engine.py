from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image as PILImage
from PIL import ImageOps

from app.config import Settings


class ImageEngine:
    def __init__(self, settings: Settings):
        self.settings = settings

    def download_and_convert(self, image_url: str, post_id: int, order: int) -> Path:
        year = datetime.utcnow().year
        base_dir = self.settings.media_root / str(year) / str(post_id)
        base_dir.mkdir(parents=True, exist_ok=True)

        ext = self._guess_extension(image_url)
        original_path = base_dir / f"{order:02d}_original{ext}"
        webp_path = base_dir / f"{order:02d}.webp"

        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        content = response.content

        if self.settings.image_keep_original:
            original_path.write_bytes(content)

        with PILImage.open(BytesIO(content)) as img:
            normalized = ImageOps.exif_transpose(img).convert("RGB")
            max_size = (
                max(320, int(self.settings.image_max_width)),
                max(320, int(self.settings.image_max_height)),
            )
            normalized.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            quality = min(95, max(55, int(self.settings.image_webp_quality)))
            normalized.save(webp_path, "WEBP", quality=quality, method=6)

        return webp_path

    @staticmethod
    def _guess_extension(url: str) -> str:
        path = urlparse(url).path.lower()
        if path.endswith(".png"):
            return ".png"
        if path.endswith(".webp"):
            return ".webp"
        return ".jpg"
