from functools import lru_cache
import os
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="blog-engine", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    api_admin_token: str = Field(default="", alias="API_ADMIN_TOKEN")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_driver: str = Field(default="mysql+pymysql", alias="DB_DRIVER")
    db_host: str = Field(default="127.0.0.1", alias="DB_HOST")
    db_port: int = Field(default=3306, alias="DB_PORT")
    db_name: str = Field(default="blog_engine_dev", alias="DB_NAME")
    db_user: str = Field(default="root", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_password_env: str = Field(default="BLOG_ENGINE_DB_PASSWORD", alias="DB_PASSWORD_ENV")
    db_charset: str = Field(default="utf8mb4", alias="DB_CHARSET")
    media_root: Path = Field(default=Path("./media"), alias="MEDIA_ROOT")
    image_max_width: int = Field(default=1600, alias="IMAGE_MAX_WIDTH")
    image_max_height: int = Field(default=1600, alias="IMAGE_MAX_HEIGHT")
    image_webp_quality: int = Field(default=82, alias="IMAGE_WEBP_QUALITY")
    image_keep_original: bool = Field(default=False, alias="IMAGE_KEEP_ORIGINAL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_api_key_env: str = Field(default="BLOG_ENGINE_OPENAI_API_KEY", alias="OPENAI_API_KEY_ENV")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    wordpress_base_url: str = Field(default="", alias="WORDPRESS_BASE_URL")
    wordpress_public_base_url: str = Field(default="", alias="WORDPRESS_PUBLIC_BASE_URL")
    wordpress_username: str = Field(default="", alias="WORDPRESS_USERNAME")
    wordpress_app_password: str = Field(default="", alias="WORDPRESS_APP_PASSWORD")
    wordpress_default_status: str = Field(default="publish", alias="WORDPRESS_DEFAULT_STATUS")
    wordpress_default_category: str = Field(default="", alias="WORDPRESS_DEFAULT_CATEGORY")
    wordpress_category_map: str = Field(default="ott:OTT 리뷰", alias="WORDPRESS_CATEGORY_MAP")

    google_service_account_file: str = Field(default="", alias="GOOGLE_SERVICE_ACCOUNT_FILE")
    google_indexing_scopes: str = Field(
        default="https://www.googleapis.com/auth/indexing", alias="GOOGLE_INDEXING_SCOPES"
    )
    naver_rss_ping_url: str = Field(
        default="https://searchadvisor.naver.com/ping", alias="NAVER_RSS_PING_URL"
    )

    rate_limit: str = Field(default="30/minute", alias="RATE_LIMIT")
    auto_create_tables: bool = Field(default=True, alias="AUTO_CREATE_TABLES")
    processing_mode: str = Field(default="queue", alias="PROCESSING_MODE")
    batch_process_limit: int = Field(default=20, alias="BATCH_PROCESS_LIMIT")
    worker_random_delay_min_minutes: int = Field(default=0, alias="WORKER_RANDOM_DELAY_MIN_MINUTES")
    worker_random_delay_max_minutes: int = Field(default=35, alias="WORKER_RANDOM_DELAY_MAX_MINUTES")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        # Prefer explicitly named secret env var over generic DB_PASSWORD.
        password = ""
        if self.db_password_env:
            password = os.getenv(self.db_password_env, "")
        if not password:
            password = self.db_password

        user_encoded = quote_plus(self.db_user)
        if password:
            auth = f"{user_encoded}:{quote_plus(password)}@"
        else:
            auth = f"{user_encoded}@"

        return (
            f"{self.db_driver}://{auth}{self.db_host}:{self.db_port}/"
            f"{self.db_name}?charset={self.db_charset}"
        )

    @property
    def effective_openai_api_key(self) -> str:
        if self.openai_api_key_env:
            secret = os.getenv(self.openai_api_key_env, "")
            if secret:
                return secret
        return self.openai_api_key

    @property
    def wordpress_category_map_dict(self) -> dict[str, str]:
        result: dict[str, str] = {}
        raw = (self.wordpress_category_map or "").strip()
        if not raw:
            return result
        for item in raw.split(","):
            pair = item.strip()
            if ":" not in pair:
                continue
            key, value = pair.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key and value:
                result[key] = value
        return result


@lru_cache
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    base_dir = Path(__file__).resolve().parents[1]
    env_dir = base_dir / "env"
    env_path = env_dir / f".env.{app_env}"

    if env_path.exists():
        return Settings(_env_file=env_path)

    fallback_path = env_dir / ".env"
    if fallback_path.exists():
        return Settings(_env_file=fallback_path)

    return Settings()
