# Промпт 01 — Главная страница ogk-chem.ru + фундамент фронтенда

> Копируйте в нейросеть всё, что ниже линии. Вместе с промптом приложите:
> 1) скриншот текущего лендинга ogk-chem.ru (источник стиля);
> 2) если есть — экспорт фреймов «Главная» и «Стиль» из Figma (OGK-CHEM-WEB-DSGN).

---

## 0. Роль, задача, формат ответа

Ты — senior frontend-разработчик (Next.js, TypeScript, Tailwind, доступность, SEO). Сделай **главную страницу B2B-каталога ОГК-ХИМ** и **общий фундамент фронтенда**: дизайн-токены, UI-кит, шапку, подвал, корзину запроса (только хранилище и счётчик), окно «Заказать в 1 клик», cookie-баннер.

Это первая страница из серии. Остальные страницы (каталог, карточка товара, корзина, поиск, услуги и т. д.) другие исполнители будут делать отдельно, а потом всё соберут в один проект. Поэтому **структура файлов, имена компонентов, их props, типы данных и токены из этого промпта обязательны**: не переименовывай и не меняй их по своему вкусу.

Приоритет источников: требования и тексты из этого промпта → макет Figma (если приложен; из него бери композицию и пропорции) → скриншот лендинга (настроение, графика).

**Формат ответа:**
1. Сначала — дерево файлов.
2. Затем полный код каждого файла отдельным блоком с путём в заголовке. Никаких `// ...остальной код`, `TODO: реализовать` вместо логики и пропущенных файлов.
3. В конце — список допущений и мест, где ты отступил от промпта (если отступил), с причиной.
4. Если не помещаешься в один ответ — остановись на границе файла и напиши `ПРОДОЛЖЕНИЕ СЛЕДУЕТ`. Я напишу «дальше».

---

## 1. Контекст проекта

ОГК-ХИМ поставляет фармацевтическим лабораториям стандартные образцы (EDQM, USP, LGC…), реактивы, расходники для ВЭЖХ, оборудование, а также делает логистику с холодовой цепью и таможню. Сайт — B2B-каталог **без цен**: клиент собирает позиции в **корзину запроса** и получает коммерческое предложение (КП) от менеджера.

- Аудитория: химики-аналитики, начальники лабораторий, закупщики, специалисты ВЭД. Ищут по точному каталожному номеру (кат. №) или CAS, часто приходят со списком из десятков позиций. Работают в основном с десктопа, но поиск, карточка и отправка запроса обязаны работать на телефоне.
- Тон: строгий, экспертный, спокойный. Без маркетинговых восклицаний.
- Визуальный образ: тёмная тема, кислотно-зелёный акцент, кнопки-«таблетки», крупные 3D-рендеры флаконов стандартных образцов (янтарное стекло, зелёная крышка) на тёмном фоне, мягкое зеленоватое свечение.
- Главная — это перенос текущего лендинга в новую структуру сайта: плюс каталог товаров, поиск, корзина запроса, мегаменю.

---

## 2. Стек и технические ограничения

- **Next.js 15** (App Router), **React 19**, **TypeScript** (`strict: true`), **Tailwind CSS v4** (токены через `@theme` в `globals.css`), **next-intl** (RU/EN).
- `next.config.ts`: `trailingSlash: true` (все внутренние ссылки заканчиваются на `/`), `images.formats: ['image/avif', 'image/webp']`.
- i18n: локали `ru` (по умолчанию, **без префикса**: `/`) и `en` (`/en/`), `localePrefix: 'as-needed'`. Все строки интерфейса — через `useTranslations`/`getTranslations` из `messages/ru.json` и `messages/en.json` (заполни **оба** файла). Контент страницы (тексты блоков, товары) приходит из моков в `src/data/mock/` — только RU; EN-версию контента я добавлю при сборке.
- Разрешённые зависимости: `next-intl`, `zustand`, `clsx`, `tailwind-merge`, `react-hook-form`, `zod`, `@hookform/resolvers`, `lucide-react`, `embla-carousel-react` (по желанию для слайдеров), примитивы `shadcn/ui` на Radix (Dialog, Sheet, NavigationMenu, Select, RadioGroup, Checkbox) — **перекрашенные под наши токены**.
- Запрещено: swiper, jQuery, framer-motion и другие анимационные библиотеки (анимации — только CSS), CSS-in-JS, lodash целиком, moment, внешние картинки/шрифты/скрипты. Единственный внешний ресурс — шрифт Manrope через `next/font/google`.
- По умолчанию — **Server Components**. `'use client'` только для интерактивных островов (слайдер, переключатель и «Загрузить ещё» в товарах, кнопки корзины, формы, диалоги, интерактивные части шапки).
- Весь контент, заголовки, ссылки и тексты должны быть в HTML с сервера (SSR). Ссылки — обычные `<a href>` через `next/link`, не `onClick`-навигация.
- Изображения — только `next/image`: у hero-изображения первого слайда `priority`, остальные лениво; всегда `width/height` или `fill` + `sizes`. Картинок у тебя нет — ссылайся на пути из раздела 7.4 (файлы положу сам).

---

## 3. Обязательная структура файлов

```
messages/
  ru.json
  en.json
public/images/                 # пусто: ассеты положу при сборке
src/
  middleware.ts                # next-intl
  i18n/
    routing.ts                 # defineRouting({ locales: ['ru','en'], defaultLocale: 'ru', localePrefix: 'as-needed' })
    request.ts
    navigation.ts              # Link, redirect, usePathname, useRouter из next-intl
  app/
    globals.css                # Tailwind v4 + @theme-токены (раздел 4)
    [locale]/
      layout.tsx               # <html lang>, шрифт, Header, Footer, CookieBanner, OneClickOrderDialog, Providers
      page.tsx                 # Главная (Server Component) + generateMetadata
      not-found.tsx            # простая заглушка в стиле сайта
  components/
    layout/
      Header.tsx  MegaMenu.tsx  MobileMenu.tsx  HeaderSearch.tsx
      CartButton.tsx  LangSwitcher.tsx  Footer.tsx  CookieBanner.tsx  SkipLink.tsx
    ui/
      Container.tsx  SectionHeading.tsx  Button.tsx  RoundArrowButton.tsx
      Input.tsx  Textarea.tsx  Checkbox.tsx  Select.tsx  RadioGroup.tsx
      QuantityStepper.tsx  FileInput.tsx  StatusBadge.tsx  Chip.tsx
      Dialog.tsx  Logo.tsx  LogoSecondary.tsx  Icon.tsx
    product/
      ProductCard.tsx          # size: 'sm' | 'md' (на главной 'sm', в каталоге будет 'md')
      ProductImage.tsx         # фото → 2D-структура → VialPlaceholder
      VialPlaceholder.tsx      # фирменная заглушка-флакон (inline SVG) с названием и CAS
      PackagingSelect.tsx
      AddToRfqButton.tsx       # «В корзину» ↔ «В корзине»
      OneClickButton.tsx       # «Заказать в 1 клик»
      OneClickOrderDialog.tsx  # одно глобальное окно, открывается через стор
      AnalogueChoice.tsx       # «Только этот товар / Готовы рассмотреть аналоги / Подберите аналог»
    forms/
      RequestForm.tsx  SubscribeForm.tsx  ConsentCheckbox.tsx  PhoneInput.tsx  FormStatus.tsx
    home/
      HeroSlider.tsx  ProductsSection.tsx  BrandsSection.tsx  CatalogPromo.tsx
      QualitySection.tsx  ServicesSection.tsx  WhyUsSection.tsx
      CapabilitiesSection.tsx  RequestSection.tsx  SubscribeSection.tsx
    seo/
      JsonLd.tsx
  lib/
    api.ts                     # изоморфные функции-моки (раздел 7.3)
    analytics.ts               # track() (раздел 9)
    rfq-store.ts               # zustand: корзина запроса
    one-click-store.ts         # zustand: открыть/закрыть окно «в 1 клик»
    consent.ts                 # согласие на cookies
    phone.ts                   # маска и нормализация в E.164
    cn.ts                      # clsx + tailwind-merge
  types/
    catalog.ts  content.ts  requests.ts  settings.ts
  data/mock/
    products.ts  categories.ts  brands.ts  home.ts  settings.ts
```

---

## 4. Дизайн-система

### 4.1. Цвета (токены — только через них, никаких «левых» hex в компонентах)

| Токен | Значение | Где |
|---|---|---|
| `base` | `#1C1C1C` | фон страницы и крупных блоков |
| `base-deep` | `#0E0E0E` | оверлей под модалками, самые тёмные зоны |
| `surface` | `rgba(53, 61, 49, 0.2)` | карточки, плитки логотипов, аккордеон, капсула шапки |
| `surface-strong` | `rgba(53, 61, 49, 0.3)` | поля ввода |
| `surface-raised` | `#2A2D29` | непрозрачный фон модалок, выпадающих меню, мегаменю |
| `accent` | `#82EE8D` | акцентные слова заголовков, бейджи, главные CTA, иконки |
| `accent-hover` | `#C4FFCA` | hover акцентных элементов |
| `text` | `#E7E7E7` | заголовки, основной текст |
| `text-secondary` | `#ACACAC` | вторичный текст, подписи, hover обычных ссылок |
| `text-placeholder` | `#9A9A9A` | плейсхолдеры (на лендинге было 13% прозрачности — это не проходит контраст WCAG AA, не повторяй) |
| `text-on-accent` | `#1C1C1C` | текст на зелёных кнопках |
| `border` | `rgba(231, 231, 231, 0.13)` | тонкие границы, разделители, hover полей |
| `border-strong` | `#ACACAC` | граница поля в фокусе |
| `error` | `#FF6B5A` | ошибки (лендинговый `#DB371F` на тёмном фоне не проходит контраст) |
| `warning` | `#F5C451` | предупреждения |
| `success` | `#82EE8D` | успех |

Эффект «свечения» (на hover карточек и у открытого пункта аккордеона — на правой половине блока):
`linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(243,255,244,0.1) 100%)`, появляется через `opacity` за 0.4 с.

Капсула шапки: фон `surface` + `backdrop-filter: blur(40px)`, скругление 100px.

### 4.2. Типографика

Шрифт: **LT Superior** (коммерческий, файлы подключу сам через `next/font/local`). Сейчас используй **Manrope** через `next/font/google` (subsets `latin`, `cyrillic`) в CSS-переменной `--font-sans`, стек: `'LT Superior', var(--font-manrope), system-ui, sans-serif`.

Начертания: заголовки — 500, основной текст — 400, пункты меню — 500, кнопки — см. 4.4.

Размеры — «резиновые» между 360 и 1440 px через `clamp()`:

| Стиль | 360 px → 1440 px | clamp | Прочее |
|---|---|---|---|
| `h1` (hero) | 32 → 58 | `clamp(2rem, 1.458rem + 2.407vw, 3.625rem)` | line-height 1.1, **uppercase**, 500 |
| `h2` (заголовок секции) | 32 → 58 | то же | line-height 1.2, 500 |
| `h3` | 22 → 36 | `clamp(1.375rem, 1.083rem + 1.296vw, 2.25rem)` | line-height 1.1, 500 |
| `h4` | 18 → 24 | `clamp(1.125rem, 1rem + 0.556vw, 1.5rem)` | line-height 1.2, 500 |
| `lead` | 16 → 24 | `clamp(1rem, 0.833rem + 0.741vw, 1.5rem)` | line-height 1.3 |
| `body` | 16 | — | line-height 1.5 |
| `small` | 14 | — | line-height 1.4 |
| `caption` | 12 | — | line-height 1.3 |

Кат. номера и CAS — `font-variant-numeric: tabular-nums`. Индексы в формулах — `<sub>`. Длинные химические названия переносятся (`overflow-wrap: anywhere`), не вылезают из карточки.

Заголовок секции: обычная часть цветом `text`, **последние слова — цветом `accent`** («Широкий **ассортимент**», «Сервис **под ключ**», «Почему **выбирают нас**», «Отправьте ваш **запрос**»). Под заголовком — подзаголовок `small`/`body` цветом `text-secondary`.

### 4.3. Сетка, отступы, скругления, брейкпоинты

- Брейкпоинты (переопредели в `@theme`): `sm 480`, `md 768`, `lg 1024`, `xl 1280`, `2xl 1440`. Базовая ширина — 360 (mobile first).
- `Container`: `max-width: 1640px` вместе с полями; поля по бокам: 16px (<768), 24px (≥768), 40px (≥1024), 80px (≥1440).
- Отступ между секциями: 80px (<768), 120px (≥768), 160px (≥1024).
- Заголовок секции → контент: 24px (<768), 48px (≥1024).
- Внутренние отступы карточек: 20px (<768), 34px (≥1024). Зазор сетки: 12px (<768), 24px (≥768), 34px (≥1440).
- Скругления: **100px** — кнопки, чипы, капсула шапки; **32px** — крупные и средние блоки (карточки, плитки, аккордеон, промо, модалка); **12–16px** — мелкие элементы и поля ввода (поля — 16px).

### 4.4. UI-кит (точно по дизайн-системе)

`Button` — `variant` × `size`, рендерится как `<a>` при наличии `href`, иначе `<button>`. Высота кнопок с иконкой и без — одинаковая. Переход 0.3 с, при нажатии `transform: scale(0.97)`.

| Вариант | Вид | Размеры / шрифт | Hover |
|---|---|---|---|
| `menu` | контур 1px `accent`, текст `accent`, фон прозрачный | s: 16px / 500, padding 12×24 | фон `accent`, текст `text-on-accent` |
| `primary` | заливка `accent`, текст `text-on-accent` | s: 16px / 500, 12×24 («Заказать» в шапке); m: 18px / 600, 12×22 («Сделать заказ +»); l: 24px / 400, 15×24, во всю ширину («Отправить») | заливка `accent-hover` |
| `secondary` | фон `surface`, текст `accent`, без рамки, справа точка `•` или иконка | m: 18px / 600, 12×22 («Заказать услугу •», «Связаться с нами •») | текст `accent-hover`, иконка ярче |
| `ghost` | без фона, текст `text`, иконка `accent` | s/m | текст `accent` |

На мобильных (<480): s 14px, m 16px, l 18px.

`RoundArrowButton` — круг 40px (32 на мобильных), контур 1px `text`, внутри стрелка → (lucide `ArrowRight`). Hover: контур и стрелка `accent`. Нужен `aria-label`.

`StatusBadge` — пилюля 12–14px: `in_stock` → «В наличии» (заливка `accent`, текст `text-on-accent`); `on_request` → «Под заказ» (контур `border`, текст `text-secondary`).

`Chip` — пилюля `surface`, текст `text`, 14–16px; если есть `href` — ссылка с hover `accent`.

`Input`/`Textarea`/`Select` — фон `surface-strong`, рамка 1px прозрачная → hover `border` → focus `border-strong`, ошибка — `error`. Скругление 16px, padding 16×22 (12×16 на мобильных), текст `text` 16–20px. **Видимая подпись (label) над каждым полем** (можно визуально компактную), плейсхолдер — только пример. Ошибка — текст под полем, связана через `aria-describedby`, `aria-invalid`. Всем полям ввода — класс `ym-disable-keys` (Вебвизор не должен записывать ввод).

`Checkbox` — квадрат 20px со скруглением 6px, контур `text-secondary`, отмечен — заливка `accent` с галочкой `base`. Подпись кликабельна, ссылки в подписи — `accent`.

`Dialog` — Radix Dialog: фон `surface-raised`, скругление 32px, оверлей `base-deep` 70%, ловушка фокуса, Esc закрывает, возврат фокуса на кнопку-источник; на <768 — полноэкранный лист снизу.

Фокус: `:focus-visible` → `outline: 2px solid var(--color-accent); outline-offset: 2px` на всех интерактивных элементах. Никаких `outline: none` без замены.

`Logo` — `<Image src="/images/brand/logo.svg" alt="ОГК-ХИМ" width={112} height={40} />` (в шапке ссылка на `/`). `LogoSecondary` — «ОГК ХИМ» в капсуле, `/images/brand/logo-secondary.svg`, декоративный (`alt=""`).

Иконки — `lucide-react`, stroke 1.5, 20–24px, цвет `accent`.

---

## 5. Глобальные компоненты (в `layout.tsx`)

### 5.1. `SkipLink`
Первый фокусируемый элемент: «Перейти к содержимому» → `#main`. Виден только в фокусе.

### 5.2. `Header` — фиксированная, `top: 12px`, z-index выше контента

**≥1024 px — две строки:**
- **Строка 1 — капсула** (высота 72px, фон `surface` + blur 40px, скругление 100px): `Logo` → кнопка **«Каталог»** (вариант `menu`, иконка `LayoutGrid` + шеврон; открывает `MegaMenu`) → **`HeaderSearch`** (занимает всё свободное место) → телефон `+7 495 234 28 63` (`tel:+74952342863`, событие `click_phone`, `place: 'header'`; на 1024–1279 только иконка `Phone` с `aria-label`) → `LangSwitcher` (RU / EN) → `CartButton` → кнопка **«Заказать»** (`primary` s, ссылка `/rfq/`).
- **Строка 2 — под капсулой**, высота 44px, без фона: ссылки-«таблетки» `menu` s: «Бренды» `/brands/`, «Услуги» `/services/`, «Статьи» `/articles/`, «О компании» `/about/`, «Контакты» `/contacts/`. Текущий раздел — `aria-current="page"` и заливка. При прокрутке вниз строка 2 уезжает (`transform`), при прокрутке вверх возвращается. Без сдвига вёрстки.

**<1024 px — одна капсула** (высота 64px): `Logo` → иконка поиска (раскрывает `HeaderSearch` во всю ширину под капсулой) → `CartButton` → бургер (открывает `MobileMenu`).

`HeaderSearch` — `<form role="search" action="/search/" method="get">`, поле `name="q"`, `type="search"`, `autocomplete="off"`, label (визуально скрыт) «Поиск по каталогу», плейсхолдер «Название, кат. № или CAS», иконка `Search`, кнопка отправки. Форма работает без JS. Подсказки сделаем отдельной задачей — оставь в компоненте пустой слот `{/* SearchSuggest: подсказки */}` и состояние `query`.

`MegaMenu` — открывается по клику и Enter/Space, закрывается по Esc, клику вне и уходу фокуса. Панель под капсулой во всю ширину контейнера, фон `surface-raised`, скругление 32px. Слева — список категорий первого уровня; справа — подкатегории наведённой/сфокусированной категории + ссылка «Все товары раздела →»; внизу — «Весь каталог» `/catalog/`. Данные — `getCatalogTree()` (7.3), все ссылки — обычные `<a href>`. Можно взять Radix NavigationMenu.

`MobileMenu` — Radix Sheet на весь экран: «Каталог» (аккордеон категорий с подкатегориями), «Бренды», «Услуги», «Статьи», «О компании», «Контакты», телефон, e-mail, RU/EN, кнопка «Заказать». Блокирует прокрутку страницы.

`CartButton` — иконка `ShoppingCart`, ссылка на `/rfq/`, `aria-label="Корзина запроса, позиций: N"`. Счётчик-бейдж (`accent`, текст `text-on-accent`) из `rfq-store`; рендерится **только после монтирования** (без ошибок гидрации); при изменении счётчика — короткая CSS-анимация (отключается при `prefers-reduced-motion`). Выдвижную панель корзины сделаем отдельно.

`LangSwitcher` — две ссылки RU / EN на **ту же страницу** в другой локали (`usePathname` + `Link` из next-intl), текущая — `aria-current`. Без автоопределения языка.

### 5.3. `Footer` (`id="contacts"` не нужен)

Как на лендинге: сверху крупный `Logo`. Ниже три колонки (на мобильных — друг под другом):
- **Меню:** Главная `/`, Каталог `/catalog/`, Бренды `/brands/`, Услуги `/services/`, Статьи `/articles/`, О компании `/about/`, Контакты `/contacts/`, Заказать `/rfq/`.
- **Центр — капсула с контактами** (рамка 1px `accent`, скругление 100px): слева вращающийся глобус (`/images/footer/globe.svg`) с круговой надписью (`/images/footer/globe-text.svg`, медленное вращение 20 с, отключается при `prefers-reduced-motion`); справа телефон (`click_phone`, `place: 'footer'`), `info@ogk-chem.ru`, `order@ogk-chem.ru` (`click_email`).
- **Документы:** «Согласие на обработку персональных данных» `/files/soglasie.pdf`, «Политика конфиденциальности» `/files/politika.pdf`, «Приложения и файлы» `/files/kartochka.pdf` (иконка `FileText`). Открываются в новой вкладке (`rel="noopener"`).

Под колонками: адрес «129301, Москва, ул. Касаткина, д. 8, помещ. 1/1», часы «пн–пт 9:00–18:00». Нижняя строка (`caption`, `text-secondary`): «© 2026 ООО «ОГК-ХИМ» · ИНН 9717188828 · КПП 771701001 · ОГРН 1267700023997». Все данные — из `getSiteSettings()`, не хардкодить.

### 5.4. `CookieBanner`
Внизу экрана, фон `surface-raised`, скругление 32px, не перекрывает кнопки форм на мобильных. Текст: «Мы используем cookies, чтобы сайт работал, и — с вашего согласия — для аналитики (Яндекс Метрика, Google Analytics).» Ссылка «Политика конфиденциальности» → `/files/politika.pdf`. Кнопки: «Принять все» (`primary` s) и «Только необходимые» (`menu` s). Выбор хранится в `localStorage` (`ogk-cookie-consent`: `all` | `necessary`) через `lib/consent.ts`, баннер больше не показывается. Счётчики аналитики не грузим — только флаг (раздел 9). Все обращения к `localStorage` — в `try/catch`.

### 5.5. `OneClickOrderDialog` — окно «Заказать в 1 клик»
Одно на приложение, открывается из любой карточки через `useOneClickStore().open({ product, packagingId })`.

Содержимое:
- Заголовок «Заказать в 1 клик».
- Блок товара: полное название, строка «Бренд · Кат. № … · CAS …».
- `PackagingSelect`: фасовки товара; если `customPackaging` — пункт «Своя фасовка», который показывает поля «Количество» + единица (`мг`, `г`, `мл`, `шт.`).
- `QuantityStepper` «Количество упаковок» (1–999, кнопки −/+ с `aria-label`, ввод с клавиатуры).
- `AnalogueChoice` (радиогруппа): «Только этот товар» (по умолчанию), «Готовы рассмотреть аналоги», «Подберите аналог» (по умолчанию, если `product.discontinued`).
- Поля: Имя*, Компания*, Телефон* (`PhoneInput`), E-mail*, `ConsentCheckbox`*.
- Кнопка «Отправить запрос» (`primary` l). Под ней `small` `text-secondary`: «Ответим в течение 2 рабочих часов. Цену и срок поставки пришлём в коммерческом предложении».
- Успех: «Запрос № {number} отправлен», «Менеджер свяжется с вами в течение 2 рабочих часов», кнопка «Закрыть».
- Отправка: `submitSiteRequest({ kind: 'one_click', … })`; событие `product_request` `{ sku, brand, category }`.

---

## 6. Главная: секции по порядку

`<main id="main">`. Ровно **один `<h1>`** на странице. Каждая секция — `<section aria-labelledby="…">` с `<h2>`. Все тексты ниже — из `getHomeContent()` (моки в `data/mock/home.ts`), **не в JSX**.

### 6.1. `HeroSlider` — первый экран
Как на лендинге: тёмная область во всю ширину контейнера, скругление 32px, высота `clamp(560px, 100svh, 900px)` (с учётом фиксированной шапки). Фон — крупное изображение слайда (флакон), медленное масштабирование 1 → 1.05 за 20 с туда-обратно (выключено при `prefers-reduced-motion`).
- Слева сверху: иконка + «Сервис, которому можно **доверять**». Справа сверху: иконка + «**60+** мировых производителей» (выделенное — `accent`). На <768 — в одну строку под шапкой или скрыть второй бейдж.
- Слева снизу: заголовок, подзаголовок (`lead`, `text-secondary`), кнопки.
- Переключение **по клику**: круглые кнопки «←/→» (`RoundArrowButton`) и точки-пилюли (активная — длинная `accent`). Свайп на тач-устройствах. **Без автопрокрутки.** Клавиатура: стрелки при фокусе на слайдере.
- Доступность: контейнер `role="region" aria-roledescription="carousel" aria-label="Главные предложения"`, слайд `role="group" aria-roledescription="slide" aria-label="1 из 3"`, неактивные слайды `inert`. Все слайды есть в SSR-HTML.
- **Заголовок первого слайда — единственный `<h1>` страницы.** Заголовки остальных слайдов — `<h2>` с тем же стилем `h1`.

Слайды (мок):
1. **H1:** «Материалы, реактивы и оборудование для фармацевтических лабораторий». Подзаголовок: «Комплексные решения для фармкомпаний». Кнопки: «Сделать заказ +» (`primary` m, иконка `Plus`, ссылка `#request` — плавная прокрутка к форме на этой странице) и «Связаться с нами •» (`secondary` m, `/contacts/`). Картинка `/images/home/hero-1.webp` (1600×1000).
2. «Стандартные образцы EDQM, USP, BP и LGC». Подзаголовок: «Поставка под заказ из каталогов производителей — с документами и соблюдением условий хранения». Кнопка: «Перейти в каталог» (`primary` m, `/catalog/reference-standards/`). Картинка `/images/home/hero-2.webp`.
3. «Логистика с холодовой цепью из 23 стран». Подзаголовок: «Термоконтейнеры, хладоэлементы и логгеры температуры, таможенное оформление и разрешения на ввоз». Кнопки: «Рассчитать доставку» (`primary` m, `/services/cold-chain/`), «Все услуги •» (`secondary` m, `/services/`). Картинка `/images/home/hero-3.webp`.

### 6.2. `ProductsSection` — «Каталог **товаров**»
Подзаголовок: «Стандартные образцы, реактивы, хроматография и оборудование ведущих производителей».
1. **Ряд кнопок категорий** — ссылки-«таблетки» `menu` s на 8 разделов каталога (7.2). На <1024 — горизонтальная прокрутка одной строкой со scroll-snap.
2. **Переключатель «Популярные / По алфавиту»** над сеткой — сегментированный контрол (`role="radiogroup"` или две кнопки с `aria-pressed`). По умолчанию «Популярные». **URL не меняется.** Переключение перезагружает список с первых 12.
3. **Сетка 12 маленьких карточек** (`ProductCard size="sm"`): 1 колонка <480, 2 — ≥480, 3 — ≥1024, 4 — ≥1280. Первые 12 «популярных» рендерятся на сервере.
4. **«Загрузить ещё»** (`menu` m, по центру): +12 товаров, сколько угодно раз; во время загрузки — `aria-busy` и скелетоны карточек; когда товары кончились — кнопка исчезает. Новые карточки добавляются без прыжка прокрутки, фокус остаётся на кнопке. Рядом — ссылка «Весь каталог →» `/catalog/`.

**`ProductCard size="sm"`** (контракт общий для всего сайта):
- Корпус: фон `surface`, скругление 32px (24px на <768), padding 16–20px, hover — свечение 4.1. Карточка — `<article>`.
- `ProductImage`: квадрат 1:1, фон `surface-strong`, скругление 16px, `object-contain` с полями 12px. Приоритет: фото производителя → 2D-структура → `VialPlaceholder`.
- `VialPlaceholder` — **inline SVG** фирменного флакона: зелёная крышка `accent`, серебристое кольцо, янтарное стекло, белая этикетка, на этикетке — название (до 2 строк, обрезка) и CAS. Должен выглядеть аккуратно в любом размере.
- Сверху на изображении слева — `StatusBadge`.
- Бренд — `caption`, uppercase, `text-secondary`, ссылка на `/brands/{slug}/`.
- Название — `body`/500, **максимум 2 строки с многоточием** (`line-clamp-2`), полное название в атрибуте `title`; ссылка на `/product/{slug}/`. Ссылка растягивается на изображение (но не перекрывает кнопки — никаких вложенных интерактивных элементов).
- Строки `small` с `tabular-nums`: «Кат. № Y0001897», «CAS 28721-07-5» (если CAS нет — строку не выводим). У оборудования вместо «Кат. №» — «P/N».
- Фасовка: одна — текст «Фасовка: 100 мг»; несколько — компактный `PackagingSelect`; если `customPackaging` — ещё строка `accent` «Любая фасовка под запрос».
- **Цен нет. Никогда.**
- Две кнопки внизу (одна под другой в `sm`, рядом в `md`): **«В корзину»** (`AddToRfqButton`, `primary` s, во всю ширину) и **«Заказать в 1 клик»** (`OneClickButton`, `secondary` s).
- `AddToRfqButton`: добавляет выбранную фасовку, количество 1, `analogue: 'none'` в `rfq-store`, событие `add_to_rfq` `{ sku, brand, place: 'list' }`. После добавления кнопка становится **«В корзине»** (иконка `Check`, стиль `menu`) и ведёт на `/rfq/`. Состояние берётся из стора, переживает перезагрузку. `aria-live="polite"` объявляет «Добавлено в корзину запроса».

### 6.3. `BrandsSection` — «Широкий **ассортимент**»
Подзаголовок: «Под любые задачи производства».
- Ряд плиток логотипов (фон `surface`, скругление 32px, ~200×120 на десктопе, ~140×88 на мобильных), каждая — ссылка на `/brands/{slug}/` с `aria-label="{Бренд}"`. Логотипы светлые, `/images/brands/{slug}.svg`; если файла нет — название бренда текстом (`h4`). Горизонтальная прокрутка со scroll-snap и кнопками ←/→ (`RoundArrowButton`), **без автопрокрутки**. На hover — свечение.
- Бренды по порядку: EDQM `edqm`, USP `usp`, Merck `merck`, LGC `lgc`, BioOrganics `bioorganics`, SynZeal `synzeal`, SCIEX `sciex`, Waters `waters`, Macklin `macklin`, Clearsynth `clearsynth`, Aozeal `aozeal`, Agilent `agilent`, Welch `welch`.
- Сразу под логотипами — **`CatalogPromo`** (элемент из UI-кита): блок `surface`, скругление 32px; слева изображение флакона `/images/home/promo-vial.webp` (выступает за верхний край блока); справа заголовок `h3` `accent` «Нужен конкретный товар?», текст `text` «Большой выбор товаров в каталоге для ваших нужд», кнопка `primary` m «Перейти в каталог ↘» (иконка `ArrowDownRight`) → `/catalog/`. На <768 — колонкой.

### 6.4. `QualitySection` — «Лучшее **качество**»
Подзаголовок: «Мы предлагаем нашим клиентам только проверенную продукцию». Три карточки (`surface`, скругление 32px, hover — свечение): заголовок `h3` слева, иконка `accent` справа, текст `body` снизу. 3 колонки ≥1024, иначе 1.
1. «Доставка» (`Map`) — «В любой регион страны за счёт отлаженной логистики. Соблюдаем температурный режим, сроки и условия хранения».
2. «Закупка» (`Globe`) — «Из США, Европы, Азии, Латинской Америки и других стран. Берём на себя таможенные процедуры и организацию логистики».
3. «Документы» (`FileText`) — «Предоставляем всю необходимую документацию. Сертификация и контроль на каждом этапе в соответствии с правилами».

### 6.5. `ServicesSection` — «Сервис **под ключ**»
Подзаголовок: «Полный цикл услуг для фармацевтических компаний». Справа от заголовка — ссылка «Все услуги →» `/services/`.

**Аккордеон как на лендинге**: три блока (`surface`, скругление 32px, между ними 32px), **открыт всегда ровно один** (по умолчанию первый). Заголовок пункта — кнопка (`aria-expanded`, `aria-controls`) с круглой стрелкой слева (у открытого поворачивается) и текстом `h3`. Открытый пункт: свечение справа; слева текст `body`/`lead`, строка-подпись `accent` («Поставляем:» / «Доставим из:» / «Сделаем для вас:») и ряд `Chip` с горизонтальной прокруткой (без автопрокрутки); внизу кнопки «Подробнее об услуге» (`primary` m → страница услуги) и «Заказать услугу •» (`secondary` m → та же страница с `#form`); справа изображение услуги, которое плавно выезжает при открытии. Закрытые пункты — только заголовок. **Текст закрытых пунктов тоже должен быть в HTML** (скрываем через `hidden="until-found"` или CSS, не удаляем из DOM). Анимация высоты — CSS (`grid-template-rows: 0fr → 1fr`). На <768 изображение под текстом.

1. **«Поставка лекарственных препаратов для исследований»** → `/services/research-drug-supply/`, картинка `/images/home/service-supply.webp`.
   Текст: «Поставляем лекарственные препараты в Россию для исследовательских целей, а также стандартные образцы, реактивы, расходные материалы для хроматографии (колонки, фильтры, предколонки, фитинги), референтные лекарственные препараты для лабораторных испытаний, лабораторную тару и вспомогательное оборудование. Продукция ведущих мировых брендов соответствует строгим международным стандартам, а предложения локальных производителей помогают закрыть потребности лаборатории без потери качества.»
   «Поставляем:» EDQM, USP, Merck, LGC, BioOrganics, SynZeal, SCIEX, Waters, Macklin, Clearsynth, Aozeal, Agilent, Welch, Dayang Chem, ATCC, British Pharmacopoeia, Shimadzu, TRC.
2. **«Логистика и холодовая цепь»** → `/services/cold-chain/`, картинка `/images/home/service-logistics.webp`.
   Текст: «Доставка фармацевтики с полным контролем температурного режима. Поддерживаем холодовую цепь с помощью термоконтейнеров и хладоэлементов, контролируем температуру логгерами. Работаем с партнёрами из Америки, Европы, Азии и стран СНГ. Подбираем транспорт с учётом особенностей груза и специфики маршрута, адаптируем решения под разные типы отправлений и требования заказчиков.»
   «Доставим из:» США, Канады, Великобритании, Франции, Швеции, Германии, Норвегии, Китая, Армении, Грузии, Нидерландов, Швейцарии, России, Казахстана, Узбекистана, Азербайджана, Австрии, Бельгии, Австралии, Японии, Южной Кореи, Италии, Испании.
3. **«Таможня»** → `/services/customs-clearance/`, картинка `/images/home/service-customs.webp`.
   Текст: «Выполняем таможенное оформление фармацевтики и сопутствующих категорий товаров. Определяем коды ТН ВЭД, проверяем пакет документов и сопровождаем получение разрешительной документации для ввоза в Российскую Федерацию. Минимизируем риски задержек, обеспечиваем соответствие требованиям регуляторов и контролируем процесс на каждом этапе.»
   «Сделаем для вас:» Оформление импорта (`/services/import-export/`), Оформление экспорта (`/services/import-export/`), Разрешение на ввоз — Минздрав (`/services/import-permits/`), Разрешение на ввоз — ФСТЭК (`/services/import-permits/`), Подбор кодов ТН ВЭД (`/services/tn-ved/`), Проверка пакета документов, Консультирование (последние два — без ссылок).

### 6.6. `WhyUsSection` — «Почему **выбирают нас**»
Две колонки (≥1024), иначе одна.
- Слева: текст `lead` — «**ОГК-ХИМ** является узкопрофильной компанией, которая обеспечивает фармацевтические предприятия всем необходимым для проведения точных лабораторных исследований и разработок. Мы помогаем клиентам оптимизировать закупки, гарантируя качество поставляемой продукции. В основе нашей работы лежит принцип клиентоориентированности и стремления к постоянному совершенствованию сервиса.» («ОГК-ХИМ» — `accent`). Ниже — горизонтальная линия 1px `accent` во всю ширину колонки, заканчивающаяся `LogoSecondary` (92×24).
- Справа: 4 пункта, сетка 2×2 (≥768), у каждого заголовок `h4` с иконкой `accent` слева и текст `body` `text-secondary`:
  1. «Экспертность» (`Users`) — «Наша команда профессионалов с многолетним опытом в фармацевтической отрасли поможет подобрать оптимальные решения для ваших лабораторных задач».
  2. «Гарантия качества» (`CircleCheck`) — «Мы работаем только с проверенными производителями и обеспечиваем качественную продукцию».
  3. «Оперативность» (`Zap`) — «Развитая логистическая сеть позволяет доставлять материалы в кратчайшие сроки в любую точку России, соблюдая подходящие условия транспортировки».
  4. «Индивидуальность» (`Loader`) — «Мы разрабатываем персонализированные решения под специфику каждого клиента, учитывая особенности его работы».

### 6.7. `CapabilitiesSection` — «У нас вы сможете»
Слева заголовок `h2` (без акцента) и под ним сменяющаяся строка `h3`: «Заказать **стандартные образцы** для лаборатории» (выделенное — `accent`). Справа — крупный размытый логотип «ogk chem» цветом `accent` (`/images/home/logo-blur.webp`, декоративный).
- Строки меняются по вертикали каждые 3 с; **есть кнопка «Пауза/Продолжить»**, пауза при наведении и фокусе; при `prefers-reduced-motion` — без анимации, показываем все строки списком.
- **Каждая строка — ссылка**, и **все 12 строк есть в HTML** (это внутренняя перелинковка):
  1. Заказать **стандартные образцы** для лаборатории → `/catalog/reference-standards/`
  2. Заказать **реактивы** для лаборатории → `/catalog/reagents/`
  3. Заказать **расходные материалы** для хроматографии → `/catalog/chromatography/`
  4. Заказать **референтные лекарственные препараты** для лабораторных исследований → `/catalog/reference-drugs/`
  5. Заказать **микроорганизмы и биологические стандарты** для лабораторных исследований → `/catalog/biological-standards/`
  6. Заказать **лабораторное оборудование** для лаборатории → `/catalog/laboratory-equipment/`
  7. Приобрести годовую **подписку на онлайн-фармакопеи** и справочники → `/catalog/pharmacopeias/`
  8. Заказать **доставку** вашего груза на ваш склад → `/services/pharma-logistics/`
  9. Заказать **перевозку** груза между складами или лабораториями → `/services/pharma-logistics/`
  10. Заказать **термобоксы и хладоэлементы** для вашего груза → `/services/cold-chain/`
  11. Заказать **таможенное оформление** вашего груза → `/services/customs-clearance/`
  12. Получить **разрешения на ввоз** для вашего груза → `/services/import-permits/`

### 6.8. `RequestSection` — «Отправьте ваш **запрос**» (`id="request"`)
Две колонки (≥1024): слева список обещаний, справа форма. На мобильных форма идёт сразу после заголовка, обещания — под ней.

Обещания (иконка `accent` в круге + заголовок `accent` + текст `text-secondary`):
1. `Zap` «Быстро обработаем заявку» — «Стандартное время — до 2 рабочих часов».
2. `Phone` «Свяжемся с вами» — «Для уточнения деталей заявки».
3. `User` «Выделим персонального менеджера» — «Для ведения вашего запроса».
4. `Mail` «Отправим коммерческое предложение» — «В соответствии с вашим запросом».
Под списком — ссылка «Перейти в контакты ↘» → `/contacts/`.

`RequestForm` (react-hook-form + zod, раздел 8):
- ФИО* (мин. 3 символа), Наименование организации* (мин. 2), E-mail*, Телефон* (`PhoneInput`), «Опишите запрос»* — textarea, плейсхолдер «Услуга или товар: производитель, кат. №, CAS, фасовка, количество и т. д.» (мин. 10 символов).
- `FileInput` «Прикрепить список позиций»: необязательно, один файл `.xlsx, .csv, .pdf, .docx`, до 10 МБ; показать имя и размер файла, кнопку «Убрать»; ошибка при неверном типе/размере.
- `ConsentCheckbox`* — «Подтверждаю **согласие на обработку персональных данных**» (ссылка `/files/soglasie.pdf`) «и ознакомлен с **Политикой конфиденциальности**» (`/files/politika.pdf`).
- Кнопка «Отправить» (`primary` l, во всю ширину).
- `kind: 'general'`.

### 6.9. `SubscribeSection` — подписка на рассылку
Блок `surface`, скругление 32px, свечение справа. Заголовок `h3`: «Подпишитесь на **рассылку**». Текст: «Новинки каталога, обзоры стандартов и новости фармлогистики». Форма в одну строку (≥768): поле e-mail + кнопка «Подписаться» (`primary` m). Под ней **два отдельных** обязательных чекбокса:
- согласие на обработку персональных данных (как в 6.8);
- «Согласен(на) получать информационные и рекламные рассылки ООО «ОГК-ХИМ». Отписаться можно в любой момент по ссылке в письме».
Отправка — `subscribe()`; событие `subscribe`; успех: «Готово! Проверьте почту».

---

## 7. Данные, типы, моки

### 7.1. Типы (`src/types/*`) — используй именно их

```ts
// types/catalog.ts
export type Availability = 'in_stock' | 'on_request';            // «В наличии» | «Под заказ»
export type CardType = 'standard' | 'equipment' | 'other';       // 3 типа карточек
export type PackUnit = 'mg' | 'g' | 'ml' | 'pcs';

export interface Packaging {
  id: string;
  label: string;               // «100 мг», «1 л», «1 шт.»
  catalogNumber?: string;      // свой кат. № фасовки, если есть
  availability: Availability;
}

export interface BrandRef { slug: string; name: string; logo?: string }

export interface ProductPreview {
  id: string;
  slug: string;                // /product/{slug}/
  cardType: CardType;
  name: string;                // название EN от производителя, может быть очень длинным
  brand: BrandRef;
  catalogNumber: string;       // кат. № или P/N
  cas?: string;
  categorySlug: string;        // основная категория
  packagings: Packaging[];
  customPackaging: boolean;    // «Любая фасовка под запрос»
  availability: Availability;  // сводный статус
  image?: { src: string; alt: string; kind: 'photo' | 'structure' };
  discontinued?: boolean;
}

export interface Category {
  slug: string;
  name: string;
  href: string;                // /catalog/reference-standards/edqm/
  children?: Category[];
}

// types/content.ts
export interface Cta { label: string; href: string; variant: 'primary' | 'secondary'; icon?: 'plus' | 'dot' | 'arrow' }
export interface HeroSlide { id: string; title: string; subtitle: string; ctas: Cta[]; image: { src: string; alt: string; width: number; height: number } }
export interface IconText { id: string; title: string; text: string; icon: string }   // icon = имя иконки lucide
export interface ServiceItem { id: string; title: string; href: string; text: string; captionLabel: string; chips: { label: string; href?: string }[]; image: { src: string; alt: string } }
export interface Capability { id: string; prefix: string; accent: string; suffix: string; href: string }
export interface HomeContent {
  hero: { badges: { trust: string; trustAccent: string; makers: string; makersAccent: string }; slides: HeroSlide[] };
  products: { title: string; accent: string; subtitle: string };
  brands: { title: string; accent: string; subtitle: string; items: BrandRef[] };
  promo: { title: string; text: string; cta: Cta; image: { src: string; alt: string } };
  quality: { title: string; accent: string; subtitle: string; items: IconText[] };
  services: { title: string; accent: string; subtitle: string; items: ServiceItem[] };
  whyUs: { title: string; accent: string; text: string; items: IconText[] };
  capabilities: { title: string; items: Capability[] };
  request: { title: string; accent: string; promises: IconText[] };
  subscribe: { title: string; accent: string; text: string };
}

// types/settings.ts
export interface SiteSettings {
  phone: { display: string; href: string };            // '+7 495 234 28 63', 'tel:+74952342863'
  emails: { info: string; order: string };
  address: string; hours: string;
  legal: { name: string; inn: string; kpp: string; ogrn: string };
  docs: { consent: string; privacy: string; card: string };
}

// types/requests.ts
export type RequestKind = 'general' | 'product_rfq' | 'one_click' | 'service';
export type Analogue = 'none' | 'allowed' | 'requested';
export interface SiteRequestItem {
  siteProductId?: string; brand?: string; catalogNumber?: string; cas?: string;
  name: string; packaging?: string; quantity: number; unit: 'pack' | PackUnit;
  analogue: Analogue; customPackaging: boolean; comment?: string; pageUrl?: string;
}
export interface SiteRequestPayload {
  kind: RequestKind;
  lang: 'ru' | 'en';
  customer: { name: string; company: string; phone: string /* E.164 */; email: string; inn?: string; city?: string; comment?: string; marketingConsent: boolean };
  items: SiteRequestItem[];
  attachment?: File;
  personalDataConsent: true;
  antispam: { website: string /* honeypot, должен быть пустым */; elapsedMs: number };
  pageUrl: string;
  attribution?: unknown;       // заполню при сборке (UTM, ClientID и т. п.)
}
```

### 7.2. Дерево каталога (`data/mock/categories.ts`)
- Стандартные образцы `/catalog/reference-standards/` → EDQM `…/edqm/`, USP `…/usp/`, British Pharmacopoeia `…/british-pharmacopoeia/`, LGC `…/lgc/`, Merck `…/merck/`, Стандарты примесей `…/impurity-standards/`
- Реактивы `/catalog/reagents/`
- Расходные материалы для хроматографии `/catalog/chromatography/` → Колонки для ВЭЖХ `…/hplc-columns/`, Фильтры `…/filters/`, Предколонки `…/precolumns/`, Фитинги `…/fittings/`
- Референтные лекарственные препараты `/catalog/reference-drugs/`
- Микроорганизмы и биологические стандарты `/catalog/biological-standards/`
- Лабораторное оборудование `/catalog/laboratory-equipment/`
- Лабораторная посуда и тара `/catalog/laboratory-glassware/`
- Фармакопеи и справочники `/catalog/pharmacopeias/`

### 7.3. Функции данных (`lib/api.ts`)
Изоморфные (работают и на сервере, и в клиенте), сейчас возвращают моки с задержкой ~300 мс. Позже я заменю тела на `fetch` к `/api/v1/public/*` — **сигнатуры не меняй**.

```ts
getSiteSettings(): Promise<SiteSettings>
getHomeContent(locale: 'ru' | 'en'): Promise<HomeContent>
getCatalogTree(locale: 'ru' | 'en'): Promise<Category[]>
getHomeProducts(p: { sort: 'popular' | 'alpha'; offset: number; limit: number; locale: 'ru' | 'en' }): Promise<{ items: ProductPreview[]; total: number }>
submitSiteRequest(p: SiteRequestPayload): Promise<{ siteRequestId: string; number: string }>   // number вида 'S-2026-000123'
subscribe(p: { email: string; personalDataConsent: true; marketingConsent: true; source: 'home' }): Promise<{ ok: true }>
```

Моки товаров (`data/mock/products.ts`) — **это заглушки для вёрстки, не реальные данные**. Возьми 14 позиций ниже; `getHomeProducts` выдаёт их циклично с суффиксом в `id`/`slug`, чтобы `total = 36` и «Загрузить ещё» можно было нажать дважды. «Популярные» — порядок списка, «По алфавиту» — `localeCompare` по `name`.

| # | name | brand | кат. № / P/N | CAS | фасовки | статус | тип |
|---|---|---|---|---|---|---|---|
| 1 | Oxcarbazepine CRS | EDQM | Y0001897 | 28721-07-5 | 100 мг | on_request | standard |
| 2 | Paracetamol CRS | EDQM | P0300000 | 103-90-2 | 100 мг | on_request | standard |
| 3 | Carbamazepine Reference Standard | USP | 1100000 | 298-46-4 | 200 мг | in_stock | standard |
| 4 | Metformin Hydrochloride Reference Standard | USP | 1396309 | 1115-70-4 | 200 мг | in_stock | standard |
| 5 | 10,11-Dihydrocarbamazepine (Carbamazepine EP Impurity A) | LGC | MM0080.02 | 3564-73-6 | 10 мг, 25 мг, 50 мг | on_request | standard |
| 6 | Omeprazole Sulfone (Omeprazole EP Impurity D) | SynZeal | SZ-O004004 | 88546-55-8 | 10 мг, 25 мг; customPackaging | on_request | standard |
| 7 | Licarbazepine (10,11-Dihydro-10-hydroxy-5H-dibenz[b,f]azepine-5-carboxamide), Pharmaceutical Secondary Standard; Certified Reference Material | Merck | PHR0000 | 29331-92-8 | 50 мг | on_request | standard — **длинное название для проверки обрезки** |
| 8 | Acetonitrile, gradient grade for liquid chromatography | Merck | 1.00030 | 75-05-8 | 1 л, 2,5 л | in_stock | standard |
| 9 | Methyl orange (C.I. 13025), ACS reagent | Macklin | M813573 | 547-58-0 | 25 г, 100 г | on_request | standard |
| 10 | Ibuprofen CRS | EDQM | I0050000 | 15687-27-1 | 100 мг | in_stock | standard |
| 11 | XBridge C18 Column, 130 Å, 5 µm, 4.6 mm × 150 mm | Waters | 186003116 | — | 1 шт. | in_stock | equipment |
| 12 | ZORBAX Eclipse Plus C18, 4.6 × 150 mm, 5 µm | Agilent | 959993-902 | — | 1 шт. | on_request | equipment |
| 13 | Escherichia coli (Migula) Castellani and Chalmers, lyophilized | ATCC | 25922 | — | 1 ампула | on_request | other |
| 14 | European Pharmacopoeia, online subscription (1 year) | EDQM | PH-EUR-ONLINE | — | 1 шт. | on_request | other |

У товаров 1, 4, 11 укажи `image` с путями `/images/products/mock-1.webp` и т. п. (файлов нет — `ProductImage` при ошибке загрузки показывает `VialPlaceholder`). У остальных `image` нет → сразу `VialPlaceholder`.

`data/mock/settings.ts`: телефон `+7 495 234 28 63`, `info@ogk-chem.ru`, `order@ogk-chem.ru`, адрес «129301, Москва, ул. Касаткина, д. 8, помещ. 1/1», часы «пн–пт 9:00–18:00», ООО «ОГК-ХИМ», ИНН 9717188828, КПП 771701001, ОГРН 1267700023997, документы `/files/soglasie.pdf`, `/files/politika.pdf`, `/files/kartochka.pdf`.

### 7.4. Изображения (пути; файлы положу сам)
`/images/brand/logo.svg`, `/images/brand/logo-secondary.svg`, `/images/home/hero-1.webp`, `hero-2.webp`, `hero-3.webp` (1600×1000), `/images/home/promo-vial.webp` (600×800), `/images/home/service-supply.webp`, `service-logistics.webp`, `service-customs.webp` (800×800), `/images/home/logo-blur.webp` (900×400), `/images/brands/{slug}.svg`, `/images/footer/globe.svg`, `/images/footer/globe-text.svg`, иконки бейджей hero — `lucide-react` (`ShieldCheck`, `Globe`).
Пока файлов нет, вёрстка не должна разваливаться: у блоков с картинками задай размеры/соотношение сторон и фон `surface`.

---

## 8. Формы (общие правила для всех форм сайта)

- react-hook-form + zod, валидация при уходе из поля и при отправке; ошибки — текстом под полем на языке интерфейса.
- E-mail — стандартная проверка формата.
- `PhoneInput` (`lib/phone.ts`): при вводе с `+7`/`8`/`9` — маска `+7 (999) 999-99-99`; иначе свободный международный ввод `+` и 10–15 цифр. Перед отправкой — нормализация в E.164 (`+79991234567`; `8XXXXXXXXXX` → `+7XXXXXXXXXX`). `type="tel"`, `inputMode="tel"`, `autoComplete="tel"`.
- Правильные `autoComplete`: `name`, `organization`, `email`, `tel`.
- Антиспам: скрытое поле-ловушка `website` (вне экрана, `tabIndex={-1}`, `autoComplete="off"`, `aria-hidden`), время от монтирования формы до отправки — в `antispam.elapsedMs`.
- Состояния: обычное → отправка (кнопка `disabled`, спиннер, `aria-busy`) → успех (`FormStatus`: «Заявка № {number} принята. Ответим в течение 2 рабочих часов») → ошибка («Не удалось отправить. Проверьте соединение и попробуйте ещё раз», **введённые данные сохраняются**). Статус объявляется через `aria-live="polite"`.
- События: `form_start` при первом фокусе в форме (один раз), `form_submit` при успехе `{ form_type, page }`.

---

## 9. Аналитика (`lib/analytics.ts`)

```ts
type AnalyticsEvent = 'form_start' | 'form_submit' | 'quote_request' | 'product_request' | 'add_to_rfq'
  | 'click_phone' | 'click_email' | 'download_document' | 'site_search' | 'search_no_results'
  | 'catalog_filter' | 'product_view' | 'brand_view' | 'service_view' | 'subscribe' | 'bulk_upload';
export function track(event: AnalyticsEvent, params?: Record<string, unknown>): void
```
Пишет в `window.dataLayer` (создать, если нет); в dev — дублирует в `console.debug`. Счётчики Метрики и GA4 **не подключать** — только событийный слой и проверка `hasAnalyticsConsent()` из `lib/consent.ts`. На главной используются: `form_start`, `form_submit`, `product_request`, `add_to_rfq`, `click_phone`, `click_email`, `subscribe`.

---

## 10. SEO главной

- `generateMetadata`: title «Стандартные образцы, реактивы и оборудование для фармлабораторий — ОГК-ХИМ»; description «Поставка стандартных образцов EDQM, USP, LGC, реактивов, расходных материалов для ВЭЖХ и лабораторного оборудования для фармацевтических лабораторий. Запрос КП — ответ в течение 2 рабочих часов.»; `alternates.canonical` `https://www.ogk-chem.ru/`; `alternates.languages`: `ru` → `/`, `en` → `/en/`, `x-default` → `/`; Open Graph с теми же title/description. `metadataBase` — `https://www.ogk-chem.ru`.
- `JsonLd` на главной: `Organization` (name «ОГК-ХИМ», legalName «ООО «ОГК-ХИМ»», url, logo, email, telephone, taxID, PostalAddress с почтовым индексом, городом, улицей, `addressCountry: 'RU'`) и `WebSite` с `SearchAction` (`https://www.ogk-chem.ru/search/?q={search_term_string}`). Данные — из `getSiteSettings()`.
- Один `<h1>`, логичная иерархия `h2`/`h3`, хлебных крошек на главной нет.
- `<html lang>` по локали.

---

## 11. Доступность и производительность

- WCAG 2.1 AA: контраст (токены выше уже подобраны, не осветляй вторичный текст сильнее `text-secondary`), видимый фокус, всё работает с клавиатуры, правильные роли и ARIA у слайдера, аккордеона, мегаменю, диалогов, радиогрупп.
- `prefers-reduced-motion: reduce` — выключить масштабирование hero, вращение глобуса, смену строк в «У нас вы сможете», анимацию счётчика.
- Тач-цели не меньше 44×44 px.
- Core Web Vitals: LCP ≤ 2,5 с (hero-картинка первого слайда — `priority`, остальные слайды — без `priority`), CLS < 0,1 (резервируй место под картинки, шрифт — `display: swap` + `adjustFontFallback`), INP < 200 мс (никаких тяжёлых обработчиков скролла — `IntersectionObserver`/`requestAnimationFrame`, пассивные слушатели).
- Без горизонтальной прокрутки страницы на 360 px.

---

## 12. Чего НЕ делать

- Не показывать цены, скидки, «Купить», рейтинги, отзывы, «избранное»-сердечки, бейджи NEW / HOT / BESTSELLER (они есть в референсах, нам не нужны).
- Не брать из референсов цвета, шрифты и светлые фоны (синие и розовые кнопки, белые карточки) — референсы только про структуру.
- Не копировать тексты и данные Химмед и других конкурентов.
- Не придумывать факты: цифры, сроки, сертификаты, клиентов, отзывы, награды — только то, что есть в промпте.
- Не делать светлую тему и переключатель темы.
- Не хардкодить тексты в JSX: строки интерфейса — в `messages/*.json`, контент — в `data/mock/*`.
- Не использовать `<div onClick>` вместо ссылок и кнопок, не вкладывать кнопки в ссылки.
- Не делать второй `<h1>`.
- Не делать автопрокрутку без кнопки паузы.
- Не подключать счётчики аналитики и не ставить аналитические cookies до согласия.
- Не добавлять секции, которых нет в разделе 6.

---

## 13. Самопроверка перед ответом

- [ ] Все файлы из раздела 3 на месте, имена и props совпадают.
- [ ] Токены из 4.1 заданы в `@theme`, в компонентах нет «сырых» hex.
- [ ] Ровно один `<h1>`; у всех секций есть `<h2>` и `aria-labelledby`.
- [ ] Главная рендерится на сервере с текстами, первыми 12 товарами и всеми ссылками без JS.
- [ ] «Популярные / По алфавиту» не меняет URL; «Загрузить ещё» добавляет по 12 и исчезает в конце.
- [ ] «В корзину» → «В корзине», счётчик в шапке обновляется и переживает перезагрузку, нет ошибок гидрации.
- [ ] «Заказать в 1 клик» открывает окно с товаром, фасовкой, количеством и выбором аналогов; фокус заперт, Esc закрывает.
- [ ] Формы: валидация, маска телефона, E.164, ловушка-поле, состояния отправки/успеха/ошибки, отдельные чекбоксы согласий.
- [ ] Цен нигде нет.
- [ ] Вёрстка проверена на 360, 768, 1024, 1440 px, нет горизонтальной прокрутки.
- [ ] Клавиатура: Tab проходит шапку, мегаменю, слайдер, карточки, аккордеон, формы; фокус всегда виден.
- [ ] `prefers-reduced-motion` отключает все анимации.
- [ ] `messages/ru.json` и `messages/en.json` содержат одинаковые ключи.
- [ ] `npm run build` и `npm run lint` проходят без ошибок и предупреждений TypeScript.
