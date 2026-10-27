# Стейдж и продакшен ogk-chem.ru

Один сервер, Docker Compose, снаружи — только Caddy на портах 80 и 443 с сертификатами Let's Encrypt (ТЗ 12.1, 12.3). Стейдж — копия продакшена без персональных данных, закрытая паролем и от индексации.

```
Caddy :443 ── SITE_DOMAIN ──┬─ /api/v1/*  → api (FastAPI) ─┬─ PostgreSQL 17 (+ архив журнала в BACKUP_DIR/wal)
           │                └─ остальное → web (Next.js)    ├─ Meilisearch (индекс строится из базы)
           └─ ADMIN_DOMAIN ─┬─ /api/v1/admin/* → api        └─ Redis (лимиты запросов)
                            └─ админка (статика в образе Caddy)
                                           worker: доставка в CRM, письма, индекс, публикации, импорт, сторож
```

## 1. Сервер

- Ubuntu 24.04, от 4 ядер и 16 ГБ памяти для каталога на 1,7 млн позиций; диск SSD от 100 ГБ: база около 10 ГБ, индекс поиска около 10 ГБ, плюс базовые копии и журнал за `BACKUP_RETENTION_DAYS` дней.
- Docker Engine с Compose 2.24 или новее: `docker compose version`.
- DNS: A-записи `SITE_DOMAIN`, `ADMIN_DOMAIN` (и `SITE_ALIASES` на продакшене) на адрес сервера. Порты 80 и 443 открыты.

```bash
sudo mkdir -p /srv/ogk-site && sudo chown $USER /srv/ogk-site
git clone https://github.com/Nsokolov-hub/ogk-site.git /srv/ogk-site
cd /srv/ogk-site
```

## 2. Настройки

```bash
python3 scripts/init-env.py staging --domain staging.ogk-chem.ru --admin-domain admin-staging.ogk-chem.ru --email it@ogk-chem.ru
```

Скрипт создаёт `.env` из `.env.example`: случайные пароли базы, ключ Meilisearch, общий секрет витрины и API, хеш пароля стейджа (пароль печатается один раз — сохраните его). Дальше вручную:

| Переменная | Что указать |
|---|---|
| `CRM_URL`, `CRM_TOKEN`, `CRM_SIGNING_SECRET`, `CRM_DELIVERY_ENABLED=true` | В CRM: `docker compose exec api python -m app.integrations.site_tokens create --name staging`; адрес сервера сайта — в `SITE_INTEGRATION_ALLOWED_IPS` CRM |
| `CRM_EVENTS_SECRET` (скрипт создаёт), `CRM_EVENTS_ALLOWED_IPS` | События из CRM (F2): в `.env` CRM `SITE_EVENTS_URL=https://<SITE_DOMAIN>/api/v1/crm/events` и `SITE_EVENTS_SECRET` = это значение. Адрес сервера CRM — в `CRM_EVENTS_ALLOWED_IPS`; пароль стейджа этот путь не закрывает, его защищает подпись |
| `METRIKA_OAUTH_TOKEN`, `GA_API_SECRET` | Офлайн-конверсии (F3), см. ниже; пусто — счётчик их не получает |
| `S3_*` | Необязательно. Пусто — файлы (вложения заявок, фото, PDF и 2D-структуры карточек) лежат в томе `files` и входят в бэкап. С S3: приватный бакет, сервисный аккаунт с правами на него, в бакете включите версионирование — `backup.sh` его не копирует. Сайт отдаёт файлы сам по `/api/v1/media/…` |
| `SMTP_*`, `MAIL_FROM` | Продакшен — почтовый провайдер с серверами в РФ. На стейдже письма остаются в Mailpit: `https://<SITE_DOMAIN>/mailpit/` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Чат оповещений: недоставленные заявки, сбои поиска и очереди, ошибки бэкапа |
| `SENTRY_DSN`, `WEB_SENTRY_DSN` | Проект в Sentry или GlitchTip; пусто — ошибки только в журналах |
| `YM_COUNTER_ID`, `GA_MEASUREMENT_ID` | Счётчики Метрики и GA4; у стейджа свои или пусто |
| `PG_SHARED_BUFFERS`, `PG_EFFECTIVE_CACHE_SIZE` | Примерно ¼ и ¾ памяти сервера |
| `BACKUP_SYNC_COMMAND` | Копия бэкапов за пределы сервера, например `rclone sync /srv/ogk-site/backups crypt:ogk-site` (rclone crypt шифрует) |

## 3. Первый запуск

```bash
./scripts/deploy.sh --no-pull --skip-backup
```

Скрипт собирает образы, применяет миграции, поднимает сервисы и ждёт, пока API и витрина ответят. Caddy сам получит сертификаты при первом запросе (DNS `ADMIN_DOMAIN` тоже должен указывать на сервер).

Первый сотрудник админки — пароль печатается один раз, при первом входе админка попросит включить код из приложения:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec api python -m app.admin.cli create-user --email it@ogk-chem.ru --name "Имя Фамилия" --role admin
```

Остальных сотрудников заводят в админке: «Сотрудники». Потерянный телефон или пароль — `reset-totp` и `reset-password` той же команды.

Структура каталога и тексты разделов, брендов, субстанций (без тестовых товаров):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec api python -m app.catalog.cli seed --content-only
```

Выгрузка ассортимента (около 15 минут: 10 — импорт, 5 — индекс), файлы 1.xlsx…5.xlsx положите в `/srv/import`:

```bash
C="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
$C run --rm -v /srv/import:/import:ro api python -m app.catalog.cli import /import/1.xlsx /import/2.xlsx /import/3.xlsx /import/4.xlsx /import/5.xlsx --no-index
$C exec api python -m app.catalog.cli recategorize
$C exec api python -m app.catalog.cli reindex
```

Для стейджа без выгрузки хватит тестового каталога из 413 позиций: `$C exec api python -m app.catalog.cli seed` (на продакшене тестовые товары не грузятся).

## 4. Обновление

```bash
./scripts/deploy.sh
```

`git pull`, сборка новых образов, пока работают старые, базовая копия перед миграциями, перезапуск. Пока контейнер перезапускается, Caddy держит запросы до 30 секунд вместо ошибки 502 — посетители не видят простоя (NFR-02).

## 5. Резервные копии (ТЗ 12.3: RPO ≤ 1 ч, RTO ≤ 4 ч)

- PostgreSQL сам пишет журнал изменений в `BACKUP_DIR/wal` — каждый заполненный сегмент и не реже раза в `ARCHIVE_TIMEOUT` секунд (10 минут).
- `scripts/backup.sh` раз в сутки делает базовую копию базы и файлов заявок, удаляет копии и журнал старше `BACKUP_RETENTION_DAYS` дней (две последние копии остаются всегда), проверяет, что архив журнала пишется, и копирует всё за пределы сервера.
- Индекс Meilisearch не копируется: он перестраивается из базы.

```bash
sudo crontab -e
15 3 * * * /srv/ogk-site/scripts/backup.sh >> /srv/ogk-site/backups/backup.log 2>&1
```

Восстановление:

```bash
./scripts/restore.sh --force                                   # последнее состояние, которое есть в журнале
./scripts/restore.sh --time "2026-10-26 14:30:00+03" --force   # база на этот момент
./scripts/restore.sh --copy 20261026T031500Z --force           # ровно базовая копия
./scripts/backup.sh                                            # сразу после восстановления — новая копия
```

Восстановление проверяется до запуска: на стейдже сделайте копию, измените данные, восстановите на момент до изменения.

## 6. Наблюдение

- `https://<SITE_DOMAIN>/api/v1/health` — 200, если работают база и поиск; его проверяет внешний мониторинг (Яндекс Мониторинг, UptimeRobot) раз в минуту, с оповещением в тот же Telegram.
- Сторож в воркере раз в 5 минут пишет в Telegram: поиск или Redis не отвечают, очередь стоит дольше 30 минут, задачи очереди не выполнены. Недоставленные в CRM заявки — отдельное оповещение через 15 минут (RFQ-07).
- Ошибки API, воркера и серверного рендера витрины — в Sentry, без персональных данных.
- Журналы: `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api worker web`; каждая строка API — JSON с `requestId`.

## 7. Нагрузочный тест (NFR-01)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec api python scripts/load_test.py --base https://<SITE_DOMAIN> --rps 50 --duration 300
```

Смешанный трафик: главная, разделы с фильтрами, карточки, подсказки и страница поиска. Цель ТЗ: 50 запросов в секунду, страница без кэша p95 ≤ 800 мс, API p95 ≤ 300 мс. На стейдже с паролем добавьте `--auth ogk:<пароль>`. Весь тест идёт с одного адреса, поэтому на время теста поднимите лимит поиска на посетителя: `SEARCH_RATE_PER_MINUTE=1000000` в `.env` и `./scripts/deploy.sh --no-pull --skip-backup`, после теста верните.

## Офлайн-конверсии (F3)

Когда заявка с сайта продвигается в CRM, сайт отправляет цель в счётчик того посетителя, который её оставил (по ClientID Метрики и GA4 или yclid из атрибуции заявки; контакты не уходят). Каждая цель — один раз на заявку.

| Событие в CRM | Метрика (цель «JavaScript-событие») | GA4 (событие) |
|---|---|---|
| Сбор квот и дальше | `crm_qualified` | `qualify_lead` |
| КП отправлено | `crm_proposal` | `crm_proposal` |
| Продажа подтверждена (с выручкой) | `crm_sale` | `close_convert_lead` |

Метрика: создайте три цели с этими идентификаторами, в настройках счётчика включите «Офлайн-конверсии», выпустите OAuth-токен пользователя с доступом к счётчику (права `metrika:write`) — в `METRIKA_OAUTH_TOKEN`. GA4: «Администратор → Потоки данных → Секретные ключи Measurement Protocol» — в `GA_API_SECRET`; события отметьте ключевыми. Номера счётчиков — из админки («Счётчики») или `YM_COUNTER_ID`/`GA_MEASUREMENT_ID`. Сбои отправки повторяются очередью, как письма.

## Сайт и CRM на одном сервере

У CRM свой Caddy в `docker-compose.https.yml`, а порты 80 и 443 может занять только один. На общем сервере запускайте CRM без `docker-compose.https.yml`, а её адрес обслуживает Caddy сайта: файл `deploy/caddy/extra/crm.caddy`

```
crm.ogk-chem.ru {
	encode zstd gzip
	header Strict-Transport-Security "max-age=31536000"
	reverse_proxy crm-project-web-1:8080
}
```

и сеть CRM для Caddy сайта — в `docker-compose.override.yml` рядом с `docker-compose.prod.yml`:

```yaml
services:
  caddy:
    networks: [default, crm]
networks:
  crm:
    name: crm-project_default
    external: true
```

Скрипты `deploy.sh`, `backup.sh` и `restore.sh` подключают `docker-compose.override.yml` сами, если он есть.

У CRM сервисы называются так же (`api`, `web`), и в общей сети Caddy может попасть не в тот контейнер. Поэтому на общем сервере в `.env` сайта укажите имена контейнеров сайта:

```
API_UPSTREAM=ogk-site-api-1:8000
WEB_UPSTREAM=ogk-site-web-1:3000
MAILPIT_UPSTREAM=ogk-site-mailpit-1:8025
```

Если CRM открывают по IP-адресу, браузер не передаёт имя сервера, и Caddy должен знать сертификат по умолчанию: добавьте в глобальный блок Caddyfile `default_sni <IP>` (на сервере — своей копией `deploy/Caddyfile.server`, подключённой в `docker-compose.override.yml`).
