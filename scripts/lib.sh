# Shared by deploy.sh, backup.sh and restore.sh. Values are read from .env without running it as a script:
# .env may hold strings like «ОГК-ХИМ <noreply@…>» that a shell would take for redirections.

cd "$(dirname "${BASH_SOURCE[0]}")/.."

env_value() {
  local key="$1" default="${2:-}" line value
  line="$(grep -E "^${key}=" .env 2>/dev/null | tail -n 1 || true)"
  value="${line#*=}"
  value="${value%\"}"; value="${value#\"}"
  value="${value%\'}"; value="${value#\'}"
  if [ -z "$line" ] || [ -z "$value" ]; then value="$default"; fi
  printf '%s' "$value"
}

compose() {
  # docker-compose.override.yml — local additions of this server (e.g. the CRM network, deploy/README.md).
  if [ -f docker-compose.override.yml ]; then
    docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.override.yml "$@"
  else
    docker compose -f docker-compose.yml -f docker-compose.prod.yml "$@"
  fi
}

BACKUP_DIR="$(env_value BACKUP_DIR ./backups)"

checksum() {
  if command -v sha256sum >/dev/null; then sha256sum "$@"; else shasum -a 256 "$@"; fi
}

say() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

# A short alert to the site's Telegram chat, without personal data (the same bot as undelivered requests).
notify() {
  local token chat
  token="$(env_value TELEGRAM_BOT_TOKEN)"
  chat="$(env_value TELEGRAM_CHAT_ID)"
  if [ -n "$token" ] && [ -n "$chat" ]; then
    curl -fsS -m 10 -o /dev/null "https://api.telegram.org/bot${token}/sendMessage" \
      --data-urlencode "chat_id=${chat}" --data-urlencode "text=ogk-chem.ru ($(env_value SITE_ENV)): $1" || true
  fi
}
