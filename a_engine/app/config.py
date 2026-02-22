from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")

    tmdb_api_key: str = Field(default="", alias="TMDB_API_KEY")
    tmdb_language: str = Field(default="ko-KR", alias="TMDB_LANGUAGE")
    tmdb_region: str = Field(default="KR", alias="TMDB_REGION")
    tmdb_image_base_url: str = Field(default="https://image.tmdb.org/t/p/original", alias="TMDB_IMAGE_BASE_URL")

    target_providers: str = Field(default="Netflix,Disney Plus", alias="TARGET_PROVIDERS")
    collect_limit: int = Field(default=3, alias="COLLECT_LIMIT")
    min_stills: int = Field(default=2, alias="MIN_STILLS")
    max_stills: int = Field(default=4, alias="MAX_STILLS")
    dedup_days: int = Field(default=30, alias="DEDUP_DAYS")

    b_engine_base_url: str = Field(default="http://127.0.0.1:8000", alias="B_ENGINE_BASE_URL")
    b_engine_admin_token: str = Field(default="", alias="B_ENGINE_ADMIN_TOKEN")
    b_engine_render_template: str = Field(default="ott_review.html", alias="B_ENGINE_RENDER_TEMPLATE")
    b_engine_auto_publish: bool = Field(default=True, alias="B_ENGINE_AUTO_PUBLISH")
    b_engine_system_role: str = Field(
        default="당신은 한국의 트렌디한 블로거입니다. 사람 말투로, 솔직한 감상 중심으로, 과하게 딱딱한 분석체를 피하세요.",
        alias="B_ENGINE_SYSTEM_ROLE",
    )

    prompt_template: str = Field(alias="PROMPT_TEMPLATE")

    run_mode: str = Field(default="trending", alias="RUN_MODE")
    candidate_pages: int = Field(default=2, alias="CANDIDATE_PAGES")
    cron_hour_1: int = Field(default=9, alias="CRON_HOUR_1")
    cron_hour_2: int = Field(default=21, alias="CRON_HOUR_2")
    timezone: str = Field(default="Asia/Seoul", alias="TIMEZONE")

    sqlite_path: Path = Field(default=Path("./data/a_engine.db"), alias="SQLITE_PATH")

    @property
    def target_provider_set(self) -> set[str]:
        return {x.strip().lower() for x in self.target_providers.split(",") if x.strip()}


@lru_cache
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    base_dir = Path(__file__).resolve().parents[1]
    env_path = base_dir / "env" / f".env.{app_env}"
    if env_path.exists():
        return Settings(_env_file=env_path)
    return Settings()
