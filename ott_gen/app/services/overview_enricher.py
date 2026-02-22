from __future__ import annotations

import re
from typing import Any

from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from openai import OpenAI

from app.config import Settings


class OverviewEnricher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        openai_api_key = settings.effective_enrich_openai_api_key
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key and settings.enrich_ai_summary else None

        tavily_api_key = settings.effective_enrich_tavily_api_key
        self.tavily = TavilySearchAPIWrapper(tavily_api_key=tavily_api_key) if tavily_api_key else None

    def enrich(
        self,
        title: str,
        year: str,
        current_overview: str,
        genres: str = "",
        media_type: str = "",
    ) -> str:
        result = self.enrich_with_meta(
            title=title,
            year=year,
            current_overview=current_overview,
            genres=genres,
            media_type=media_type,
            force_web_search=False,
            force_ai=False,
        )
        return str(result.get("text") or "")

    def enrich_with_meta(
        self,
        title: str,
        year: str,
        current_overview: str,
        genres: str = "",
        media_type: str = "",
        force_web_search: bool = False,
        force_ai: bool = False,
    ) -> dict[str, Any]:
        current = self._normalize((current_overview or "").strip())
        media_hint = "드라마" if media_type == "tv" else "영화"
        genre_hint = genres.replace(",", " ").strip()
        query = f"{title} {year} {media_hint} 줄거리 {genre_hint}".strip()

        snippets = self._search_snippets(query, max_results=self.settings.enrich_search_max_snippets)
        if not snippets:
            reason = "tavily_no_results"
            if force_web_search and not self.tavily:
                reason = "tavily_key_missing"
            return {
                "text": "",
                "snippet_count": 0,
                "ai_used": False,
                "reason": reason,
            }

        merged = "\n".join(f"- {s}" for s in snippets[:10])
        ai_used = False
        if self.client:
            ai_used = True
            summarized = self._summarize_with_ai(title=title, year=year, current=current, source_text=merged)
            if summarized:
                return {
                    "text": summarized,
                    "snippet_count": len(snippets),
                    "ai_used": ai_used,
                    "reason": "ai_summary",
                }
        elif force_ai:
            return {
                "text": "",
                "snippet_count": len(snippets),
                "ai_used": False,
                "reason": "ai_key_missing",
            }

        fallback = self._normalize(" ".join(snippets)[:800])
        if fallback and fallback != current:
            return {
                "text": fallback,
                "snippet_count": len(snippets),
                "ai_used": ai_used,
                "reason": "fallback_merged",
            }
        return {
            "text": current,
            "snippet_count": len(snippets),
            "ai_used": ai_used,
            "reason": "same_as_current",
        }

    def _search_snippets(self, query: str, max_results: int) -> list[str]:
        if not self.tavily:
            return []
        try:
            results = self.tavily.results(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_raw_content=False,
            )
            snippets: list[str] = []
            seen: set[str] = set()
            for item in results:
                text = self._normalize(
                    " ".join(
                        [
                            str(item.get("title", "")).strip(),
                            str(item.get("content", "")).strip(),
                            str(item.get("raw_content", "")).strip(),
                        ]
                    )
                )
                if not text or text in seen:
                    continue
                snippets.append(text)
                seen.add(text)
                if len(snippets) >= max_results:
                    break
            return snippets
        except Exception:
            return []

    def _summarize_with_ai(self, title: str, year: str, current: str, source_text: str) -> str:
        if not self.client:
            return ""
        try:
            response = self.client.chat.completions.create(
                model=self.settings.enrich_openai_model,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "너는 작품 줄거리 정리기다. 블로그 글감으로 사용할 수 있게 상세 줄거리를 작성한다. "
                            "항목 나열이 아닌 자연스러운 문단형으로 작성하고, 사건 전개는 반드시 시간 순서를 유지한다. "
                            "핵심 사건, 인물 선택, 갈등 변화를 빠짐없이 담되 사실 기반으로만 작성한다. "
                            "과장, 추측, 홍보 문구를 금지한다."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"작품명: {title}\n연도: {year}\n"
                            f"현재 줄거리: {current or '(없음)'}\n\n"
                            f"웹 검색 결과:\n{source_text}\n\n"
                            "출력 형식:\n"
                            "1) 줄거리 본문만 출력\n"
                            "2) 4~7개 문단\n"
                            "3) 문단당 2~4문장\n"
                            "4) 처음-중반-후반 흐름이 보이게 작성"
                        ),
                    },
                ],
            )
            text = self._normalize(response.choices[0].message.content or "")
            if text and text != current:
                return text
            return ""
        except Exception:
            return ""

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
