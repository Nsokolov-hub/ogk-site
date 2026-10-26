# ogk-chem-web — витрина ogk-chem.ru

Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · next-intl (RU `/`, EN `/en/`).

Бэкенд сайта — в [backend/](backend/README.md): FastAPI + PostgreSQL + Meilisearch. Каталог, поиск, корзина, импорт прайсов, приём заявок и доставка в «Реактив CRM» (потоки F1 и F5). Витрина берёт все данные каталога из API: моков каталога в коде нет.

Админка — [admin/README.md](admin/README.md): товары, страницы, SEO, импорт, очереди, заявки, настройки (ТЗ 13).

Стейдж и продакшен — [deploy/README.md](deploy/README.md): HTTPS через Caddy, пароль на стейдже, бэкапы с восстановлением на момент времени, мониторинг, нагрузочный тест; обновление — `./scripts/deploy.sh`.

Весь сайт в Docker: `cp .env.example .env && docker compose up -d --build`, затем тестовый каталог `docker compose exec api python -m app.catalog.cli seed` — витрина <http://127.0.0.1:3000>, API <http://127.0.0.1:8001/api/docs>, письма в Mailpit <http://127.0.0.1:8025>. Витрина проксирует `/api/v1/*` на API внутри сети. Для правки витрины с горячей перезагрузкой остановите сервис `web` и запустите `npm run dev` — она пойдёт в API на `API_ORIGIN` (по умолчанию <http://127.0.0.1:8001>).

Связь с CRM, запущенной своим `docker compose` на этом же компьютере: в CRM `docker compose exec api python -m app.integrations.site_tokens create --name local`, значения — в `CRM_TOKEN` и `CRM_SIGNING_SECRET` файла `.env`, `CRM_URL=http://host.docker.internal:8000`, `CRM_DELIVERY_ENABLED=true`, затем `docker compose up -d`.

## Запуск

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production-сборка
npm run lint       # ESLint
npm run typecheck  # TypeScript
npm run api:types  # типы ответов API из backend/openapi.json → src/types/api-schema.d.ts
npm run e2e        # сценарии SC-01…SC-04 на запущенном сайте с тестовым каталогом (PLAYWRIGHT_CHANNEL=chrome — свой Chrome)
NEXT_DIST_DIR=.next-prod npm run build  # проверочная сборка, не мешает запущенному npm run dev
```

Страницы рендерятся на запрос (`dynamic = 'force-dynamic'` в `src/app/[locale]/layout.tsx`), ответы API лежат в Data Cache Next 2–5 минут с тегами (`catalog`, `product:{slug}`…). Воркер API сбрасывает кэш изменённых товаров через `POST /api/revalidate/` (секрет `REVALIDATE_SECRET`). Поэтому сборка не зависит от API и проходит в CI без него.

## Что где

- `src/app/globals.css` — дизайн-токены (цвета, типографика, скругления, брейкпоинты).
- `src/components/ui` — UI-кит: кнопки, поля, бейджи, диалог.
- `src/components/layout` — шапка, мегаменю, мобильное меню, подвал, cookie-баннер.
- `src/components/product` — карточка товара, «В корзину», окно «Заказать в 1 клик».
- `src/components/home` — секции главной; `HeroSearch` — поиск по кат. № и CAS на первом экране.
- `src/components/search/SearchBox.tsx` — строка поиска с подсказками (шапка, главная, 404): товары и группы «Субстанции», «Разделы каталога», «Бренды» (SRCH-01); данные — `GET /api/search/suggest/?q=&lang=`: маршрут Next берёт подсказки из API (Meilisearch) и добавляет SEO-посадочные. Поиск понимает брутто-формулу в порядке Хилла (SRCH-10), русские названия субстанций и неверную раскладку (SRCH-05) — всё это делает бэкенд.
- `src/components/rfq/CartDrawer.tsx` — выдвижная панель корзины (RFQ-01): открывается иконкой в шапке и кнопками «В корзине», без JS ссылка ведёт на `/rfq/`.
- `src/components/catalog` — каталог: фильтры, сортировка, сетка/таблица, пагинация, блоки под сеткой.
- `src/app/[locale]/catalog/[[...slug]]` — `/catalog/`, `/catalog/{раздел}/`, `/catalog/{раздел}/{подраздел}/` и SEO-посадочные из срезов фильтров `/catalog/{раздел}/{подраздел}/{срез}/` (URL-07, создаются в админке, ADM-07; `src/lib/landings.ts`): свои H1, Title и текст, фиксированные фильтры, чипы «Подборки» на родительской категории; индексируются при ≥ 3 позициях.
- `src/lib/backend.ts` — клиент API сайта (на сервере `API_ORIGIN`, в браузере `/api/v1` через прокси); `src/lib/api-types.ts` — схемы из `backend/openapi.json`.
- `src/lib/catalog-api.ts`, `category-page.ts`, `product-api.ts`, `content-api.ts` (бренды), `search.ts`, `sitemap.ts`, `feed.ts` — данные каталога из `/api/v1/public/*`. `src/lib/content.ts` — тексты главной, услуг, статей, решений, авторов и страниц доверия, контакты и реквизиты из `/api/v1/public/pages/*` и `/public/site`: их ведут в админке (ADM-02, ADM-10). `?preview=` — черновик из админки по подписанной ссылке, без кэша и в noindex. `src/lib/redirects.ts` — редиректы из админки в middleware (ADM-07).
- `src/lib/api.ts` → `submitSiteRequest` — отправка всех форм в `POST /api/v1/public/requests/`: ключ повторяемости по содержимому (повтор той же формы не создаёт вторую заявку), SmartCaptcha по ответу 428 (`src/components/forms/CaptchaHost.tsx`), коды ошибок → тексты на языке страницы (`src/lib/submit-error.ts`).
- `src/middleware.ts` + `src/lib/attribution-cookie.ts` — источник визита (ТЗ 15.3): первое и последнее касание, UTM, yclid, gclid в cookie `ogk_attr` на 90 дней; её читает API при отправке заявки.
- `src/lib/catalog.ts` — формат URL фильтров (`?brand=edqm&pack=100-mg&sort=name&page=2`) и порядок значений в фильтрах; фильтрует и считает фасеты API.
- `src/lib/rfq-store.ts` — корзина запроса в localStorage; `src/lib/cart-sync.ts` — её серверная копия по cookie `ogk_cart` на 90 дней (RFQ-01).
- `src/middleware.ts` + `src/lib/csp.ts` — Content-Security-Policy с одноразовым nonce на каждый ответ (NFR-04): скрипты только свои и загруженные ими, поэтому Метрика, GA4 и SmartCaptcha работают без перечня адресов.
- `src/components/analytics/Counters.tsx` — Яндекс Метрика и GA4 (ТЗ 15.1) после согласия на аналитические cookies; номера — `YM_COUNTER_ID` и `GA_MEASUREMENT_ID` при запросе страницы, у стейджа и продакшена свои. `track()` шлёт события ТЗ 15.2 целями Метрики и событиями GA4; поля форм не пишутся Вебвизором (`ym-disable-keys`, NFR-08).
- `src/components/forms/SubscribeForm.tsx` → `POST /api/v1/public/subscriptions/`: адрес с двумя согласиями в базе сайта, письмо со ссылкой отписки, копия в CRM (ТЗ 11.2, NFR-07); `/unsubscribe/?t=` — отписка кнопкой.
- `src/instrumentation.ts` — ошибки серверного рендера в Sentry или GlitchTip по `SENTRY_DSN`, без SDK и без персональных данных.
- `messages/ru.json`, `messages/en.json` — строки интерфейса.
- `src/app/[locale]/product/[slug]` — карточка товара (3 типа: стандарты, оборудование, прочее): идентификаторы с копированием, фасовки и своя фасовка, аналоги, вкладки «Описание» / «Технические данные», документы, «другие примеси субстанции», аналоги других брендов, аксессуары, FAQ, форма с подставленным товаром.
- `src/app/[locale]/substances` — указатель А–Я и `/substances/{мнн}/`: все стандарты и примеси субстанции, выбор нескольких позиций и добавление в корзину одним действием (SC-05).
- `src/app/[locale]/brands`, `services`, `articles`, `authors` — бренды, услуги с формой расчёта (поля задаются на услугу, RFQ-08), 10 статей по темам ТЗ 10.4 и автор.
- `src/app/[locale]/solutions` — отраслевые решения (ТЗ 4.1): контроль качества, лаборатория ВЭЖХ, R&D, микробиология — задачи, разделы каталога, популярные позиции, услуги, статьи, FAQ, заявка.
- `src/app/[locale]/about`, `delivery`, `documents`, `contacts` — страницы доверия с реквизитами из `getSiteSettings()`.
- `src/app/[locale]/rfq` — корзина запроса: строки с фасовкой, количеством, аналогами и комментарием, свободные строки, вставка списка до 200 позиций или файл xlsx/csv (SC-02, `POST /api/v1/public/search/batch` и `/batch/file`), форма RFQ-03 с проверкой ИНН, экран «Спасибо» (RFQ-05).
- `src/app/[locale]/search` — результаты поиска с фильтрами по бренду и разделу; пустая выдача — форма с подставленным запросом (SC-03).
- `src/app/robots.txt`, `src/app/sitemap.xml`, `src/app/sitemaps/[file]` — robots.txt (SEO-03, Clean-param, staging закрыт через `SITE_ENV=staging`) и индекс Sitemap по типам страниц (SEO-04), включая `en-*` для переведённых страниц.
- `src/app/feeds/yandex-direct.yml` — YML-фид для Директа (ТЗ 15.4), обновление раз в 6 часов; позиции и разделы — `GET /api/v1/public/catalog/feed`, состав фида — настройка каталога `feed` в API. Цен в фиде нет — открытый вопрос ТЗ 15.4.
- Подконтрольные вещества (ТЗ 5.2.1) — перечни и автопроверка в API (`backend/app/catalog/controlled.py`): совпавшие позиции скрыты с витрины, из поиска, Sitemap и фида настройкой `hide_controlled`.
- Английские тексты (EN-04) хранятся в API вместе с русскими: у страницы есть версия `en`, только когда она переведена (EN-05); подписи фасовок на английском отдаёт API.

## SEO-слой

- `src/lib/seo.ts` — `pageMetadata()`: canonical на себя без query (URL-09), `?page=N` в canonical только у пагинации (URL-08), noindex для фильтров (URL-06) и неполных карточек (SEO-07). hreflang ru/en/x-default — только у страниц с переводом (`hasEn`); EN-страница без перевода — `noindex, follow` и canonical на русскую (EN-05).
- Уровневая индексация товаров: полнота 0–100 и решение об индексации считает API (`backend/app/catalog/completeness.py`) по критериям ТЗ 5.6, порог 70 — настройка `index_threshold`. Ниже порога — noindex и нет в Sitemap. Субстанции — index при ≥ 3 позициях и тексте.
- JSON-LD (`src/components/seo/JsonLd.tsx`): Organization, WebSite + SearchAction, BreadcrumbList на всех страницах кроме главной, Product без offers, Article, Person, Service, FAQPage только там, где FAQ виден.
- Метатеги товаров и субстанций — по шаблонам ТЗ 10.2; H1/Title категорий и услуг — из ТЗ 10.3.

## Временно

- Шрифт Manrope вместо LT Superior (нужны файлы и веб-лицензия).
- Статьи и «Решения» пока только на русском (P2), их `/en/`-версии в noindex с canonical на русские. Начальные тексты сайта — `backend/seed/content.json` (`seed --content-only`).
- Тестовый каталог для разработки — `backend/seed/catalog.json` (413 позиций, 9 обогащённых карточек; выгружен из прежних моков скриптом `scripts/export-catalog-seed.mjs`). Настоящий ассортимент загружается импортом (backend/README.md); карточки без описания — шаблонный текст и noindex до обогащения.
- Статьи — 10 первых тем ТЗ 10.4; ещё 5 тем публикуются по мере написания, без страниц-заглушек. Отметка «Проверено экспертом» появится после проверки химиком (`reviewed`).
- Страница автора в noindex, пока нет квалификации и фото.
- Не сделаны: личный кабинет (P2), стили печати карточки и корзины (P2).
- Фото товаров нет: в карточках нарисованная банка-заглушка, её заменят фото производителей.

## Дизайн

Визуальный язык — ТЗ 11 (тёмная тема, зелёный акцент, кнопки-«таблетки»). Вёрстка проверена скиллами frontend-design, ui-ux-pro-max и taste-skill: заголовки не длиннее 2 строк (кроме H1 главной из ТЗ 10.3 на телефоне), без надзаголовков, тонких линий и декоративных градиентов, шесть ступеней шрифта, текст не мельче 13 px. Строки с осознанными исключениями помечены `taste-skill-ignore` с причиной.
