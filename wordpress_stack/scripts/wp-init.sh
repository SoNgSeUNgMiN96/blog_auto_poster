#!/usr/bin/env bash
set -euo pipefail

cd /var/www/html

required_vars=(
  WORDPRESS_URL
  WORDPRESS_TITLE
  WORDPRESS_ADMIN_USER
  WORDPRESS_ADMIN_PASSWORD
  WORDPRESS_ADMIN_EMAIL
)
for v in "${required_vars[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "[wp-init] missing required env: ${v}" >&2
    exit 1
  fi
done

if ! wp core is-installed --allow-root >/dev/null 2>&1; then
  echo "[wp-init] waiting for wordpress files and db..."
  sleep 8

  wp core install \
    --allow-root \
    --url="${WORDPRESS_URL}" \
    --title="${WORDPRESS_TITLE}" \
    --admin_user="${WORDPRESS_ADMIN_USER}" \
    --admin_password="${WORDPRESS_ADMIN_PASSWORD}" \
    --admin_email="${WORDPRESS_ADMIN_EMAIL}" \
    --skip-email
  echo "[wp-init] core install completed"
else
  echo "[wp-init] wordpress already installed, skipping"
fi
