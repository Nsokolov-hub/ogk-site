#!/usr/bin/env bash
# Daily base copy of the site's database and files (TZ 12.3, NFR-13). Cron on the server, as root:
#   15 3 * * * /srv/ogk-site/scripts/backup.sh >> /srv/ogk-site/backups/backup.log 2>&1
#
# PostgreSQL itself archives its journal into BACKUP_DIR/wal at least every ARCHIVE_TIMEOUT seconds
# (docker-compose.prod.yml); with the base copies it brings the database back to any moment of the last
# BACKUP_RETENTION_DAYS days: scripts/restore.sh. The search index is not copied, it is rebuilt from the database.
# BACKUP_SYNC_COMMAND (e.g. «rclone sync /srv/ogk-site/backups crypt-remote:ogk-site») copies everything off the server.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

RETENTION_DAYS="$(env_value BACKUP_RETENTION_DAYS 7)"
SYNC_COMMAND="$(env_value BACKUP_SYNC_COMMAND)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$BACKUP_DIR/base/$STAMP"

trap 'say "Ошибка резервного копирования"; notify "резервная копия $STAMP не создана, см. backups/backup.log"' ERR

mkdir -p "$BACKUP_DIR/base"
say "Копия базы $STAMP"
# Inside the database container BACKUP_DIR is /backups. -X stream adds the journal of the copy itself, so the
# copy is consistent even without the archive.
compose exec -T -u postgres db pg_basebackup -U site -D "/backups/base/$STAMP" -Ft -z -X stream -c fast \
  -l "ogk-site $STAMP"

say "Файлы заявок"
compose exec -T api tar -C /data/files -czf - . > "$TARGET/files.tar.gz"

# The first journal segment the copy needs: older segments are dropped together with older copies.
tar -xzOf "$TARGET/base.tar.gz" backup_label | sed -n 's/.*(file \([0-9A-F]\{24\}\)).*/\1/p' > "$TARGET/wal_start"
[ -s "$TARGET/wal_start" ]
(cd "$TARGET" && checksum base.tar.gz pg_wal.tar.gz files.tar.gz > SHA256SUMS)
say "Готово: $(du -sh "$TARGET" | cut -f1)"

# Copies older than RETENTION_DAYS go, but the two newest always stay.
limit="$(date -u -d "-${RETENTION_DAYS} days" +%Y%m%dT%H%M%SZ 2>/dev/null || date -u -v-"${RETENTION_DAYS}"d +%Y%m%dT%H%M%SZ)"
find "$BACKUP_DIR/base" -mindepth 1 -maxdepth 1 -type d -name '20*' | sort | sed '$d' | sed '$d' | while IFS= read -r copy; do
  if [[ "$(basename "$copy")" < "$limit" ]]; then
    say "Удаляю старую копию $(basename "$copy")"
    rm -rf "$copy"
  fi
done

# Journal segments older than the oldest kept copy are not needed any more; timeline histories always stay.
oldest="$(find "$BACKUP_DIR/base" -mindepth 1 -maxdepth 1 -type d -name '20*' | sort | head -n 1)"
if [ -n "$oldest" ] && [ -s "$oldest/wal_start" ]; then
  start="$(cat "$oldest/wal_start")"
  find "$BACKUP_DIR/wal" -maxdepth 1 -type f -name '[0-9A-F]*' | while IFS= read -r file; do
    name="$(basename "$file")"
    # Segments only (24 hex digits); timeline histories like 00000002.history.gz stay.
    if [[ "$name" =~ ^[0-9A-F]{24} ]] && [[ "${name:0:24}" < "$start" ]]; then rm -f "$file"; fi
  done
fi

# The archive must keep up: a failing archive_command means the moments since the last copy are not protected.
failed="$(compose exec -T -u postgres db psql -U site -d site -tAc \
  "select failed_count from pg_stat_archiver where last_failed_time > coalesce(last_archived_time, 'epoch')" | tr -d '[:space:]')"
if [ -n "$failed" ]; then
  say "Внимание: архив журнала не пишется"
  notify "архив журнала PostgreSQL не пишется, проверьте место на диске и backups/wal"
fi

if [ -n "$SYNC_COMMAND" ]; then
  say "Копирую за пределы сервера"
  sh -c "$SYNC_COMMAND"
fi
say "Резервное копирование завершено"
