#!/usr/bin/env bash
# Update staging or production to the current commit (NFR-02: no visible downtime).
#
#   scripts/deploy.sh                 — git pull, build, base copy, migrations, restart, health check
#   scripts/deploy.sh --no-pull       — the code already on the server
#   scripts/deploy.sh --skip-backup   — without the base copy before the migrations (first start, staging)
#
# Images are built while the old containers keep serving; Caddy holds requests while a container restarts.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

PULL=1
BACKUP=1
for arg in "$@"; do
  case "$arg" in
    --no-pull) PULL="" ;;
    --skip-backup) BACKUP="" ;;
    *) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
  esac
done

[ -f .env ] || { echo "Нет .env: python3 scripts/init-env.py staging (deploy/README.md)"; exit 1; }
trap 'say "Обновление прервано"; notify "обновление сайта прервано, см. журнал деплоя"' ERR

if [ -n "$PULL" ]; then
  say "Код: git pull"
  git pull --ff-only
fi
say "Версия $(git rev-parse --short HEAD): сборка образов"
compose build --pull

if [ -n "$BACKUP" ] && [ -n "$(compose ps --status running -q db 2>/dev/null)" ]; then
  say "Базовая копия перед миграциями"
  ./scripts/backup.sh
fi

say "Миграции и перезапуск"
compose up -d --remove-orphans

say "Проверка"
for _ in $(seq 1 60); do
  if compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready')" 2>/dev/null \
    && compose exec -T web wget -q -O /dev/null http://127.0.0.1:3000/ 2>/dev/null; then
    say "Сайт работает: $(git rev-parse --short HEAD)"
    docker image prune -f >/dev/null
    exit 0
  fi
  sleep 5
done
say "Сайт не ответил за 5 минут: docker compose logs api web"
notify "после обновления сайт не отвечает"
exit 1
