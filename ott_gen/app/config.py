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
    run_mode: str = Field(default="hybrid", alias="RUN_MODE")
    candidate_pages: int = Field(default=2, alias="CANDIDATE_PAGES")
    per_page_limit: int = Field(default=10, alias="PER_PAGE_LIMIT")
    latest_daily_pages: int = Field(default=1, alias="LATEST_DAILY_PAGES")
    backfill_pages_per_run: int = Field(default=3, alias="BACKFILL_PAGES_PER_RUN")
    backfill_sort_by: str = Field(default="popularity.desc", alias="BACKFILL_SORT_BY")
    min_stills: int = Field(default=2, alias="MIN_STILLS")
    max_stills: int = Field(default=4, alias="MAX_STILLS")
    dedup_days: int = Field(default=30, alias="DEDUP_DAYS")
    enrich_overview: bool = Field(default=True, alias="ENRICH_OVERVIEW")
    overview_min_length: int = Field(default=120, alias="OVERVIEW_MIN_LENGTH")
    scheduler_min_overview_length: int = Field(default=200, alias="SCHEDULER_MIN_OVERVIEW_LENGTH")
    scheduler_enrich_overview: bool = Field(default=True, alias="SCHEDULER_ENRICH_OVERVIEW")
    enrich_search_max_snippets: int = Field(default=5, alias="ENRICH_SEARCH_MAX_SNIPPETS")
    enrich_ai_summary: bool = Field(default=True, alias="ENRICH_AI_SUMMARY")
    enrich_openai_api_key: str = Field(default="", alias="ENRICH_OPENAI_API_KEY")
    enrich_openai_api_key_env: str = Field(default="BLOG_ENGINE_OPENAI_API_KEY", alias="ENRICH_OPENAI_API_KEY_ENV")
    enrich_openai_model: str = Field(default="gpt-4.1-mini", alias="ENRICH_OPENAI_MODEL")
    enrich_tavily_api_key: str = Field(default="", alias="ENRICH_TAVILY_API_KEY")
    enrich_tavily_api_key_env: str = Field(default="TAVILY_API_KEY", alias="ENRICH_TAVILY_API_KEY_ENV")

    daily_generate_limit: int = Field(default=3, alias="DAILY_GENERATE_LIMIT")
    publish_hours: str = Field(default="10,15,21", alias="PUBLISH_HOURS")
    publish_minute: int = Field(default=0, alias="PUBLISH_MINUTE")
    parse_hour: int = Field(default=9, alias="PARSE_HOUR")
    parse_minute: int = Field(default=5, alias="PARSE_MINUTE")
    timezone: str = Field(default="Asia/Seoul", alias="TIMEZONE")

    b_engine_base_url: str = Field(default="http://127.0.0.1:8000", alias="B_ENGINE_BASE_URL")
    b_engine_admin_token: str = Field(default="", alias="B_ENGINE_ADMIN_TOKEN")
    b_engine_render_template: str = Field(default="ott_review.html", alias="B_ENGINE_RENDER_TEMPLATE")
    b_engine_auto_publish: bool = Field(default=True, alias="B_ENGINE_AUTO_PUBLISH")
    b_engine_system_role: str = Field(default="", alias="B_ENGINE_SYSTEM_ROLE")
    prompt_template: str = Field(
        default=(
            "너는 네이버에서 활동하는 한국 OTT 리뷰 블로거야. 친구에게 추천하듯 자연스럽고 트렌디한 캐주얼 존댓말(해요체)로만 써줘. 반말은 절대 사용하지 마. "
            "첫 문단은 가벼운 인사로 시작해줘(예: 안녕하세요, 오늘은 ...). "
            "딱딱한 분석체 대신 솔직한 감상, 재밌었던 장면, 아쉬웠던 포인트를 균형 있게 담아줘. "
            "줄거리 파트는 가능한 한 상세하게 반영하되 시간순 전개가 보이게 정리하고, 작품의 호기심을 자극할 정도로 정보 밀도를 높여줘. "
            "감상평만 쓰지 말고 줄거리 설명 비중도 충분히 확보해줘. 단, 결말 핵심 스포일러는 피하고 중후반 반전은 완곡하게 표현해줘. "
            "문단 가독성을 위해 필요한 경우에만 Markdown 서식(굵게, 리스트, 인용문)을 자연스럽게 사용해줘. 과도한 장식은 금지해줘. "
            "문장은 너무 길게 붙이지 말고, 문장 끝(.,!,?) 뒤에는 자연스럽게 줄바꿈해 가독성을 높여줘. "
            "이모지는 문맥에 맞게 자연스럽게 사용해줘(본문 전체 1~4개 권장). "
            "트렌디한 후보: 🫠 🫶 🔥 ✨ 👀 💥 😵‍💫 😭 🤭 🥹 😮‍💨 🧠 🎬. "
            "같은 이모지 반복은 피하고, 억지 텐션은 금지해줘. "
            "제목은 너무 길지 않게 20자 내외로 매력적으로 작성해줘. "
            "정보: 제목={title}, 줄거리={overview}, 원본줄거리={original_overview}, 보강줄거리={enriched_overview}, 컨텍스트={overview_context}, 평점={rating}, 장르={genres}, 연도={year}. "
            "반드시 JSON(title, sections, tags, meta_description)으로만 출력해."
        ),
        alias="PROMPT_TEMPLATE",
    )

    sqlite_path: Path = Field(default=Path("./data/ott_gen.db"), alias="SQLITE_PATH")
    web_host: str = Field(default="0.0.0.0", alias="WEB_HOST")
    web_port: int = Field(default=8010, alias="WEB_PORT")

    @property
    def target_provider_set(self) -> set[str]:
        return {x.strip().lower() for x in self.target_providers.split(",") if x.strip()}

    @property
    def publish_hours_list(self) -> list[int]:
        out: set[int] = set()
        for x in self.publish_hours.split(","):
            x = x.strip()
            if not x:
                continue
            try:
                v = int(x)
            except ValueError:
                continue
            if 0 <= v <= 23:
                out.add(v)
        ordered = sorted(out)
        return ordered or [10, 15, 21]

    @property
    def effective_publish_minute(self) -> int:
        if 0 <= self.publish_minute <= 59:
            return self.publish_minute
        return 0

    @property
    def effective_parse_minute(self) -> int:
        if 0 <= self.parse_minute <= 59:
            return self.parse_minute
        return 5

    @property
    def effective_parse_hour(self) -> int:
        if 0 <= self.parse_hour <= 23:
            return self.parse_hour
        return 9

    @property
    def effective_enrich_openai_api_key(self) -> str:
        if self.enrich_openai_api_key_env:
            secret = os.getenv(self.enrich_openai_api_key_env, "")
            if secret:
                return secret
        return self.enrich_openai_api_key

    @property
    def effective_enrich_tavily_api_key(self) -> str:
        if self.enrich_tavily_api_key_env:
            secret = os.getenv(self.enrich_tavily_api_key_env, "")
            if secret:
                return secret
        return self.enrich_tavily_api_key


@lru_cache
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    base_dir = Path(__file__).resolve().parents[1]
    env_path = base_dir / "env" / f".env.{app_env}"
    if env_path.exists():
        return Settings(_env_file=env_path)
    env_example_path = base_dir / "env" / f".env.{app_env}.example"
    if env_example_path.exists():
        return Settings(_env_file=env_example_path)
    return Settings()
