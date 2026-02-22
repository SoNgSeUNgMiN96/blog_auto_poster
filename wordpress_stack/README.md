# wordpress_stack

`blog_engine`와 분리된 로컬 WordPress 운영 폴더입니다.
로컬 HTTP 환경에서도 Application Password를 쓸 수 있도록 `mu-plugins/allow-app-passwords-local.php`를 마운트합니다.

큐 기반 운영에서도 WordPress는 독립적으로 유지되며, `blog_engine` 워커가 발행 시점에만 접근합니다.

## 1) 준비

```bash
cd /Users/seungminsong/Desktop/coding/blog_auto_poster/wordpress_stack
cp .env.example .env
```

기존 서버와 같은 MySQL 인스턴스를 사용합니다. (별도 DB 컨테이너 없음)
워드프레스용 DB는 기존 MySQL 안에 하나만 추가 생성하세요.

```bash
mysql -h 127.0.0.1 -P 3306 -uroot -p -e "CREATE DATABASE IF NOT EXISTS wordpress CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

비밀번호는 파일에 쓰지 말고 셸 환경변수로만 주입합니다.

```bash
export WORDPRESS_DB_PASSWORD='mysql비밀번호@'
export WORDPRESS_ADMIN_PASSWORD='wp관리자비밀번호@'
```

## 2) 컨테이너 실행

```bash
docker compose up -d wordpress
```

이미 실행 중이었다면 플러그인 반영을 위해 재생성:

```bash
docker compose up -d --force-recreate wordpress
```

브라우저에서 `http://127.0.0.1:8081` 접속 후 설치를 진행하거나, 자동 설치를 원하면 아래를 실행합니다.

```bash
docker compose --profile tools run --rm wpcli
```

## 3) blog_engine 연동용 Application Password 발급

아래 명령으로 워드프레스 admin 계정의 App Password를 발급하세요.

```bash
docker compose --profile tools run --rm wpcli \
  wp user application-password create admin blog-engine --porcelain --allow-root
```

출력된 값을 `blog_engine/env/.env.dev`의 `WORDPRESS_APP_PASSWORD`에 넣습니다.

## 4) blog_engine .env.dev 권장값

```env
WORDPRESS_BASE_URL=http://127.0.0.1:8081
WORDPRESS_USERNAME=admin
WORDPRESS_APP_PASSWORD=<발급된 App Password>
WORDPRESS_DEFAULT_STATUS=draft
```

## 5) 중지/삭제

```bash
docker compose down
```

데이터까지 초기화하려면:

```bash
docker compose down -v
```
