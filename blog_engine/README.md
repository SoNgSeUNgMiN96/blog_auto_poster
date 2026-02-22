# blog_engine (B영역 서버)

A영역에서 받은 JSON으로 콘텐츠 생성, SEO 최적화, 이미지 처리, 워드프레스 발행, 색인 요청까지 수행하는 FastAPI 서버입니다.

## 1) 실행 준비 (Poetry)

```bash
cd /Users/seungminsong/Desktop/coding/blog_auto_poster/blog_engine
poetry install
cp env/.env.dev.example env/.env.dev
cp env/.env.prod.example env/.env.prod
```

기본 실행 환경은 `APP_ENV=dev`이며, `env/.env.dev`를 사용합니다.

## 2) MySQL(localhost) 준비

```bash
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS blog_engine_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS blog_engine_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

`env/.env.dev`는 DB 접속 정보를 분리해서 받습니다. 비밀번호는 파일에 쓰지 말고 OS 환경변수로 넣으세요.

```bash
export BLOG_ENGINE_DB_PASSWORD='실제비밀번호@'
export BLOG_ENGINE_OPENAI_API_KEY='sk-...'
```

이때 `env/.env.dev`는 아래처럼 유지합니다.

```env
DB_DRIVER=mysql+pymysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=blog_engine_dev
DB_USER=root
DB_PASSWORD=
DB_PASSWORD_ENV=BLOG_ENGINE_DB_PASSWORD
DB_CHARSET=utf8mb4
```

## 3) DB 마이그레이션

```bash
APP_ENV=dev poetry run alembic -c alembic.ini upgrade head
```

`AUTO_CREATE_TABLES=true`인 경우 서버 시작 시 `posts`, `images` 테이블이 자동 생성됩니다.
다만 DB 계정 인증이 실패하면 자동 생성도 실행되지 않습니다.

## 4) 서버 실행

```bash
APP_ENV=dev poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5) API

- `POST /generate-post`
- `POST /publish/{post_id}`
- `GET /status/{post_id}`
- `GET /health`

`API_ADMIN_TOKEN`이 설정된 경우 `x-admin-token` 헤더가 필요합니다.

## 6) 환경 파일 구조

- 개발: `env/.env.dev`
- 운영: `env/.env.prod`
- 샘플: `env/.env.dev.example`, `env/.env.prod.example`

`APP_ENV=dev|prod` 값에 따라 자동으로 해당 파일을 읽습니다.

## 7) .env에서 먼저 채울 값(우선순위)

1. `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`
2. `DB_PASSWORD_ENV` 이름 확인 후, OS 환경변수에 실제 비밀번호 등록
3. `API_ADMIN_TOKEN` (API 보호용 토큰)
4. `OPENAI_API_KEY_ENV` 이름 확인 후, OS 환경변수에 OpenAI 키 등록
5. `WORDPRESS_BASE_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` (발행 기능 사용 시)
6. `GOOGLE_SERVICE_ACCOUNT_FILE` (Google 색인 사용 시)
- 이미지 최적화: `IMAGE_MAX_WIDTH`, `IMAGE_MAX_HEIGHT`, `IMAGE_WEBP_QUALITY`, `IMAGE_KEEP_ORIGINAL`

카테고리 자동 지정:
- `WORDPRESS_CATEGORY_MAP=ott:OTT 리뷰,it:IT 리뷰` 형식으로 매핑
- `WORDPRESS_DEFAULT_CATEGORY`를 지정하면 모든 글에 고정 카테고리 적용

로컬 WordPress를 별도 폴더로 운영하려면 `/Users/seungminsong/Desktop/coding/blog_auto_poster/wordpress_stack/README.md` 절차를 먼저 실행하세요.
(`WORDPRESS_DB_PASSWORD`, `WORDPRESS_ADMIN_PASSWORD`는 wordpress_stack에서 셸 환경변수로만 주입)

## 요청 예시: /generate-post

```json
{
  "content_type": "ott",
  "prompt_template": "{title}에 대한 심층 리뷰 글을 작성해줘.",
  "prompt_variables": {
    "title": "샘플 영화"
  },
  "images": [
    {"url": "https://example.com/image.jpg", "type": "poster"}
  ],
  "render_template": "ott_review.html",
  "system_role": "당신은 구조화된 JSON만 반환하는 리뷰 작성자다.",
  "auto_publish": true
}
```

`auto_publish=true`면 generate 직후 WordPress 발행까지 한 번에 수행합니다.
