# a_engine (A영역 자동 수집 모듈)

TMDB에서 트렌딩/최신 작품을 수집하고, 한국 OTT(Netflix/Disney+) 가용성 필터 후 B영역 `/generate-post`로 전달하는 모듈입니다.

## 구조

- `app/clients/tmdb_client.py`: TMDB API 호출
- `app/services/collector.py`: 전체 파이프라인 오케스트레이션
- `app/services/dedup_store.py`: SQLite 기반 중복 방지(30일)
- `app/clients/b_engine_client.py`: B영역 API 호출
- `app/main.py`: 1회 실행
- `app/scheduler.py`: 하루 2회 스케줄 실행

## 시작

```bash
cd /Users/seungminsong/Desktop/coding/blog_auto_poster/a_engine
poetry install
cp env/.env.dev.example env/.env.dev
```

필수값:

- `TMDB_API_KEY`
- `B_ENGINE_BASE_URL`
- `B_ENGINE_ADMIN_TOKEN`

## 1회 실행

```bash
APP_ENV=dev poetry run python -m app.main
```

## 스케줄 실행(하루 2회)

```bash
APP_ENV=dev poetry run python -m app.scheduler
```

## B영역 전달 payload

`auto_publish=true`가 기본이므로 생성 후 즉시 워드프레스 발행까지 이어집니다.
