from __future__ import annotations

import re
from typing import Any

from slugify import slugify


class SeoEngine:
    MIN_META = 120
    MAX_META = 160

    @staticmethod
    def optimize(content: dict[str, Any]) -> dict[str, Any]:
        title = (content.get("title") or "").strip()
        sections = content.get("sections", [])
        tags = content.get("tags", [])
        raw_meta = (content.get("meta_description") or "").strip()

        keywords = SeoEngine._extract_keywords(title, sections)
        merged_tags = SeoEngine._normalize_tags(tags + keywords)
        slug = slugify(title)[:120] if title else "generated-post"

        source_text = raw_meta or SeoEngine._first_summary(sections) or title
        meta_description = SeoEngine._fit_meta_length(source_text)

        return {
            "seo_title": title,
            "slug": slug,
            "tags": merged_tags,
            "meta_description": meta_description,
        }

    @staticmethod
    def _extract_keywords(title: str, sections: list[dict[str, Any]]) -> list[str]:
        words = re.findall(r"[\w가-힣]{2,}", title)
        if not words and sections:
            words = re.findall(r"[\w가-힣]{2,}", sections[0].get("heading", ""))
        return words[:8]

    @staticmethod
    def _normalize_tags(tags: list[Any]) -> list[str]:
        result: list[str] = []
        for tag in tags:
            if not isinstance(tag, str):
                continue
            norm = tag.strip().lower()
            if not norm or norm in result:
                continue
            result.append(norm)
            if len(result) == 15:
                break
        return result

    @staticmethod
    def _first_summary(sections: list[dict[str, Any]]) -> str:
        for section in sections:
            text = (section.get("content") or "").strip()
            if text:
                return text
        return ""

    @classmethod
    def _fit_meta_length(cls, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > cls.MAX_META:
            return text[: cls.MAX_META - 1].rstrip() + "…"
        if len(text) < cls.MIN_META:
            filler = " 리뷰 핵심을 빠르게 확인하고 시청 여부를 결정할 수 있도록 정리했습니다."
            text = (text + filler).strip()
            if len(text) > cls.MAX_META:
                text = text[: cls.MAX_META - 1].rstrip() + "…"
        return text
