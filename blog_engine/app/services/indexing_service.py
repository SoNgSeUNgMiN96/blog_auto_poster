from __future__ import annotations

from typing import Any

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import Settings


class IndexingService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def notify(self, url: str) -> dict[str, Any]:
        results: dict[str, Any] = {}
        if self.settings.google_service_account_file:
            try:
                results["google"] = self._notify_google(url)
            except Exception as exc:
                results["google_error"] = str(exc)

        try:
            results["naver"] = self._notify_naver(url)
        except Exception as exc:
            results["naver_error"] = str(exc)

        return results

    def _notify_google(self, url: str) -> dict[str, Any]:
        credentials = service_account.Credentials.from_service_account_file(
            self.settings.google_service_account_file,
            scopes=[scope.strip() for scope in self.settings.google_indexing_scopes.split(",") if scope.strip()],
        )
        service = build("indexing", "v3", credentials=credentials, cache_discovery=False)
        response = (
            service.urlNotifications()
            .publish(body={"url": url, "type": "URL_UPDATED"})
            .execute()
        )
        return response

    def _notify_naver(self, url: str) -> dict[str, Any]:
        response = requests.get(self.settings.naver_rss_ping_url, params={"url": url}, timeout=15)
        return {"status_code": response.status_code, "text": response.text[:200]}
