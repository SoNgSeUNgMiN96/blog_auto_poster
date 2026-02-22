from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pymysql
import requests

from app.config import Settings


class BEngineClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.b_engine_base_url.rstrip("/")

    def generate_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        submit_mode = (self.settings.b_engine_submit_mode or "api").strip().lower()
        if submit_mode == "db_queue":
            return self._enqueue_to_b_engine_db(payload)
        if submit_mode == "api":
            return self._submit_via_api(payload)
        raise RuntimeError(f"Unsupported B_ENGINE_SUBMIT_MODE: {self.settings.b_engine_submit_mode}")

    def _submit_via_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.settings.b_engine_admin_token:
            headers["x-admin-token"] = self.settings.b_engine_admin_token

        response = requests.post(
            f"{self.base_url}/generate-post",
            json=payload,
            headers=headers,
            timeout=60,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"B-engine generate-post failed: status={response.status_code}, body={response.text[:1000]}"
            )
        return response.json()

    def _enqueue_to_b_engine_db(self, payload: dict[str, Any]) -> dict[str, Any]:
        connection = pymysql.connect(
            host=self.settings.b_engine_db_host,
            port=self.settings.b_engine_db_port,
            user=self.settings.b_engine_db_user,
            password=self.settings.b_engine_effective_db_password,
            database=self.settings.b_engine_db_name,
            charset=self.settings.b_engine_db_charset,
            autocommit=True,
        )
        try:
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            raw_json = json.dumps(payload, ensure_ascii=False)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO posts (raw_input, status, created_at)
                    VALUES (%s, %s, %s)
                    """,
                    (raw_json, "queued", now),
                )
                post_id = int(cursor.lastrowid or 0)
            return {"post_id": post_id, "status": "queued"}
        except Exception as exc:
            raise RuntimeError(f"B-engine DB enqueue failed: {exc}") from exc
        finally:
            connection.close()
