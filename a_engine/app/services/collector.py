from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from app.clients.b_engine_client import BEngineClient
from app.clients.tmdb_client import TMDBClient
from app.config import Settings
from app.services.dedup_store import DedupStore
from app.services.prompt_builder import build_prompt_variables


@dataclass
class RunResult:
    tried: int
    filtered_provider: int
    filtered_duplicate: int
    filtered_images: int
    published: int
    failed: int


class AEngineCollector:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tmdb = TMDBClient(settings)
        self.b_engine = BEngineClient(settings)
        self.store = DedupStore(settings.sqlite_path)
        self.logger = logging.getLogger("a_engine.collector")

    def run_once(self) -> RunResult:
        self.logger.info(
            "run started | mode=%s pages=%s collect_limit=%s providers=%s dedup_days=%s",
            self.settings.run_mode,
            self.settings.candidate_pages,
            self.settings.collect_limit,
            sorted(self.settings.target_provider_set),
            self.settings.dedup_days,
        )
        candidates = self.tmdb.fetch_candidates(
            self.settings.run_mode,
            pages=self.settings.candidate_pages,
        )
        self.logger.info("candidates fetched | count=%s", len(candidates))
        tried = 0
        filtered_provider = 0
        filtered_duplicate = 0
        filtered_images = 0
        published = 0
        failed = 0

        for item in candidates:
            if published >= self.settings.collect_limit:
                break

            tried += 1
            tmdb_id = int(item["id"])
            media_type = item.get("_media_type", "movie")
            title_hint = item.get("title") or item.get("name") or ""
            self.logger.info(
                "candidate checking | tmdb_id=%s media_type=%s source=%s title=%s",
                tmdb_id,
                media_type,
                item.get("_source", "unknown"),
                title_hint,
            )

            if self.store.is_recently_posted(tmdb_id, media_type, self.settings.dedup_days):
                filtered_duplicate += 1
                self.logger.info(
                    "candidate skipped (duplicate) | tmdb_id=%s media_type=%s",
                    tmdb_id,
                    media_type,
                )
                continue

            if not self._is_available_in_target_provider(media_type, tmdb_id):
                filtered_provider += 1
                self.logger.info(
                    "candidate skipped (provider) | tmdb_id=%s media_type=%s",
                    tmdb_id,
                    media_type,
                )
                continue

            details = self.tmdb.fetch_details(media_type, tmdb_id)
            images = self._build_images(media_type, tmdb_id, details)
            still_count = sum(1 for img in images if img.get("type") == "still")
            if still_count < self.settings.min_stills:
                filtered_images += 1
                self.logger.info(
                    "candidate skipped (images) | tmdb_id=%s media_type=%s still_count=%s min_stills=%s",
                    tmdb_id,
                    media_type,
                    still_count,
                    self.settings.min_stills,
                )
                continue
            payload = self._build_b_payload(details, images)
            self.logger.info(
                "candidate ready | tmdb_id=%s media_type=%s title=%s image_count=%s",
                tmdb_id,
                media_type,
                payload["prompt_variables"].get("title", ""),
                len(images),
            )

            try:
                result = self.b_engine.generate_post(payload)
                self.store.mark_posted(tmdb_id, media_type)
                published += 1
                self.logger.info(
                    "candidate published | tmdb_id=%s media_type=%s post_id=%s status=%s",
                    tmdb_id,
                    media_type,
                    result.get("post_id"),
                    result.get("status"),
                )
            except Exception as exc:
                failed += 1
                self.logger.error(
                    "candidate failed | tmdb_id=%s media_type=%s error=%s",
                    tmdb_id,
                    media_type,
                    exc,
                )
                continue

        result = RunResult(
            tried=tried,
            filtered_provider=filtered_provider,
            filtered_duplicate=filtered_duplicate,
            filtered_images=filtered_images,
            published=published,
            failed=failed,
        )
        self.logger.info("run finished | result=%s", result)
        return result

    def _is_available_in_target_provider(self, media_type: str, tmdb_id: int) -> bool:
        data = self.tmdb.fetch_watch_providers(media_type, tmdb_id)
        kr = (data.get("results") or {}).get(self.settings.tmdb_region, {})
        providers = kr.get("flatrate") or []
        names = {str(p.get("provider_name", "")).strip().lower() for p in providers}
        return any(target in names for target in self.settings.target_provider_set)

    def _build_images(self, media_type: str, tmdb_id: int, details: dict[str, Any]) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        base = self.settings.tmdb_image_base_url.rstrip("/")

        poster_path = details.get("poster_path")
        if poster_path:
            images.append({"url": f"{base}{poster_path}", "type": "poster"})

        image_data = self.tmdb.fetch_images(media_type, tmdb_id)
        backdrops = image_data.get("backdrops", [])
        still_count = 0
        for backdrop in backdrops:
            file_path = backdrop.get("file_path")
            if not file_path:
                continue
            images.append({"url": f"{base}{file_path}", "type": "still"})
            still_count += 1
            if still_count >= self.settings.max_stills:
                break

        return images

    def _build_b_payload(self, details: dict[str, Any], images: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "content_type": "ott",
            "prompt_template": self.settings.prompt_template,
            "prompt_variables": build_prompt_variables(details),
            "images": images,
            "render_template": self.settings.b_engine_render_template,
            "auto_publish": self.settings.b_engine_auto_publish,
            "system_role": self.settings.b_engine_system_role,
        }
