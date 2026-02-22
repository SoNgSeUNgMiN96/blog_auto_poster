from __future__ import annotations

import html
import math
from typing import Any
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings
from app.services.engine import OTTGenEngine

settings = get_settings()
engine = OTTGenEngine(settings)
app = FastAPI(title="OTT Gen Dashboard")


def _candidate_card(c: Any) -> str:
    status = (getattr(c, "status", "") or "").strip().lower()
    status_bg = {
        "queued": "#dbeafe",
        "generating": "#fef3c7",
        "submitted": "#ede9fe",
        "generated": "#dcfce7",
        "failed": "#fee2e2",
    }.get(status, "#e5e7eb")
    status_text = {
        "queued": "대기",
        "generating": "생성중",
        "submitted": "제출됨",
        "generated": "생성됨",
        "failed": "실패",
    }.get(status, status or "-")
    stills_html = "".join(
        f'<img src="{html.escape(u)}" style="width:150px;height:84px;object-fit:cover;border-radius:8px;margin-right:8px;" />'
        for u in (c.still_urls or [])[:4]
    )
    poster_html = (
        f'<img src="{html.escape(c.poster_url)}" style="width:120px;border-radius:10px;" />'
        if c.poster_url
        else ""
    )
    original_overview_html = html.escape((getattr(c, "original_overview", "") or "").strip())
    enriched_overview_html = html.escape((getattr(c, "enriched_overview", "") or "").strip())
    overview_block = f"<div style='margin-top:8px;white-space:pre-wrap;color:#222;'>{html.escape((c.overview or '')[:280])}</div>"
    if original_overview_html or enriched_overview_html:
        overview_block = f"""
          <div style='margin-top:10px;padding:10px;border-radius:10px;background:#f8fafc;border:1px solid #e5e7eb;'>
            <div style='font-size:12px;color:#6b7280;margin-bottom:4px;'>원본 줄거리(TMDB)</div>
            <div style='white-space:pre-wrap;color:#374151;'>{original_overview_html or '-'}</div>
            <div style='font-size:12px;color:#6b7280;margin:10px 0 4px;'>보강 줄거리(검색)</div>
            <div style='white-space:pre-wrap;color:#111827;'>{enriched_overview_html or '-'}</div>
          </div>
        """
    return f"""
    <div style='border:1px solid #ddd;border-radius:14px;padding:14px;margin:10px 0;background:#fff;'>
      <div style='display:flex;gap:14px;'>
        <div>{poster_html}</div>
        <div style='flex:1;'>
          <div style='display:flex;align-items:center;gap:8px;'>
            <div style='font-weight:700;font-size:1.05rem;'>[{html.escape(c.media_type.upper())}] {html.escape(c.title)}</div>
            <span style='font-size:12px;padding:3px 8px;border-radius:999px;background:{status_bg};color:#111;'>{status_text}</span>
          </div>
          <div style='color:#666;margin-top:6px;'>평점 {html.escape(c.rating)} | {html.escape(c.genres)} | {html.escape(c.year)}</div>
          <div style='color:#666;margin-top:4px;'>Provider: {html.escape(c.provider_names)}</div>
          {overview_block}
          <div style='margin-top:10px;display:flex;align-items:center;overflow-x:auto;'>{stills_html}</div>
          <div style='margin-top:10px;'>
            {"<form method='post' action='/admin/enrich/" + str(c.id) + "' style='display:inline;margin-right:6px;'><button style='border:none;background:#2563eb;color:#fff;padding:8px 12px;border-radius:8px;cursor:pointer;'>줄거리 보강</button></form><form method='post' action='/admin/generate/" + str(c.id) + "' style='display:inline;'><button style='border:none;background:#0f766e;color:#fff;padding:8px 12px;border-radius:8px;cursor:pointer;'>이 글감 생성</button></form>" if status == "queued" else ""}
            {"<form method='post' action='/admin/reset/" + str(c.id) + "' style='display:inline;' onsubmit=\"return confirm('실패 항목을 복구하여 대기열로 보낼까요?');\"><button style='border:none;background:#b45309;color:#fff;padding:8px 12px;border-radius:8px;cursor:pointer;'>실패 복구</button></form>" if status == "failed" else ""}
            {"<form method='post' action='/admin/reset/" + str(c.id) + "' style='display:inline;margin-right:6px;' onsubmit=\"return confirm('생성 플래그를 해제하고 다시 대기로 돌릴까요?');\"><button style='border:none;background:#b45309;color:#fff;padding:8px 12px;border-radius:8px;cursor:pointer;'>플래그 해제</button></form><form method='post' action='/admin/delete/" + str(c.id) + "' style='display:inline;' onsubmit=\"return confirm('이 항목을 삭제할까요?');\"><button style='border:none;background:#6b7280;color:#fff;padding:8px 12px;border-radius:8px;cursor:pointer;'>항목 삭제</button></form>" if status in {"generated", "generating", "submitted"} else ""}
          </div>
        </div>
      </div>
    </div>
    """


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    status: str = "queued",
    page: int = 1,
    page_size: int = 20,
    overview_filter: str = "all",
    msg: str = "",
) -> str:
    status = status if status in {"queued", "generating", "submitted", "generated", "failed"} else "queued"
    overview_filter = overview_filter if overview_filter in {"all", "long"} else "all"
    page = max(1, page)
    page_size = min(300, max(5, page_size))
    min_overview_length = settings.scheduler_min_overview_length if overview_filter == "long" else 0

    total = engine.store.count_candidates(status=status, min_overview_length=min_overview_length)
    total_pages = max(1, math.ceil(total / page_size))
    page = min(page, total_pages)
    offset = (page - 1) * page_size

    queued = engine.store.list_candidates(
        status=status,
        limit=page_size,
        offset=offset,
        min_overview_length=min_overview_length,
    )
    failed = engine.store.list_candidates("failed", limit=20)
    used = engine.store.today_generated_count()
    remaining = max(0, settings.daily_generate_limit - used)

    queued_html = "".join(_candidate_card(c) for c in queued) or "<p>큐에 글감이 없습니다.</p>"
    failed_html = "".join(
        (
            f"<li>#{c.id} {html.escape(c.title)} - {html.escape(c.error_message or '')} "
            f"<form method='post' action='/admin/reset/{c.id}' style='display:inline;margin-left:8px;'>"
            f"<button style='border:none;background:#b45309;color:#fff;padding:4px 8px;border-radius:6px;cursor:pointer;'>복구</button>"
            f"</form></li>"
        )
        for c in failed
    ) or "<li>실패 항목 없음</li>"

    prev_link = f"/?status={status}&overview_filter={overview_filter}&page={max(1, page-1)}&page_size={page_size}"
    next_link = f"/?status={status}&overview_filter={overview_filter}&page={min(total_pages, page+1)}&page_size={page_size}"
    queued_tab = f"/?status=queued&overview_filter={overview_filter}&page=1&page_size={page_size}"
    generating_tab = f"/?status=generating&overview_filter={overview_filter}&page=1&page_size={page_size}"
    submitted_tab = f"/?status=submitted&overview_filter={overview_filter}&page=1&page_size={page_size}"
    generated_tab = f"/?status=generated&overview_filter={overview_filter}&page=1&page_size={page_size}"
    failed_tab = f"/?status=failed&overview_filter={overview_filter}&page=1&page_size={page_size}"
    filter_all = f"/?status={status}&overview_filter=all&page=1&page_size={page_size}"
    filter_long = f"/?status={status}&overview_filter=long&page=1&page_size={page_size}"
    size_20 = f"/?status={status}&overview_filter={overview_filter}&page=1&page_size=20"
    size_50 = f"/?status={status}&overview_filter={overview_filter}&page=1&page_size=50"
    size_100 = f"/?status={status}&overview_filter={overview_filter}&page=1&page_size=100"
    size_200 = f"/?status={status}&overview_filter={overview_filter}&page=1&page_size=200"

    return f"""
    <html>
      <head>
        <meta charset='utf-8'/>
        <title>OTT Gen Dashboard</title>
      </head>
      <body style='max-width:1100px;margin:20px auto;padding:0 16px;background:#f6f7f9;font-family:Arial;'>
        <h1 style='margin-bottom:8px;'>OTT Gen Dashboard</h1>
        <p style='color:#555;'>오늘 생성 {used}/{settings.daily_generate_limit} (남은 수량 {remaining})</p>
        <p style='color:#0f766e;font-weight:600;'>{html.escape(msg)}</p>

        <div style='margin:12px 0;'>
          <form method='post' action='/admin/parse' style='display:inline;'>
            <button style='border:none;background:#1d4ed8;color:#fff;padding:9px 14px;border-radius:8px;cursor:pointer;'>소스 파싱 실행</button>
          </form>
          <form method='post' action='/admin/generate-batch' style='display:inline;margin-left:8px;'>
            <button style='border:none;background:#7c3aed;color:#fff;padding:9px 14px;border-radius:8px;cursor:pointer;'>오늘 남은 수량만 생성</button>
          </form>
        </div>

        <div style='display:flex;gap:8px;margin:10px 0 6px;'>
          <a href='{queued_tab}' style='padding:6px 10px;border-radius:8px;background:{'#e0f2fe' if status=='queued' else '#eef2f7'};text-decoration:none;color:#111;'>Queued</a>
          <a href='{generating_tab}' style='padding:6px 10px;border-radius:8px;background:{'#e0f2fe' if status=='generating' else '#eef2f7'};text-decoration:none;color:#111;'>Generating</a>
          <a href='{submitted_tab}' style='padding:6px 10px;border-radius:8px;background:{'#e0f2fe' if status=='submitted' else '#eef2f7'};text-decoration:none;color:#111;'>Submitted</a>
          <a href='{generated_tab}' style='padding:6px 10px;border-radius:8px;background:{'#e0f2fe' if status=='generated' else '#eef2f7'};text-decoration:none;color:#111;'>Generated</a>
          <a href='{failed_tab}' style='padding:6px 10px;border-radius:8px;background:{'#e0f2fe' if status=='failed' else '#eef2f7'};text-decoration:none;color:#111;'>Failed</a>
        </div>
        <h2 style='margin-top:4px;'>목록 ({status})</h2>
        <p style='color:#666;'>total={total}, page={page}/{total_pages}, page_size={page_size}</p>
        <div style='display:flex;gap:8px;margin:6px 0 8px;'>
          <a href='{filter_all}' style='padding:6px 10px;border-radius:8px;background:{'#dbeafe' if overview_filter=='all' else '#eef2f7'};text-decoration:none;color:#111;'>전체</a>
          <a href='{filter_long}' style='padding:6px 10px;border-radius:8px;background:{'#dbeafe' if overview_filter=='long' else '#eef2f7'};text-decoration:none;color:#111;'>200자 이상</a>
        </div>
        <div style='display:flex;gap:8px;margin:8px 0 14px;'>
          <a href='{size_20}' style='padding:6px 10px;border-radius:8px;background:{'#dbeafe' if page_size==20 else '#eef2f7'};text-decoration:none;color:#111;'>20개</a>
          <a href='{size_50}' style='padding:6px 10px;border-radius:8px;background:{'#dbeafe' if page_size==50 else '#eef2f7'};text-decoration:none;color:#111;'>50개</a>
          <a href='{size_100}' style='padding:6px 10px;border-radius:8px;background:{'#dbeafe' if page_size==100 else '#eef2f7'};text-decoration:none;color:#111;'>100개</a>
          <a href='{size_200}' style='padding:6px 10px;border-radius:8px;background:{'#dbeafe' if page_size==200 else '#eef2f7'};text-decoration:none;color:#111;'>200개</a>
        </div>
        {queued_html}
        <div style='display:flex;gap:8px;margin:12px 0;'>
          <a href='{prev_link}' style='padding:6px 10px;border-radius:8px;background:#e5e7eb;text-decoration:none;color:#111;'>이전</a>
          <a href='{next_link}' style='padding:6px 10px;border-radius:8px;background:#e5e7eb;text-decoration:none;color:#111;'>다음</a>
        </div>

        <h2>실패 항목</h2>
        <ul>{failed_html}</ul>
      </body>
    </html>
    """


@app.post("/admin/parse")
def parse_now() -> RedirectResponse:
    engine.parse_sources()
    return RedirectResponse(url="/", status_code=303)


@app.post("/admin/generate-batch")
def generate_batch() -> RedirectResponse:
    engine.generate_daily_batch()
    return RedirectResponse(url="/", status_code=303)


@app.post("/admin/generate/{candidate_id}")
def generate_one(candidate_id: int) -> RedirectResponse:
    try:
        engine.generate_one(candidate_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse(url="/?msg=생성+완료", status_code=303)


@app.post("/admin/reset/{candidate_id}")
def reset_one(candidate_id: int) -> RedirectResponse:
    try:
        engine.reset_generated_flag(candidate_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse(url="/?msg=대기열+복구+완료(재생성+가능)", status_code=303)


@app.post("/admin/delete/{candidate_id}")
def delete_one(candidate_id: int) -> RedirectResponse:
    try:
        engine.delete_candidate(candidate_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse(url="/?msg=항목+삭제+완료", status_code=303)


@app.post("/admin/enrich/{candidate_id}")
def enrich_one(candidate_id: int) -> RedirectResponse:
    try:
        res = engine.enrich_one(candidate_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if int(res.get("enriched", 0)) > 0:
        msg = (
            f"줄거리 보강 완료 (검색 {int(res.get('snippet_count', 0))}건, "
            f"AI {'사용' if int(res.get('ai_used', 0)) > 0 else '미사용'})"
        )
        return RedirectResponse(url=f"/?msg={quote_plus(msg)}", status_code=303)
    msg = (
        f"보강 결과 없음: reason={res.get('reason','unknown')} "
        f"(검색 {int(res.get('snippet_count', 0))}건, AI {'사용' if int(res.get('ai_used', 0)) > 0 else '미사용'})"
    )
    if str(res.get("reason", "")) in {"tavily_no_results", "tavily_key_missing"}:
        msg += " | TAVILY_API_KEY(또는 ENRICH_TAVILY_API_KEY) 설정 확인"
    if str(res.get("reason", "")) == "ai_key_missing":
        msg += " | BLOG_ENGINE_OPENAI_API_KEY 설정 필요"
    return RedirectResponse(url=f"/?msg={quote_plus(msg)}", status_code=303)
