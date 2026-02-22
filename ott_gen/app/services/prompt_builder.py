from __future__ import annotations

from typing import Any


def build_prompt_variables(details: dict[str, Any]) -> dict[str, str]:
    title = details.get("title") or details.get("name") or ""
    overview = details.get("overview") or ""
    rating = str(details.get("vote_average") or "")
    genres = ", ".join(g.get("name", "") for g in details.get("genres", []) if g.get("name"))
    date_value = details.get("release_date") or details.get("first_air_date") or ""
    year = date_value[:4] if date_value else ""
    return {
        "title": title,
        "overview": overview,
        "rating": rating,
        "genres": genres,
        "year": year,
    }
