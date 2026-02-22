# ott_gen

A영역 대체 모듈입니다.

핵심 기능:
- TMDB 소스 파싱 후 글감 큐 저장(바로 포스팅 안 함)
- 최신 소스는 하루 1회 우선 수집 + 이후 실행은 백필 페이지 커서로 과거/인기작 누적 수집
- 하루 생성 제한(`DAILY_GENERATE_LIMIT`, 기본 3건)
- 스케줄 기반 자동 생성(줄거리 200자 이상 대상 + 생성 전 보강)
- 웹 대시보드에서 글감 미리보기 + 수동 생성 버튼
- 줄거리 보강은 웹 개별 생성과 스케줄 배치 생성 모두에서 수행 가능
- 이미지 URL 중복 제거(동일 still 자동 필터)
- 대시보드 목록 페이지네이션(Queued/Generated/Failed 전환 가능)
- LangChain(Tavily) 검색 기반 보강 + 선택적으로 AI 요약(`ENRICH_AI_SUMMARY=true`)
- 생성 완료 항목은 `생성됨`으로 고정되어 중복 생성되지 않음
- DB 큐 직적재 모드(`B_ENGINE_SUBMIT_MODE=db_queue`) 지원: B엔진 API 서버 없이 blog_engine DB에 바로 적재
- 재생성하려면 웹에서 `플래그 해제` 후 다시 생성

## 큐 기반 운영 요약

1. `ott_gen` 스케줄러가 TMDB 파싱 + 줄거리 보강 + blog_engine DB 큐 적재
2. `blog_engine`은 API 서버 없이 워커(`python -m app.worker`)만 1시간 주기로 실행
3. `ott_gen` 웹 대시보드는 필요할 때만 켜서 점검/수동생성 후 종료

## 0) 초기 설정

```bash
cd /Users/seungminsong/Desktop/coding/blog_auto_poster/ott_gen
poetry install
cp env/.env.dev.example env/.env.dev
```

필수 값:
- `TMDB_API_KEY=...`
- `B_ENGINE_SUBMIT_MODE=db_queue`
- `B_ENGINE_DB_HOST/PORT/NAME/USER`
- `B_ENGINE_DB_PASSWORD_ENV=BLOG_ENGINE_DB_PASSWORD`

```bash
export BLOG_ENGINE_DB_PASSWORD='mysql비밀번호'
```

## 1) 수동 1회 배치(파싱+큐적재)

```bash
APP_ENV=dev poetry run python -m app.main
```

## 2) 상시 자동 배치(권장)

```bash
APP_ENV=dev poetry run python -m app.scheduler
```

동작:
- `PARSE_HOUR`:`PARSE_MINUTE` 하루 1회: 소스 파싱(최신 1회 + 백필 페이지 진행)
- `PUBLISH_HOURS` + `PUBLISH_MINUTE`: 남은 일일 한도 내에서 생성 요청을 blog_engine DB 큐로 적재

## 3) 웹 대시보드 (필요할 때만 ON/OFF)

켜기:

```bash
APP_ENV=dev poetry run python -m app.web.run
```

접속:
- `http://127.0.0.1:8010`

화면에서:
- 소스 파싱 실행
- 오늘 남은 수량만 생성
- 개별 글감 생성 버튼

끄기:
- 실행 터미널에서 `Ctrl + C`
- 스케줄러와 별도 프로세스이므로 대시보드만 종료 가능

## 주요 환경값

- `DAILY_GENERATE_LIMIT=3`
- `PUBLISH_HOURS=10,15,21`
- `PUBLISH_MINUTE=0`
- `PARSE_HOUR=9`
- `PARSE_MINUTE=5`
- `RUN_MODE=hybrid`
- `CANDIDATE_PAGES=2`
- `LATEST_DAILY_PAGES=1` (최신 일일 수집 페이지 수)
- `BACKFILL_PAGES_PER_RUN=3` (파싱 1회당 백필 페이지 진행 수)
- `BACKFILL_SORT_BY=popularity.desc` (예: `popularity.desc`, `release_date.desc`)
- `ENRICH_OVERVIEW=true`
- `OVERVIEW_MIN_LENGTH=120`
- `SCHEDULER_MIN_OVERVIEW_LENGTH=200`
- `SCHEDULER_ENRICH_OVERVIEW=true`
- `ENRICH_SEARCH_MAX_SNIPPETS=5`
- `ENRICH_AI_SUMMARY=true`
- `ENRICH_TAVILY_API_KEY=` (또는 `TAVILY_API_KEY`)
- `ENRICH_TAVILY_API_KEY_ENV=TAVILY_API_KEY`
- `PROMPT_TEMPLATE`에서 `{overview_context}`, `{original_overview}`, `{enriched_overview}` 활용 가능
- `B_ENGINE_SUBMIT_MODE=db_queue|api` (`db_queue` 권장)
- `B_ENGINE_DB_*` (db_queue 모드에서 blog_engine MySQL 접속값)

## 권장 운영(프로세스 최소화)

1. 상시: `ott_gen` 스케줄러만 실행
2. 필요 시: `ott_gen` 대시보드 수동 실행 후 종료
3. 상시 API 서버 없이: `blog_engine` 워커만 cron으로 1시간 주기 실행

## 모듈 이름 변경

기존 `a_engine`은 유지되지만, 앞으로는 `ott_gen`을 사용하세요.
