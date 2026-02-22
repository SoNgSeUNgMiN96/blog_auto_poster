from __future__ import annotations

from typing import Any

import requests

from app.config import Settings


class BEngineClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.b_engine_base_url.rstrip("/")

    def generate_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.settings.b_engine_admin_token:
            headers["x-admin-token"] = self.settings.b_engine_admin_token

        response = requests.post(
            f"{self.base_url}/generate-post",
            json=payload,
            headers=headers,
            timeout=45,
        )
        if response.status_code >= 400:
            body = response.text[:1000]
            raise RuntimeError(
                f"B-engine generate-post failed: status={response.status_code}, body={body}"
            )
        return response.json()
