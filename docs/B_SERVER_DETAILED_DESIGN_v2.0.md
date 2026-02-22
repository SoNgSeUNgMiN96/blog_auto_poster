# OTT 리뷰 블로그 자동화 프로젝트

# B영역 서버단 상세 설계서 (v2.3 – Implementation Ready)

---

# 0. 목표

이 문서는 "콘텐츠 생성 + SEO 최적화 + 워드프레스 발행"을 담당하는
B영역 서버를 실제로 구현하기 위한 기술 설계 문서이다.

목표:

- A영역에서 JSON 수신
- 리뷰 콘텐츠 완성 생성
- SEO 최적화 처리
- 이미지 처리 및 업로드
- WordPress 자동 발행
- 색인 요청 자동화

---

# 1. 전체 기술 스택 확정

## 서버 환경

- Ubuntu 22.04 LTS
- Python 3.11

## 프레임워크

- FastAPI
- Uvicorn

## 패키지 관리

- Poetry

## DB

- MySQL (개발/운영)
- SQLAlchemy ORM
- Alembic (마이그레이션)

## AI

- OpenAI API

## 이미지 처리

- Pillow
- requests (이미지 다운로드)

## HTML 템플릿

- Jinja2

## 워드프레스 연동

- WordPress REST API
- Application Password 인증
- 로컬 개발 시 Docker Compose 기반 별도 스택(`wordpress_stack/`) 운영

## 색인 자동화

- Google Indexing API
- 네이버 RSS Ping

---

# 2. 프로젝트 디렉토리 구조

```text
blog_engine/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── models/
│   │   ├── post.py
│   │   └── image.py
│   │
│   ├── schemas/
│   │   ├── request.py
│   │   └── response.py
│   │
│   ├── services/
│   │   ├── content_generator.py
│   │   ├── seo_engine.py
│   │   ├── image_engine.py
│   │   ├── html_renderer.py
│   │   ├── wordpress_publisher.py
│   │   └── indexing_service.py
│   │
│   └── templates/
│       └── ott_review.html
│
├── alembic/
├── pyproject.toml
└── env/
    ├── .env.dev
    └── .env.prod
```

---

# 3. 데이터베이스 설계

## posts

- id (PK)
- raw_input (JSON)
- generated_content (JSON)
- seo_title
- meta_description
- slug
- status (draft/generated/published/failed)
- wp_post_id
- created_at
- published_at

## images

- id
- post_id (FK)
- original_url
- local_path
- wp_media_id
- order

---

# 4. API 설계

## POST /generate-post

입력: A영역 JSON
동작:

1. DB 저장 (status=draft)
2. Content Generator 실행
3. SEO Engine 실행
4. 이미지 다운로드 및 저장
5. HTML 생성
6. DB 업데이트 (status=generated)

옵션:
- `auto_publish=true` 전달 시 생성 직후 WordPress 발행까지 연속 수행

응답:

```json
{
  "post_id": 1,
  "status": "generated"
}
```

## POST /publish/{post_id}

동작:

1. WordPress 이미지 업로드
2. WordPress 글 업로드
3. DB status=published
4. 색인 요청

## GET /status/{post_id}

처리 상태 반환

---

# 5. Content Generator 설계 (완전 비의존 구조)

핵심 원칙:

- B영역은 OTT, Netflix, IMDb 등 어떤 도메인에도 의존하지 않는다.
- 도메인 지식은 전부 A영역에서 결정한다.

B영역 책임:

- 입력 JSON 기반 콘텐츠 확장
- 입력으로 전달된 프롬프트 템플릿 사용
- 구조화된 출력 생성

입력 계약:

```json
{
  "content_type": "string",
  "prompt_template": "string",
  "prompt_variables": {},
  "images": [{ "url": "", "type": "" }],
  "render_template": "template_name"
}
```

출력 계약:

```json
{
  "title": "",
  "sections": [
    {"heading": "", "content": ""}
  ],
  "tags": [],
  "meta_description": ""
}
```

---

# 6. SEO Engine (도메인 비의존)

- 입력 title 기반 키워드 추출
- tags 정리
- slug 생성 (python-slugify)
- meta_description 길이 검증 (120~160자)

---

# 7. 이미지 처리 파이프라인

1. 이미지 URL 다운로드
2. 로컬 저장
3. WebP 변환
4. 썸네일 생성 (선택)
5. DB 기록

파일 저장 구조:

```text
/media/{year}/{post_id}/
```

---

# 8. HTML 렌더링

Jinja2 템플릿 사용.

---

# 9. WordPress Publisher

- 인증: Application Password (Basic)
- 이미지 업로드: `POST /wp-json/wp/v2/media`
- 글 발행: `POST /wp-json/wp/v2/posts`

---

# 10. 색인 자동화

- Google Indexing API
- 네이버 RSS Ping

---

# 11. 비동기 처리 전략

- 초기: FastAPI BackgroundTasks
- 확장: Redis + Celery

---

# 12. 보안 설계

- `env/.env.dev`, `env/.env.prod` 기반 시크릿 분리 관리
- 관리자 토큰 보호
- Rate limit

---

# 13. 향후 확장 설계

`content_type` 기반 템플릿 분기, 코어 로직 재사용.

---

# 14. 구현 순서

1. FastAPI 기본 서버 구축
2. DB 모델 생성 + Alembic
3. Content Generator 연결
4. HTML 렌더링
5. WordPress 발행 테스트
6. 이미지 업로드 연동
7. 색인 API 연동
8. 비동기 처리 추가

---

현재 버전: v2.3
