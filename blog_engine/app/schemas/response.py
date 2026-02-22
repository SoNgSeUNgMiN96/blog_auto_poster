from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GeneratePostResponse(BaseModel):
    post_id: int
    status: str


class PublishResponse(BaseModel):
    post_id: int
    status: str
    wp_post_id: int
    wp_url: str | None


class PostStatusResponse(BaseModel):
    post_id: int
    status: str
    slug: str | None
    seo_title: str | None
    wp_post_id: int | None
    published_at: datetime | None
    generated_content: dict[str, Any] | None
