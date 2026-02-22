from __future__ import annotations

import random
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

    def fetch_candidates(self, run_mode: str, pages: int = 2, per_page_limit: int = 10) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        media_types = ["movie", "tv"]
        pages = max(1, pages)
        for media_type in media_types:
            include_trending = run_mode in {"trending", "hybrid"}
            include_latest = run_mode in {"latest", "hybrid"}
            for page in range(1, pages + 1):
                if include_trending:
                    data = self._get(f"/trending/{media_type}/week", page=page)
                    for item in data.get("results", [])[:per_page_limit]:
                        item["_media_type"] = media_type
                        item["_source"] = "trending"
                        candidates.append(item)
                if include_latest:
                    data = self._get(
                        f"/discover/{media_type}",
                        sort_by="release_date.desc" if media_type == "movie" else "first_air_date.desc",
                        region=self.settings.tmdb_region,
                        page=page,
                    )
                    for item in data.get("results", [])[:per_page_limit]:
                        item["_media_type"] = media_type
                        item["_source"] = "latest"
                        candidates.append(item)

        random.shuffle(candidates)
        return candidates

    def fetch_details(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/{media_type}/{tmdb_id}")

    def fetch_watch_providers(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/{media_type}/{tmdb_id}/watch/providers")

    def fetch_images(self, media_type: str, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/{media_type}/{tmdb_id}/images", include_image_language="ko,en,null")
