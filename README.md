# ogk-chem-web — витрина ogk-chem.ru

Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · next-intl (RU `/`, EN `/en/`).

## Запуск

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production-сборка
npm run lint       # ESLint
npm run typecheck  # TypeScript
```

## Что где

- `src/app/globals.css` — дизайн-токены (цвета, типографика, скругления, брейкпоинты).
- `src/components/ui` — UI-кит: кнопки, поля, бейджи, диалог.
- `src/components/layout` — шапка, мегаменю, мобильное меню, подвал, cookie-баннер.
- `src/components/product` — карточка товара, «В корзину», окно «Заказать в 1 клик».
- `src/components/home` — секции главной.
- `src/components/catalog` — каталог: фильтры, сортировка, сетка/таблица, пагинация, блоки под сеткой.
- `src/app/[locale]/catalog/[[...slug]]` — `/catalog/`, `/catalog/{раздел}/`, `/catalog/{раздел}/{подраздел}/`.
- `src/lib/api.ts`, `src/lib/catalog-api.ts`, `src/lib/category-page.ts` — данные сайта. Сейчас отдают моки из `src/data/mock`; при подключении бэкенда меняются только тела функций.
- `src/lib/catalog.ts` — формат URL фильтров (`?brand=edqm&pack=100-mg&sort=name&page=2`), фильтрация, сортировка, фасеты.
- `src/lib/rfq-store.ts` — корзина запроса (пока в localStorage).
- `messages/ru.json`, `messages/en.json` — строки интерфейса.

## Временно

- Шрифт Manrope вместо LT Superior (нужны файлы и веб-лицензия).
- Товары, тексты главной и категорий — моки; EN-версия контента пока на русском (интерфейс переведён).
- Страницы товара, корзины, поиска, брендов, услуг и т. д. ещё не сделаны — ссылки ведут на 404.
