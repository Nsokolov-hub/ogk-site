# Бэкенд сайта ogk-chem.ru

FastAPI + SQLAlchemy 2 + PostgreSQL 17, тот же стек и те же приёмы, что в «Реактив CRM». Сейчас здесь приём заявок с форм сайта и их доставка в CRM (поток F1, ТЗ 7 и 9).

## Как идёт заявка

1. Витрина отправляет `POST /api/v1/public/requests`: `multipart/form-data` с JSON формы в части `payload` и необязательным файлом в части `attachment`, заголовок `Idempotency-Key` — UUID отправки.
2. API проверяет поля, как формы (ИНН с контрольной суммой, телефон E.164, согласие), вложение (XLSX, CSV, PDF, DOCX до 10 МБ, тип — по содержимому) и антиспам (скрытое поле, время заполнения, лимиты по адресу, SmartCaptcha только при подозрении).
3. В одной транзакции сохраняются заявка с номером `S-2026-000123`, позиции, вложение, источник визита (cookie `ogk_attr`, `_ym_uid`, `_ga`) и три задачи outbox: доставка в CRM, письмо клиенту, письмо на order@. Ответ клиенту уходит только после фиксации.
4. Worker (`python -m app.outbox.worker`) доставляет заявку в CRM: подпись HMAC, `Idempotency-Key` = id заявки, повторы через 1, 5, 15, 60 минут и дальше раз в час до 24 часов. Каждая попытка пишется в `delivery_attempts`.
5. Заявка не в CRM через 15 минут — алерт в Telegram (только номер и ошибка) и письмо на `ALERT_EMAILS` с полным составом. CRM отклонила заявку (400, 409, 422) — алерт сразу, повторы прекращаются; 401 или 403 — алерт сразу, повторы продолжаются.

| Ответ CRM | Что делает сайт |
|---|---|
| 200, 201 | Заявка доставлена, сохраняются id и номер CRM |
| Таймаут, сеть, 5xx, 429 | Повтор по расписанию |
| 401, 403 | Алерт сразу, повторы продолжаются |
| 400, 404, 409, 413, 422 | Алерт сразу, статус `failed`, переотправка вручную |

Пока `CRM_DELIVERY_ENABLED=false`, заявки копятся в очереди, а отдел продаж получает их письмом. Когда доставку включат, очередь уйдёт в CRM сама.

## Запуск для разработки

```bash
cp .env.example .env
docker compose up -d --build
npm run dev
```

API — <http://127.0.0.1:8001/api/docs>, письма — <http://127.0.0.1:8025>. Витрина проксирует `/api/v1/*` на `API_ORIGIN`.

Без Docker:

```bash
cd backend
uv venv .venv --python 3.13 && VIRTUAL_ENV=.venv uv pip install -r requirements-dev.lock
DATABASE_URL=postgresql+psycopg://… .venv/bin/alembic upgrade head
DATABASE_URL=… .venv/bin/uvicorn app.main:app --port 8001
DATABASE_URL=… .venv/bin/python -m app.outbox.worker
```

## Проверки

```bash
cd backend
.venv/bin/ruff check . && .venv/bin/mypy app tests
DATABASE_URL=sqlite:// .venv/bin/pytest -q
TEST_DATABASE_URL=postgresql+psycopg://… DATABASE_URL=sqlite:// .venv/bin/pytest -q
```

Тест `tests/test_contract.py` проверяет тело, которое сайт отправляет в CRM, по схеме из `contracts/crm-f1.json`. Схема закреплена из `docs/openapi.json` CRM. Если CRM намеренно меняет контракт, перезакрепите её:

```bash
python3 backend/scripts/pin_crm_contract.py ../my-crm-project/docs/openapi.json
```

## Эксплуатация

```bash
docker compose exec api python -m app.cli status        # сводка по статусам и очереди
docker compose exec api python -m app.cli undelivered   # заявки, которых нет в CRM
docker compose exec api python -m app.cli resend S-2026-000123
```

Подключение к CRM: в CRM выпустите токен (`python -m app.integrations.site_tokens create --name production`), впишите адрес сервера сайта в `SITE_INTEGRATION_ALLOWED_IPS` CRM, а здесь заполните `CRM_URL`, `CRM_TOKEN`, `CRM_SIGNING_SECRET` и включите `CRM_DELIVERY_ENABLED=true`. Подробно — `docs/site-integration.md` в репозитории CRM.

После изменения зависимостей в `pyproject.toml`:

```bash
uv pip compile pyproject.toml -o requirements.lock
uv pip compile pyproject.toml --group dev -o requirements-dev.lock
```

## Что дальше

- Журнал заявок с повторной отправкой — в админке (ADM-08); пока его заменяет `app.cli`.
- События CRM → сайт (F2) и офлайн-конверсии (F3).
- Серверная копия корзины по анонимной cookie (RFQ-01), S3 для файлов, ClamAV на стороне сайта.
