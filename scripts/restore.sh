#!/usr/bin/env bash
# Bring the site's database and files back from BACKUP_DIR (TZ 12.3: RTO ≤ 4 h, checked before the launch).
#
#   scripts/restore.sh --force                                   — the latest state the journal holds
#   scripts/restore.sh --time "2026-10-26 14:30:00+03" --force   — the database as it was at that moment
#   scripts/restore.sh --copy 20261026T031500Z --force           — exactly a base copy, without the journal after it
#
# The current database is replaced. The storefront and the API stop for the time of the restore; afterwards the
# search index is rebuilt from the restored database. Make a fresh base copy right after: scripts/backup.sh.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

TIME=""
COPY=""
EXACT=""
FORCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --time) TIME="${2:?}"; shift 2 ;;
    --copy) COPY="${2:?}"; EXACT=1; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) usage ;;
  esac
done
[ -n "$FORCE" ] || { echo "Восстановление заменит текущую базу сайта. Повторите с --force."; exit 1; }

# The base copy: the one named, or the newest one made before the moment asked for.
if [ -z "$COPY" ]; then
  if [ -n "$TIME" ]; then
    limit="$(TZ=UTC0 date -u -d "$TIME" +%Y%m%dT%H%M%SZ 2>/dev/null || true)"
    [ -n "$limit" ] || { echo "Не понял время: $TIME (нужно, например, 2026-10-26 14:30:00+03)"; exit 1; }
    COPY="$(find "$BACKUP_DIR/base" -mindepth 1 -maxdepth 1 -type d -name '20*' -exec basename {} \; | sort \
      | awk -v limit="$limit" '$0 < limit' | tail -n 1)"
  else
    COPY="$(find "$BACKUP_DIR/base" -mindepth 1 -maxdepth 1 -type d -name '20*' -exec basename {} \; | sort | tail -n 1)"
  fi
fi
SOURCE="$BACKUP_DIR/base/$COPY"
[ -n "$COPY" ] && [ -f "$SOURCE/base.tar.gz" ] || { echo "Нет подходящей копии в $BACKUP_DIR/base"; exit 1; }
say "Проверяю копию $COPY"
(cd "$SOURCE" && checksum -c SHA256SUMS >/dev/null)

say "Останавливаю сайт"
compose stop web worker api db

# Recovery settings: the archive is read up to its end, up to the moment asked for, or — a copy named without a
# moment — only up to the point where the copy is consistent. Every way ends on a new timeline, so the journal
# written afterwards never takes the names of segments already in the archive.
RECOVERY="restore_command = 'test -f /backups/wal/%f.gz && gunzip -c /backups/wal/%f.gz > %p'
recovery_target_action = 'promote'"
if [ -n "$TIME" ]; then
  RECOVERY="$RECOVERY
recovery_target_time = '$TIME'"
elif [ -n "$EXACT" ]; then
  RECOVERY="$RECOVERY
recovery_target = 'immediate'"
fi

say "Разворачиваю копию в базу"
compose run --rm --no-deps -T --entrypoint sh db -s <<SCRIPT
set -e
cd /var/lib/postgresql/data
find . -mindepth 1 -delete
tar -xzf /backups/base/$COPY/base.tar.gz -C .
mkdir -p pg_wal
tar -xzf /backups/base/$COPY/pg_wal.tar.gz -C pg_wal
printf '%s\n' "$RECOVERY" >> postgresql.auto.conf
touch recovery.signal
chown -R postgres:postgres .
chmod 700 .
SCRIPT

say "Восстанавливаю базу по журналу"
compose up -d db
for _ in $(seq 1 720); do
  state="$(compose exec -T -u postgres db psql -U site -d site -tAc 'select pg_is_in_recovery()' 2>/dev/null | tr -d '[:space:]' || true)"
  [ "$state" = "f" ] && break
  sleep 5
done
[ "$state" = "f" ] || { echo "База не вышла из восстановления: docker compose logs db"; exit 1; }
compose exec -T -u postgres db psql -U site -d site -q -c 'alter system reset restore_command' \
  -c 'alter system reset recovery_target_time' -c 'alter system reset recovery_target' \
  -c 'alter system reset recovery_target_action' -c 'select pg_reload_conf()' >/dev/null
say "Последняя восстановленная транзакция: $(compose exec -T -u postgres db psql -U site -d site -tAc \
  "select coalesce(to_char(pg_last_xact_replay_timestamp(), 'YYYY-MM-DD HH24:MI:SS TZ'), 'на момент копии')" | tr -d '\r')"

say "Файлы заявок"
compose run --rm --no-deps -T --entrypoint sh api -c 'find /data/files -mindepth 1 -delete && tar -xzf - -C /data/files' \
  < "$SOURCE/files.tar.gz"

say "Запускаю сайт"
compose up -d
say "Перестраиваю поисковый индекс"
compose exec -T api python -m app.catalog.cli reindex
say "Восстановление завершено. Сделайте новую базовую копию: scripts/backup.sh"
