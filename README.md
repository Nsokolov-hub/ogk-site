# ogk-chem-web — витрина ogk-chem.ru

Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · next-intl (RU `/`, EN `/en/`).

## Запуск

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production-сборка
npm run lint       # ESLint
npm run typecheck  # TypeScript
NEXT_DIST_DIR=.next-prod npm run build  # проверочная сборка, не мешает запущенному npm run dev
```

## Что где

- `src/app/globals.css` — дизайн-токены (цвета, типографика, скругления, брейкпоинты).
- `src/components/ui` — UI-кит: кнопки, поля, бейджи, диалог.
- `src/components/layout` — шапка, мегаменю, мобильное меню, подвал, cookie-баннер.
- `src/components/product` — карточка товара, «В корзину», окно «Заказать в 1 клик».
- `src/components/home` — секции главной; `HeroSearch` — поиск по кат. № и CAS на первом экране.
- `src/components/search/SearchBox.tsx` — строка поиска с подсказками (шапка, главная, 404); данные — `GET /api/search/suggest/?q=` (`src/lib/search.ts`, в проде — Meilisearch).
- `src/components/catalog` — каталог: фильтры, сортировка, сетка/таблица, пагинация, блоки под сеткой.
- `src/app/[locale]/catalog/[[...slug]]` — `/catalog/`, `/catalog/{раздел}/`, `/catalog/{раздел}/{подраздел}/`.
- `src/lib/api.ts`, `src/lib/catalog-api.ts`, `src/lib/category-page.ts` — данные сайта. Сейчас отдают моки из `src/data/mock`; при подключении бэкенда меняются только тела функций.
- `src/lib/catalog.ts` — формат URL фильтров (`?brand=edqm&pack=100-mg&sort=name&page=2`), фильтрация, сортировка, фасеты.
- `src/lib/rfq-store.ts` — корзина запроса (пока в localStorage).
- `messages/ru.json`, `messages/en.json` — строки интерфейса.
- `src/app/[locale]/product/[slug]` — карточка товара (3 типа: стандарты, оборудование, прочее): идентификаторы с копированием, фасовки и своя фасовка, аналоги, вкладки «Описание» / «Технические данные», документы, «другие примеси субстанции», аналоги других брендов, аксессуары, FAQ, форма с подставленным товаром.
- `src/app/[locale]/substances` — указатель А–Я и `/substances/{мнн}/`: все стандарты и примеси субстанции, выбор нескольких позиций и добавление в корзину одним действием (SC-05).
- `src/app/[locale]/brands`, `services`, `articles`, `authors` — бренды, услуги с формой расчёта (поля задаются на услугу, RFQ-08), статьи и автор.
- `src/app/[locale]/about`, `delivery`, `documents`, `contacts` — страницы доверия с реквизитами из `getSiteSettings()`.
- `src/app/[locale]/rfq` — корзина запроса: строки с фасовкой, количеством, аналогами и комментарием, свободные строки, вставка списка до 200 позиций (SC-02, `POST /api/search/batch`), форма RFQ-03 с проверкой ИНН, экран «Спасибо» (RFQ-05).
- `src/app/[locale]/search` — результаты поиска с фильтрами по бренду и разделу; пустая выдача — форма с подставленным запросом (SC-03).
- `src/app/robots.txt`, `src/app/sitemap.xml`, `src/app/sitemaps/[file]` — robots.txt (SEO-03, Clean-param, staging закрыт через `SITE_ENV=staging`) и индекс Sitemap по типам страниц (SEO-04).

## SEO-слой

- `src/lib/seo.ts` — `pageMetadata()`: canonical на себя без query (URL-09), `?page=N` в canonical только у пагинации (URL-08), noindex для фильтров (URL-06) и неполных карточек (SEO-07). hreflang ru/en/x-default — только у страниц с переводом (`hasEn`); EN-страница без перевода — `noindex, follow` и canonical на русскую (EN-05).
- Уровневая индексация товаров: полнота 0–100 считается в `src/lib/product-api.ts` по критериям ТЗ 5.6, порог 70 (`INDEX_THRESHOLD`). Ниже порога — noindex и нет в Sitemap. Субстанции — index при ≥ 3 позициях и тексте.
- JSON-LD (`src/components/seo/JsonLd.tsx`): Organization, WebSite + SearchAction, BreadcrumbList на всех страницах кроме главной, Product без offers, Article, Person, Service, FAQPage только там, где FAQ виден.
- Метатеги товаров и субстанций — по шаблонам ТЗ 10.2; H1/Title категорий и услуг — из ТЗ 10.3.

## Временно

- Шрифт Manrope вместо LT Superior (нужны файлы и веб-лицензия).
- Товары, тексты главной, категорий, брендов, услуг, статей и страниц доверия — моки в `src/data/mock`; EN-версия контента пока на русском (интерфейс переведён), поэтому `/en/` в noindex.
- Обогащённые карточки (описание, формула, документы) — 9 витринных позиций в `src/data/mock/product-details.ts`; химические данные сверить с каталогами производителей. Остальные позиции — шаблонный текст и noindex до обогащения.
- Статей 3 из 10 тем ТЗ 10.4: остальные публикуются по мере написания, без страниц-заглушек. Отметка «Проверено экспертом» появится после проверки химиком (`reviewed`).
- Страница автора в noindex, пока нет квалификации и фото.
- Не сделаны: выдвижная панель корзины (сейчас иконка ведёт на `/rfq/`), разбор xlsx на клиенте (файл прикладывается к заявке), YML-фид для Директа, отраслевые решения `/solutions/` (P2), личный кабинет (P2).
- Фото товаров нет: в карточках нарисованная банка-заглушка, её заменят фото производителей.

## Дизайн

Визуальный язык — ТЗ 11 (тёмная тема, зелёный акцент, кнопки-«таблетки»). Вёрстка проверена скиллами frontend-design, ui-ux-pro-max и taste-skill: заголовки не длиннее 2 строк (кроме H1 главной из ТЗ 10.3 на телефоне), без надзаголовков, тонких линий и декоративных градиентов, шесть ступеней шрифта, текст не мельче 13 px. Строки с осознанными исключениями помечены `taste-skill-ignore` с причиной.
