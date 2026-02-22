from __future__ import annotations

import logging
from datetime import datetime

from app.clients.b_engine_client import BEngineClient
from app.clients.tmdb_client import TMDBClient
from app.config import Settings
from app.services.overview_enricher import OverviewEnricher
from app.services.prompt_builder import build_prompt_variables
from app.services.store import CandidateItem, Store

STYLE_RECIPES: list[dict[str, str]] = [
    {
        "name": "Q_HOOK",
        "intro_style": "질문형 도입으로 공감 포인트를 먼저 던진다",
        "section_flow": "도입 갈등 -> 인물 선택 -> 분위기 전환 -> 개인 감상",
        "ending_style": "짧은 여운 + 취향 추천형 마무리",
        "emoji_pool": "👀,🔥,😮‍💨",
    },
    {
        "name": "CONFESS_HOOK",
        "intro_style": "개인 경험 고백형 도입으로 친밀하게 시작한다",
        "section_flow": "보는 계기 -> 초반 몰입 구간 -> 중반 긴장 포인트 -> 한줄 총평",
        "ending_style": "솔직한 호불호 + 다음 작품 암시",
        "emoji_pool": "🫠,🥹,✨",
    },
    {
        "name": "SCENE_HOOK",
        "intro_style": "한 장면 묘사로 시작해 궁금증을 만든다",
        "section_flow": "장면 티저 -> 시간순 줄거리 정리 -> 포인트 해설 -> 추천 대상",
        "ending_style": "짧은 질문형 엔딩",
        "emoji_pool": "🎬,💥,🤭",
    },
    {
        "name": "COMPARE_HOOK",
        "intro_style": "비슷한 작품과 비교하면서 진입한다",
        "section_flow": "비교 기준 -> 차별점 -> 캐릭터/연출 포인트 -> 시청 팁",
        "ending_style": "취향 분기형 마무리",
        "emoji_pool": "🧠,👀,🫶",
    },
    {
        "name": "ONE_LINE_HOOK",
        "intro_style": "강한 한줄평으로 시작하고 바로 이유를 푼다",
        "section_flow": "한줄평 근거 -> 줄거리 핵심 흐름 -> 감정선 포인트 -> 결론",
        "ending_style": "간결한 재시청 의향 코멘트",
        "emoji_pool": "😵‍💫,😭,🔥",
    },
]

REPETITIVE_PHRASES: list[str] = [
    "안녕하세요 오늘은",
    "추천드립니다",
    "정리해봤어요",
    "끝까지 읽어주세요",
    "개인적으로 좋았습니다",
    "호불호가 갈릴 수 있습니다",
]


class OTTGenEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tmdb = TMDBClient(settings)
        self.b_engine = BEngineClient(settings)
        self.store = Store(settings.sqlite_path)
        self.overview_enricher = OverviewEnricher(settings)
        self.logger = logging.getLogger("ott_gen.engine")

    def parse_sources(self) -> dict[str, int]:
        candidates, parse_meta = self._collect_parse_candidates()
        self.logger.info("parse started | count=%s meta=%s", len(candidates), parse_meta)

        queued = 0
        skipped_provider = 0
        skipped_images = 0
        skipped_dup = 0

        seen_keys: set[tuple[int, str]] = set()
        for item in candidates:
            tmdb_id = int(item["id"])
            media_type = item.get("_media_type", "movie")
            source = item.get("_source", "unknown")
            dedup_key = (tmdb_id, media_type)
            if dedup_key in seen_keys:
                skipped_dup += 1
                continue
            seen_keys.add(dedup_key)

            providers = self._provider_names(media_type, tmdb_id)
            if not providers:
                skipped_provider += 1
                continue

            details = self.tmdb.fetch_details(media_type, tmdb_id)
            payload_images, poster_url, still_urls = self._build_images(media_type, tmdb_id, details)
            if len(still_urls) < self.settings.min_stills:
                skipped_images += 1
                continue

            pv = build_prompt_variables(details)
            original_overview = (pv.get("overview") or "").strip()
            enriched_overview = ""
            pv["overview"] = original_overview

            changed = self.store.upsert_candidate(
                tmdb_id=tmdb_id,
                media_type=media_type,
                source=source,
                title=pv["title"],
                overview=pv["overview"],
                original_overview=original_overview,
                enriched_overview=enriched_overview,
                rating=pv["rating"],
                genres=pv["genres"],
                year=pv["year"],
                provider_names=", ".join(providers),
                poster_url=poster_url,
                still_urls=still_urls,
                dedup_days=self.settings.dedup_days,
            )
            if changed:
                queued += 1
            else:
                skipped_dup += 1

        result = {
            "queued": queued,
            "skipped_provider": skipped_provider,
            "skipped_images": skipped_images,
            "skipped_duplicate": skipped_dup,
            "latest_included": int(parse_meta.get("latest_included", 0)),
            "latest_pages": int(parse_meta.get("latest_pages", 0)),
            "backfill_pages": int(parse_meta.get("backfill_pages", 0)),
        }
        self.logger.info("parse finished | %s", result)
        return result

    def _collect_parse_candidates(self) -> tuple[list[dict], dict[str, int]]:
        media_types = ["movie", "tv"]
        candidates: list[dict] = []
        latest_included = 0
        latest_pages = 0
        backfill_pages = 0

        today_ymd = datetime.utcnow().strftime("%Y-%m-%d")
        last_latest_ymd = self.store.get_state("latest_parse_ymd", "")
        include_latest = last_latest_ymd != today_ymd

        if include_latest:
            for media_type in media_types:
                for page in range(1, max(1, self.settings.latest_daily_pages) + 1):
                    items, _ = self.tmdb.fetch_discover_page(
                        media_type,
                        page=page,
                        sort_by=self.tmdb.latest_sort_by_for(media_type),
                        source=f"latest_daily_p{page}",
                        per_page_limit=self.settings.per_page_limit,
                    )
                    candidates.extend(items)
                    latest_pages += 1
            self.store.set_state("latest_parse_ymd", today_ymd)
            latest_included = 1

        for media_type in media_types:
            page_key = f"backfill_page_{media_type}"
            cursor_page = max(1, self.store.get_state_int(page_key, 1))
            for _ in range(max(1, self.settings.backfill_pages_per_run)):
                items, total_pages = self.tmdb.fetch_discover_page(
                    media_type,
                    page=cursor_page,
                    sort_by=self.settings.backfill_sort_by,
                    source=f"backfill_p{cursor_page}",
                    per_page_limit=self.settings.per_page_limit,
                )
                candidates.extend(items)
                backfill_pages += 1
                cursor_page = cursor_page + 1
                if cursor_page > total_pages:
                    cursor_page = 1
            self.store.set_state(page_key, str(cursor_page))

        meta = {
            "latest_included": latest_included,
            "latest_pages": latest_pages,
            "backfill_pages": backfill_pages,
        }
        return candidates, meta

    def generate_daily_batch(self) -> dict[str, int]:
        used = self.store.today_generated_count()
        remaining = max(0, self.settings.daily_generate_limit - used)
        if remaining == 0:
            return {"today_used": used, "generated": 0, "failed": 0, "remaining": 0}

        target_count = min(remaining, self.settings.effective_submit_per_run_limit)
        queued = self.store.get_next_queued(target_count, min_overview_length=self.settings.scheduler_min_overview_length)
        generated = 0
        failed = 0

        for item in queued:
            try:
                if not self.store.acquire_generation_lock(item.id):
                    self.logger.info("skip generate(lock failed) | candidate_id=%s", item.id)
                    continue
                item = self.store.get_candidate(item.id) or item
                if self.settings.scheduler_enrich_overview:
                    item = self._enrich_for_manual_generate(item, force=True)
                payload = self._candidate_to_payload(item)
                res = self.b_engine.generate_post(payload)
                returned_status = str(res.get("status", "") or "").strip().lower()
                if returned_status in {"queued", "draft", "processing"}:
                    self.store.mark_submitted(item.id, int(res.get("post_id", 0) or 0))
                else:
                    self.store.mark_generated(item.id, int(res.get("post_id", 0) or 0))
                self.store.increment_today_generated(1)
                generated += 1
                self.logger.info(
                    "submitted | candidate_id=%s tmdb_id=%s b_post_id=%s status=%s",
                    item.id,
                    item.tmdb_id,
                    res.get("post_id"),
                    returned_status or "-",
                )
            except Exception as exc:
                failed += 1
                self.store.mark_failed(item.id, str(exc))
                self.logger.error("generate failed | candidate_id=%s error=%s", item.id, exc)

        used_after = self.store.today_generated_count()
        return {
            "today_used": used_after,
            "generated": generated,
            "failed": failed,
            "remaining": max(0, self.settings.daily_generate_limit - used_after),
        }

    def generate_one(self, candidate_id: int) -> dict[str, int | str]:
        item = self.store.get_candidate(candidate_id)
        if not item:
            raise ValueError("Candidate not found")
        if item.status != "queued":
            raise ValueError(f"Cannot generate from status={item.status}. Reset flag first.")
        if not self.store.acquire_generation_lock(item.id):
            raise ValueError("Candidate is not available for generation.")
        item = self.store.get_candidate(item.id) or item
        try:
            item = self._enrich_for_manual_generate(item, force=False)
            payload = self._candidate_to_payload(item)
            res = self.b_engine.generate_post(payload)
            returned_status = str(res.get("status", "") or "").strip().lower()
            if returned_status in {"queued", "draft", "processing"}:
                self.store.mark_submitted(item.id, int(res.get("post_id", 0) or 0))
            else:
                self.store.mark_generated(item.id, int(res.get("post_id", 0) or 0))
            self.store.increment_today_generated(1)
            return {
                "candidate_id": item.id,
                "post_id": int(res.get("post_id", 0) or 0),
                "status": str(res.get("status", "")),
            }
        except Exception as exc:
            self.store.mark_failed(item.id, str(exc))
            raise

    def reset_generated_flag(self, candidate_id: int) -> dict[str, int]:
        ok = self.store.reset_to_queued(candidate_id)
        if not ok:
            raise ValueError("Candidate not found")
        return {"candidate_id": candidate_id, "reset": 1}

    def delete_candidate(self, candidate_id: int) -> dict[str, int]:
        ok = self.store.delete_candidate(candidate_id)
        if not ok:
            raise ValueError("Candidate not found")
        return {"candidate_id": candidate_id, "deleted": 1}

    def enrich_one(self, candidate_id: int) -> dict[str, int | str]:
        item = self.store.get_candidate(candidate_id)
        if not item:
            raise ValueError("Candidate not found")
        base_overview = (item.original_overview or item.overview or "").strip()
        result = self.overview_enricher.enrich_with_meta(
            title=item.title,
            year=item.year,
            current_overview=base_overview,
            genres=item.genres,
            media_type=item.media_type,
            force_web_search=True,
            force_ai=True,
        )
        enriched = str(result.get("text") or "").strip()
        if enriched and enriched != base_overview:
            self.store.update_overview_texts(
                item.id,
                overview=enriched,
                original_overview=base_overview,
                enriched_overview=enriched,
            )
            self.logger.info("overview enriched(manual) | candidate_id=%s tmdb_id=%s", item.id, item.tmdb_id)
        updated = self.store.get_candidate(item.id) or item
        changed = 1 if (updated.enriched_overview or "").strip() else 0
        return {
            "candidate_id": updated.id,
            "enriched": changed,
            "overview_length": len((updated.overview or "").strip()),
            "snippet_count": int(result.get("snippet_count", 0) or 0),
            "ai_used": 1 if bool(result.get("ai_used")) else 0,
            "reason": str(result.get("reason") or ""),
        }

    def _enrich_for_manual_generate(self, item: CandidateItem, force: bool = False) -> CandidateItem:
        if not self.settings.enrich_overview:
            return item
        base_overview = (item.original_overview or item.overview or "").strip()
        if (not force) and len(base_overview) >= self.settings.overview_min_length:
            return item

        enriched = self.overview_enricher.enrich(
            title=item.title,
            year=item.year,
            current_overview=base_overview,
            genres=item.genres,
            media_type=item.media_type,
        )
        if not enriched or enriched == base_overview:
            return item

        self.store.update_overview_texts(
            item.id,
            overview=enriched,
            original_overview=base_overview,
            enriched_overview=enriched,
        )
        self.logger.info("overview enriched | candidate_id=%s tmdb_id=%s", item.id, item.tmdb_id)
        updated = self.store.get_candidate(item.id)
        return updated or item

    def _provider_names(self, media_type: str, tmdb_id: int) -> list[str]:
        data = self.tmdb.fetch_watch_providers(media_type, tmdb_id)
        kr = (data.get("results") or {}).get(self.settings.tmdb_region, {})
        providers = kr.get("flatrate") or []
        names = [str(p.get("provider_name", "")).strip() for p in providers if p.get("provider_name")]
        name_lc = {x.lower() for x in names}
        if not any(tp in name_lc for tp in self.settings.target_provider_set):
            return []
        return names

    def _build_images(self, media_type: str, tmdb_id: int, details: dict) -> tuple[list[dict], str, list[str]]:
        base = self.settings.tmdb_image_base_url.rstrip("/")
        images: list[dict] = []
        poster_url = ""
        still_urls: list[str] = []
        seen: set[str] = set()

        poster_path = details.get("poster_path")
        if poster_path:
            poster_url = f"{base}{poster_path}"
            if poster_url not in seen:
                images.append({"url": poster_url, "type": "poster"})
                seen.add(poster_url)

        image_data = self.tmdb.fetch_images(media_type, tmdb_id)
        for b in image_data.get("backdrops", []):
            fp = b.get("file_path")
            if not fp:
                continue
            still_url = f"{base}{fp}"
            if still_url in seen:
                continue
            still_urls.append(still_url)
            images.append({"url": still_url, "type": "still"})
            seen.add(still_url)
            if len(still_urls) >= self.settings.max_stills:
                break

        return images, poster_url, still_urls

    def _candidate_to_payload(self, item: CandidateItem) -> dict:
        style = self._next_style_recipe()
        repetition_guard = self._build_repetition_guard()
        images = []
        if item.poster_url:
            images.append({"url": item.poster_url, "type": "poster"})
        for u in item.still_urls:
            images.append({"url": u, "type": "still"})

        original_overview = (item.original_overview or "").strip()
        enriched_overview = (item.enriched_overview or "").strip()
        overview_context = (
            f"[원본 줄거리]\n{original_overview or '(없음)'}\n\n"
            f"[보강 줄거리]\n{enriched_overview or '(없음)'}"
        )
        prompt_template = self._compose_prompt_template(self.settings.prompt_template)

        self.logger.info(
            "generate prompt style | candidate_id=%s tmdb_id=%s style=%s",
            item.id,
            item.tmdb_id,
            style["name"],
        )
        return {
            "content_type": "ott",
            "prompt_template": prompt_template,
            "prompt_variables": {
                "title": item.title,
                "overview": item.overview,
                "original_overview": original_overview,
                "enriched_overview": enriched_overview,
                "overview_context": overview_context,
                "rating": item.rating,
                "genres": item.genres,
                "year": item.year,
                "style_recipe_name": style["name"],
                "style_intro": style["intro_style"],
                "style_flow": style["section_flow"],
                "style_ending": style["ending_style"],
                "emoji_pool": style["emoji_pool"],
                "avoid_phrases": repetition_guard["avoid_phrases"],
                "recent_titles": repetition_guard["recent_titles"],
                "writing_direction": repetition_guard["writing_direction"],
            },
            "images": images,
            "render_template": self.settings.b_engine_render_template,
            "auto_publish": self.settings.b_engine_auto_publish,
            "system_role": self.settings.b_engine_system_role,
        }

    def _next_style_recipe(self) -> dict[str, str]:
        cursor = self.store.get_state_int("style_recipe_cursor", 0)
        recipe = STYLE_RECIPES[cursor % len(STYLE_RECIPES)]
        self.store.set_state("style_recipe_cursor", str(cursor + 1))
        return recipe

    def _build_repetition_guard(self) -> dict[str, str]:
        recent = self.store.list_recent_generated(limit=12)
        recent_titles = [x.title.strip() for x in recent if x.title.strip()][:8]
        avoid_phrases = list(REPETITIVE_PHRASES)
        writing_direction = (
            "이전 글과 도입 문장 구조를 다르게 시작하고, 섹션 제목 톤을 바꿔라. "
            "같은 접속어 반복(예: 그리고/또한/한편으로)을 줄이고 문장 길이를 섞어라."
        )
        return {
            "avoid_phrases": ", ".join(avoid_phrases),
            "recent_titles": ", ".join(recent_titles) if recent_titles else "(최근 생성 이력 없음)",
            "writing_direction": writing_direction,
        }

    @staticmethod
    def _compose_prompt_template(base_template: str) -> str:
        runtime_guard = (
            "\n[이번 글 레퍼토리 가이드]\n"
            "- 스타일 코드: {style_recipe_name}\n"
            "- 도입 방식: {style_intro}\n"
            "- 섹션 전개: {style_flow}\n"
            "- 마무리 톤: {style_ending}\n"
            "- 이모지 후보: {emoji_pool}\n"
            "- 최근 생성 작품(톤/구성 반복 금지): {recent_titles}\n"
            "- 금지 문구: {avoid_phrases}\n"
            "- 추가 지시: {writing_direction}\n"
        )
        if "{style_recipe_name}" in base_template:
            return base_template
        return f"{base_template.rstrip()}\n{runtime_guard}"
