==============================
A영역 – Netflix 자동 수집 모듈 상세 설계서 (v1.0)
==============================

이 문서는 B영역이 완성되어 있다는 전제 하에, "한국 OTT 시청 가능 작품을 자동 수집하여 B영역으로 전달하는 A영역 설계"를 정의한다.

핵심 목표:

- 최신 또는 트렌딩 작품 탐색
- 한국 Netflix/Disney+ 시청 가능 여부 필터링
- 포스터 / 줄거리 / 스틸컷 수집
- B영역 계약(JSON) 형태로 정규화
- B영역 /generate-post 호출

1. 전체 아키텍처

[트렌드 수집기] ↓ [메타데이터 수집기] ↓ [한국 OTT 가용성 필터] ↓ [이미지 수집기] ↓ [정규화 레이어] ↓ [B영역 API 호출]

2. 작품 탐색 전략

IMDb 단독 사용은 한계가 있으므로 다음 조합 권장:

1) TMDB API (Primary)
2) JustWatch 비공식 API 또는 RapidAPI 기반 OTT 가용성 확인
3) IMDb는 보조 정보(평점, 추가 메타데이터)

TMDB 장점:

- 공식 API 제공
- 포스터/백드롭 고해상도 제공
- 장르/개봉연도 필터 가능
- 트렌딩 API 존재

3. 최신 작품 수집 전략

전략 A – 트렌딩 기준

- TMDB API: /trending/tv/week /trending/movie/week

전략 B – 최신 공개일 기준

- /discover/tv
  - sort_by=first_air_date.desc
  - region=KR
- /discover/movie
  - sort_by=release_date.desc
  - region=KR

4. 한국 OTT 시청 가능 여부 필터

필수 단계.

- TMDB API: /watch/providers
- 응답에서 "KR" region 확인
- Netflix / Disney+ 포함 여부 필터

5. 이미지 수집 전략

1) 포스터
- TMDB: poster_path

2) 스틸컷
- /images endpoint backdrops 사용

최소 수집 개수:
- poster 1
- still 2~4

원본 URL 구성:
- https://image.tmdb.org/t/p/original/{poster_path}

6. 줄거리 및 메타데이터 수집

TMDB detail endpoint: /movie/{id} /tv/{id}

수집 필드:
- title
- overview
- vote_average
- genres
- first_air_date or release_date
- original_language

7. A영역 → B영역 계약 구조

B영역 입력 포맷:

{
  "content_type": "ott",
  "prompt_template": "string",
  "prompt_variables": {
    "title": "",
    "overview": "",
    "rating": "",
    "genres": "",
    "year": ""
  },
  "images": [
    {"url": "", "type": "poster"},
    {"url": "", "type": "still"}
  ],
  "render_template": "generic_review"
}

8. 프롬프트 설계 전략 (A영역 책임)

A영역은 도메인 전략을 담은 프롬프트를 구성한다.

9. 중복 방지 전략

DB 또는 Redis 사용:

- 이미 발행된 TMDB id 저장
- 30일 이내 중복 게시 방지

10. 자동 실행 전략

- APScheduler 또는 Cron
- 하루 2회 실행
- 매번 3개 작품 수집

11. 실패 대응 설계

- TMDB API 실패 → 재시도
- 이미지 없음 → fallback 이미지 사용
- B영역 실패 → 재큐잉

12. 최종 데이터 흐름 예시

- 트렌딩 10개 수집
- KR OTT 필터
- 상위 3개 선택
- 이미지 수집
- 프롬프트 생성
- B영역 /generate-post 호출
- 성공 시 publish 호출

13. 향후 확장

- 조회수 기반 리포스트
- 특정 장르 집중 전략
- 배우 이름 기반 키워드 강화
- 유튜브 트렌딩 연동

현재 A영역 Netflix 모듈 버전: v1.0
