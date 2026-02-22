from __future__ import annotations

from typing import Any

import requests

from app.config import Settings


class TMDBClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = "https://api.themoviedb.org/3"
        self.session = requests.Session()
        self.session.params = {"api_key": settings.tmdb_api_key, "language": settings.tmdb_language}

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def fetch_discover_page(
        self,
        media_type: str,
        *,
        page: int,
        sort_by: str,
        source: str,
        per_page_limit: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        data = self._get(
            f"/discover/{media_type}",
            sort_by=sort_by,
            region=self.settings.tmdb_region,
            page=max(1, page),
        )
        out: list[dict[str, Any]] = []
        for item in data.get("results", [])[:per_page_limit]:
            item["_media_type"] = media_type
            item["_source"] = source
            out.append(item)
        total_pages = int(data.get("total_pages", 1) or 1)
        return out, max(1, total_pages)

    @staticmethod
    def latest_sort_by_for(media_type: str) -> str:
        return "release_date.desc" if media_type == "movie" else "first_air_date.desc"

    def fetch_details(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/{media_type}/{tmdb_id}")

    def fetch_watch_providers(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/{media_type}/{tmdb_id}/watch/providers")

    def fetch_images(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/{media_type}/{tmdb_id}/images", include_image_language="ko,en,null")
