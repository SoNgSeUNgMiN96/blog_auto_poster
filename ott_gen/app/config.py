from functools import lru_cache
import os
from pathlib import Path
from urllib.parse import quote_plus

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
    b_engine_submit_mode: str = Field(default="db_queue", alias="B_ENGINE_SUBMIT_MODE")
    b_engine_admin_token: str = Field(default="", alias="B_ENGINE_ADMIN_TOKEN")
    b_engine_render_template: str = Field(default="ott_review.html", alias="B_ENGINE_RENDER_TEMPLATE")
    b_engine_auto_publish: bool = Field(default=True, alias="B_ENGINE_AUTO_PUBLISH")
    b_engine_db_driver: str = Field(default="mysql+pymysql", alias="B_ENGINE_DB_DRIVER")
    b_engine_db_host: str = Field(default="127.0.0.1", alias="B_ENGINE_DB_HOST")
    b_engine_db_port: int = Field(default=3306, alias="B_ENGINE_DB_PORT")
    b_engine_db_name: str = Field(default="blog_engine_dev", alias="B_ENGINE_DB_NAME")
    b_engine_db_user: str = Field(default="root", alias="B_ENGINE_DB_USER")
    b_engine_db_password: str = Field(default="", alias="B_ENGINE_DB_PASSWORD")
    b_engine_db_password_env: str = Field(default="BLOG_ENGINE_DB_PASSWORD", alias="B_ENGINE_DB_PASSWORD_ENV")
    b_engine_db_charset: str = Field(default="utf8mb4", alias="B_ENGINE_DB_CHARSET")
    b_engine_system_role: str = Field(default="", alias="B_ENGINE_SYSTEM_ROLE")
    prompt_template: str = Field(
        default=(
            "너는 네이버에서 활동하는 한국 OTT 리뷰 블로거야. 아래 정보를 바탕으로 '끝까지 읽히는' 리뷰를 작성해줘. "
            "말투는 캐주얼 존댓말(해요체)만 사용하고 반말은 금지해. "
            "[핵심 목표] 몰입감, 후킹, 가독성, 정보 밀도, 신뢰감을 동시에 만족. "
            "[도입 규칙] 첫 3문장은 반드시 후킹 구조로 작성: ①공감/질문 또는 강한 한 줄 ②작품의 핵심 갈등 티저 ③이 글을 읽어야 할 이유. "
            "[전개 규칙] 줄거리 설명 비중을 충분히 확보하고(시간순), 인물 선택/갈등 변화/분위기 전환 포인트를 구체적으로 써줘. "
            "감상평만 나열하지 말고 '왜 재미있는지/왜 호불호 갈리는지' 근거를 붙여줘. "
            "결말 핵심 스포일러는 피하고, 중후반 반전은 완곡하게 표현해. "
            "[가독성 규칙] 문장은 짧고 리듬감 있게. 문장 끝(.,!,?) 뒤에는 자연 줄바꿈. 필요하면 Markdown(굵게/리스트/인용) 사용. "
            "[후킹 규칙] 섹션 말미에 다음 문단이 궁금해지도록 짧은 오픈 루프를 1문장 넣어줘. "
            "[반복 방지] 도입 방식(질문형/고백형/상황형/비교형/한줄평형), 섹션 제목 패턴, 마무리 톤을 매번 다르게 섞어 써줘. "
            "같은 표현/같은 문장 구조/같은 클리셰 반복 금지. 특히 '안녕하세요 오늘은', '추천드립니다', '정리해봤어요' 남발 금지. "
            "[이모지 규칙] 문맥에 맞게 1~4개만 자연 사용. 트렌디 후보: 🫠 🫶 🔥 ✨ 👀 💥 😵‍💫 😭 🤭 🥹 😮‍💨 🧠 🎬. 반복/억지 텐션 금지. "
            "[출력 품질] 정보는 구체적이고 문장은 생동감 있게, 하지만 과장/허위/추측은 금지. "
            "제목은 18~24자 내외로 강하게 후킹되게. "
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

    @property
    def b_engine_effective_db_password(self) -> str:
        if self.b_engine_db_password_env:
            secret = os.getenv(self.b_engine_db_password_env, "")
            if secret:
                return secret
        return self.b_engine_db_password

    @property
    def b_engine_sqlalchemy_url(self) -> str:
        user_encoded = quote_plus(self.b_engine_db_user)
        password = self.b_engine_effective_db_password
        if password:
            auth = f"{user_encoded}:{quote_plus(password)}@"
        else:
            auth = f"{user_encoded}@"
        return (
            f"{self.b_engine_db_driver}://{auth}{self.b_engine_db_host}:{self.b_engine_db_port}/"
            f"{self.b_engine_db_name}?charset={self.b_engine_db_charset}"
        )


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
