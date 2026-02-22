from __future__ import annotations

from pathlib import Path
import mimetypes
from typing import Any

import requests
from requests.auth import HTTPBasicAuth
from slugify import slugify

from app.config import Settings


class WordPressPublisher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.wordpress_base_url.rstrip("/")
        self.auth = HTTPBasicAuth(settings.wordpress_username, settings.wordpress_app_password)

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def _request_with_rest_fallback(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        data: Any = None,
        files: Any = None,
    ) -> requests.Response:
        urls = [
            f"{self.base_url}/wp-json{path}",
            f"{self.base_url}/?rest_route={path}",
        ]
        last_response: requests.Response | None = None
        for url in urls:
            response = requests.request(
                method,
                url,
                headers=headers,
                auth=self.auth,
                json=json,
                data=data,
                files=files,
                timeout=30,
            )
            if response.status_code != 404:
                if response.status_code >= 400:
                    raise RuntimeError(
                        f"WordPress REST error: status={response.status_code}, url={url}, body={response.text[:1000]}"
                    )
                return response
            last_response = response

        if last_response is not None:
            raise RuntimeError(
                f"WordPress REST endpoint not found: status={last_response.status_code}, "
                f"url={last_response.url}, body={last_response.text[:1000]}"
            )
        raise RuntimeError("WordPress REST endpoint not reachable")

    def upload_media(self, file_path: Path) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        file_bytes = file_path.read_bytes()
        response = self._request_with_rest_fallback(
            "POST",
            "/wp/v2/media",
            headers=self._headers(),
            files={"file": (file_path.name, file_bytes, mime_type)},
        )
        return response.json()

    def publish_post(
        self,
        title: str,
        content: str,
        slug: str,
        featured_media_id: int | None = None,
        category_ids: list[int] | None = None,
        tag_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "title": title,
            "content": content,
            "status": self.settings.wordpress_default_status,
            "slug": slug,
        }
        if featured_media_id:
            payload["featured_media"] = featured_media_id
        if category_ids:
            payload["categories"] = category_ids
        if tag_ids:
            payload["tags"] = tag_ids

        response = self._request_with_rest_fallback(
            "POST",
            "/wp/v2/posts",
            headers=self._headers(),
            json=payload,
        )
        return response.json()

    def ensure_category(self, category_name: str) -> int:
        category_name = category_name.strip()
        if not category_name:
            raise ValueError("Category name is required")

        response = self._request_with_rest_fallback(
            "GET",
            "/wp/v2/categories",
            headers=self._headers(),
        )
        categories = response.json()
        if isinstance(categories, list):
            for cat in categories:
                if str(cat.get("name", "")).strip().lower() == category_name.lower():
                    cat_id = cat.get("id")
                    if isinstance(cat_id, int):
                        return cat_id

        create_response = self._request_with_rest_fallback(
            "POST",
            "/wp/v2/categories",
            headers=self._headers(),
            json={"name": category_name, "slug": slugify(category_name)},
        )
        created = create_response.json()
        cat_id = created.get("id")
        if not isinstance(cat_id, int):
            raise RuntimeError("Failed to create WordPress category")
        return cat_id

    def ensure_tag(self, tag_name: str) -> int:
        tag_name = tag_name.strip()
        if not tag_name:
            raise ValueError("Tag name is required")

        response = self._request_with_rest_fallback(
            "GET",
            "/wp/v2/tags",
            headers=self._headers(),
        )
        tags = response.json()
        if isinstance(tags, list):
            for tag in tags:
                if str(tag.get("name", "")).strip().lower() == tag_name.lower():
                    tag_id = tag.get("id")
                    if isinstance(tag_id, int):
                        return tag_id

        create_response = self._request_with_rest_fallback(
            "POST",
            "/wp/v2/tags",
            headers=self._headers(),
            json={"name": tag_name, "slug": slugify(tag_name)},
        )
        created = create_response.json()
        tag_id = created.get("id")
        if not isinstance(tag_id, int):
            raise RuntimeError("Failed to create WordPress tag")
        return tag_id
