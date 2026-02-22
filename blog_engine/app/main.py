from datetime import datetime
from pathlib import Path
import re
from typing import Any

import markdown as md
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, engine, get_db
from app.models.image import Image
from app.models.post import Post
from app.schemas.request import GeneratePostRequest
from app.schemas.response import GeneratePostResponse, PostStatusResponse, PublishResponse
from app.services.content_generator import ContentGenerator
from app.services.html_renderer import HtmlRenderer
from app.services.image_engine import ImageEngine
from app.services.indexing_service import IndexingService
from app.services.seo_engine import SeoEngine
from app.services.wordpress_publisher import WordPressPublisher

settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
app = FastAPI(title=settings.app_name)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def startup_sync_tables() -> None:
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


def verify_admin_token(x_admin_token: str = Header(default="")) -> None:
    if settings.api_admin_token and x_admin_token != settings.api_admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _build_unique_slug(db: Session, base_slug: str, current_post_id: int) -> str:
    root_slug = base_slug or f"post-{current_post_id}"
    slug = root_slug
    index = 2
    while True:
        exists = db.execute(
            select(Post.id).where(Post.slug == slug, Post.id != current_post_id)
        ).scalar_one_or_none()
        if not exists:
            return slug
        slug = f"{root_slug}-{index}"
        index += 1


def _resolve_wp_category_name(post: Post) -> str | None:
    if settings.wordpress_default_category:
        return settings.wordpress_default_category

    content_type = str((post.raw_input or {}).get("content_type", "")).strip().lower()
    if not content_type:
        return None
    return settings.wordpress_category_map_dict.get(content_type)


def _build_display_title(work_title: str, generated_title: str) -> str:
    clean_work_title = (work_title or "").strip()
    clean_generated_title = (generated_title or "").strip()
    if not clean_work_title:
        return clean_generated_title
    prefix = f"[{clean_work_title}]"
    # Avoid repeating the work title in the AI-generated suffix.
    suffix = clean_generated_title
    if suffix.startswith(prefix):
        suffix = suffix[len(prefix) :].strip()

    patterns = [
        re.escape(clean_work_title),
        re.escape(f"[{clean_work_title}]"),
        re.escape(f'"{clean_work_title}"'),
        re.escape(f"'{clean_work_title}'"),
        re.escape(f"《{clean_work_title}》"),
        re.escape(f"<{clean_work_title}>"),
    ]
    suffix = re.sub("|".join(patterns), " ", suffix, flags=re.IGNORECASE).strip()
    suffix = re.sub(r"\s+", " ", suffix).strip(" -:|,./")
    if not suffix:
        suffix = "리뷰"
    return f"{prefix} {suffix}"


def _render_section_html(content: str) -> str:
    normalized = re.sub(r"([.!?])\s+(?=[A-Za-z0-9가-힣\"'(\[])",
                        r"\1\n",
                        str(content or ""))
    return md.markdown(
        normalized,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html5",
    )


def _publish_post_internal(db: Session, post: Post) -> PublishResponse:
    if not post.rendered_html or not post.seo_title or not post.slug:
        raise HTTPException(status_code=400, detail="Post is not ready for publishing")

    publisher = WordPressPublisher(settings)

    featured_media_id = None
    content_html = post.rendered_html
    for image in sorted(post.images, key=lambda x: x.order):
        media = publisher.upload_media(Path(image.local_path))
        image.wp_media_id = media.get("id")
        wp_media_url = media.get("source_url") or ((media.get("guid") or {}).get("rendered"))
        if wp_media_url and content_html:
            # Replace locally-rendered image path with final WordPress media URL.
            content_html = content_html.replace(image.local_path, wp_media_url)
        if featured_media_id is None:
            featured_media_id = image.wp_media_id

    category_ids: list[int] = []
    category_name = _resolve_wp_category_name(post)
    if category_name:
        category_ids.append(publisher.ensure_category(category_name))

    tag_ids: list[int] = []
    raw_tags = []
    if isinstance(post.generated_content, dict):
        raw_tags = post.generated_content.get("tags", []) or []
    if isinstance(raw_tags, list):
        for tag in raw_tags[:15]:
            tag_text = str(tag or "").strip().lstrip("#").strip()
            if not tag_text:
                continue
            try:
                tag_ids.append(publisher.ensure_tag(tag_text))
            except Exception:
                # Tag creation failure should not block publishing.
                continue

    wp_post = publisher.publish_post(
        title=post.seo_title,
        content=content_html,
        slug=post.slug,
        featured_media_id=featured_media_id,
        category_ids=category_ids,
        tag_ids=tag_ids,
    )

    post.wp_post_id = wp_post.get("id")
    post.wp_url = wp_post.get("link")
    post.status = "published"
    post.published_at = datetime.utcnow()
    db.commit()

    if post.wp_url:
        indexing = IndexingService(settings)
        indexing.notify(post.wp_url)

    return PublishResponse(
        post_id=post.id,
        status=post.status,
        wp_post_id=post.wp_post_id,
        wp_url=post.wp_url,
    )


@app.post("/generate-post", response_model=GeneratePostResponse)
@limiter.limit(settings.rate_limit)
def generate_post(
    request: Request,
    payload: GeneratePostRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
) -> GeneratePostResponse:
    post = Post(raw_input=payload.model_dump(), status="draft")
    db.add(post)
    db.commit()
    db.refresh(post)

    try:
        content_generator = ContentGenerator(settings)
        generated = content_generator.generate(payload.model_dump())
        seo = SeoEngine.optimize(generated)
        work_title = str(payload.prompt_variables.get("title", "")).strip()
        final_title = _build_display_title(work_title, seo["seo_title"])
        seo["seo_title"] = final_title
        seo["slug"] = slugify(final_title)[:120] or f"post-{post.id}"

        image_engine = ImageEngine(settings)
        stored_images: list[dict[str, str]] = []
        for idx, image in enumerate(payload.images):
            local_path = image_engine.download_and_convert(image.url, post.id, idx)
            stored_images.append({"path": str(local_path), "type": image.type})
            db.add(
                Image(
                    post_id=post.id,
                    original_url=image.url,
                    local_path=str(local_path),
                    order=idx,
                )
            )

        poster_url = next((img["path"] for img in stored_images if img["type"] == "poster"), None)
        if not poster_url and stored_images:
            poster_url = stored_images[0]["path"]
        still_urls = [img["path"] for img in stored_images if img["type"] == "still"]
        rendered_sections = [
            {
                "heading": str(section.get("heading", "") or ""),
                "content": str(section.get("content", "") or ""),
                "content_html": _render_section_html(str(section.get("content", "") or "")),
            }
            for section in generated.get("sections", [])
        ]

        renderer = HtmlRenderer(Path(__file__).resolve().parent / "templates")
        html = renderer.render(
            payload.render_template,
            {
                "seo_title": seo["seo_title"],
                "meta_description": seo["meta_description"],
                "sections": rendered_sections,
                "tags": seo["tags"],
                "poster_url": poster_url,
                "still_urls": still_urls,
            },
        )

        generated["tags"] = seo["tags"]
        generated["meta_description"] = seo["meta_description"]
        generated["title"] = seo["seo_title"]

        post.generated_content = generated
        post.rendered_html = html
        post.seo_title = seo["seo_title"]
        post.meta_description = seo["meta_description"]
        post.slug = _build_unique_slug(db, seo["slug"], post.id)
        post.status = "generated"

        db.commit()
        if payload.auto_publish:
            publish_result = _publish_post_internal(db, post)
            return GeneratePostResponse(
                post_id=publish_result.post_id,
                status=publish_result.status,
            )
        return GeneratePostResponse(post_id=post.id, status=post.status)
    except Exception as exc:
        db.rollback()
        failed_post = db.get(Post, post.id)
        if failed_post:
            failed_post.status = "failed"
            db.commit()
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc


@app.post("/publish/{post_id}", response_model=PublishResponse)
@limiter.limit(settings.rate_limit)
def publish_post(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
) -> PublishResponse:
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    try:
        return _publish_post_internal(db, post)
    except Exception as exc:
        db.rollback()
        failed_post = db.get(Post, post.id)
        if failed_post:
            failed_post.status = "failed"
            db.commit()
        raise HTTPException(status_code=500, detail=f"Publish failed: {exc}") from exc


@app.get("/status/{post_id}", response_model=PostStatusResponse)
def get_status(
    post_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_token),
) -> PostStatusResponse:
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return PostStatusResponse(
        post_id=post.id,
        status=post.status,
        slug=post.slug,
        seo_title=post.seo_title,
        wp_post_id=post.wp_post_id,
        published_at=post.published_at,
        generated_content=post.generated_content,
    )
