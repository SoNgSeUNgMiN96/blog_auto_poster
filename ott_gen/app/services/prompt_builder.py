from __future__ import annotations

from typing import Any


def _extract_runtime(details: dict[str, Any]) -> str:
    runtime = details.get("runtime")
    if isinstance(runtime, int) and runtime > 0:
        return f"{runtime}분"
    episode = details.get("episode_run_time")
    if isinstance(episode, list) and episode:
        first = episode[0]
        if isinstance(first, int) and first > 0:
            return f"회당 {first}분"
    return ""


def _extract_director(details: dict[str, Any]) -> str:
    credits = details.get("credits") or {}
    crew = credits.get("crew") or []
    if isinstance(crew, list):
        for c in crew:
            if str(c.get("job", "")).strip().lower() == "director":
                name = str(c.get("name", "")).strip()
                if name:
                    return name
    created_by = details.get("created_by") or []
    if isinstance(created_by, list) and created_by:
        name = str(created_by[0].get("name", "")).strip()
        if name:
            return name
    return ""


def _extract_cast(details: dict[str, Any], limit: int = 4) -> str:
    credits = details.get("credits") or {}
    cast = credits.get("cast") or []
    names: list[str] = []
    if isinstance(cast, list):
        for member in cast[: max(1, limit)]:
            name = str(member.get("name", "")).strip()
            if name:
                names.append(name)
    return ", ".join(names)


def build_prompt_variables(details: dict[str, Any]) -> dict[str, str]:
    title = details.get("title") or details.get("name") or ""
    overview = details.get("overview") or ""
    rating = str(details.get("vote_average") or "")
    genres = ", ".join(g.get("name", "") for g in details.get("genres", []) if g.get("name"))
    date_value = details.get("release_date") or details.get("first_air_date") or ""
    year = date_value[:4] if date_value else ""
    runtime = _extract_runtime(details)
    director = _extract_director(details)
    cast = _extract_cast(details)
    return {
        "title": title,
        "overview": overview,
        "rating": rating,
        "genres": genres,
        "year": year,
        "release_date": str(date_value or ""),
        "runtime": runtime,
        "director": director,
        "cast": cast,
    }
