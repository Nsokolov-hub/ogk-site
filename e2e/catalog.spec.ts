import { expect, test } from '@playwright/test';
import { dismissCookies, expectRequestNumber, fillContacts } from './helpers';

test.describe('Каталог и заявки (ТЗ 3.2)', () => {
  test('SC-01: поиск по номеру → корзина → заявка', async ({ page }) => {
    await page.goto('/');
    await dismissCookies(page);
    const search = page.getByRole('searchbox', { name: 'Поиск по каталогу' }).filter({ visible: true }).first();
    await search.fill('Y0001897');
    // Первая подсказка — карточка EDQM (SRCH-04)
    const first = page.locator('a[data-suggest]').filter({ visible: true }).first();
    await expect(first).toContainText('Oxcarbazepine CRS');
    await expect(first).toContainText('EDQM');
    await first.click();
    await expect(page).toHaveURL(/\/product\/edqm-y0001897-oxcarbazepine-crs\/$/);
    await page.getByRole('button', { name: 'В корзину' }).first().click();
    await page.goto('/rfq/');
    await expect(page.getByText('Y0001897').first()).toBeVisible();
    await fillContacts(page);
    await page.getByRole('button', { name: 'Отправить запрос' }).click();
    await expectRequestNumber(page);
  });

  test('SC-02: запрос по списку', async ({ page }) => {
    await page.goto('/rfq/#bulk');
    await dismissCookies(page);
    await page.getByLabel('Список позиций').fill('Y0001897 2\nP0300000;3\nнет такой позиции 123');
    await page.getByRole('button', { name: /Найти в каталоге/ }).click();
    await expect(page.getByText(/Найдено точно: 2/)).toBeVisible();
    await page.getByRole('button', { name: /Добавить в корзину/ }).click();
    await expect(page.getByText(/Добавлен[оа]? \d+ позици/)).toBeVisible();
  });

  test('SC-03: пустая выдача → форма с подставленным запросом', async ({ page }) => {
    await page.goto('/search/?q=несуществующий%20стандарт%20xyz');
    await dismissCookies(page);
    await expect(page.getByText(/Такой позиции нет на сайте/).first()).toBeVisible();
    await expect(page.getByLabel(/^Опишите запрос/)).toHaveValue(/несуществующий стандарт xyz/);
  });

  test('SC-04: категория → фильтр → карточка → заказ в 1 клик, источник визита сохранён', async ({ page, context }) => {
    await page.goto('/catalog/reference-standards/edqm/?utm_source=yandex&utm_medium=cpc&utm_campaign=e2e');
    await dismissCookies(page);
    const cookies = await context.cookies();
    expect(cookies.some((c) => c.name === 'ogk_attr')).toBeTruthy();
    await expect(page.getByText(/Найден[оа]? \d+ позици/)).toBeVisible();
    // Фильтр «Фасовка» → «Применить»: выбор попадает в адрес (URL-06)
    await page.getByRole('checkbox', { name: /^100 мг/ }).first().check();
    await page.getByRole('button', { name: 'Применить' }).first().click();
    await expect(page).toHaveURL(/pack=100-mg/);
    await page.getByRole('link', { name: /Oxcarbazepine CRS/ }).first().click();
    await expect(page).toHaveURL(/\/product\//);
    await page.getByRole('button', { name: 'Заказать в 1 клик' }).first().click();
    const dialog = page.getByRole('dialog');
    await fillContacts(page, dialog);
    await dialog.getByRole('button', { name: 'Отправить запрос' }).click();
    await expect(dialog.getByText(/Запрос № S-\d+ отправлен/)).toBeVisible();
  });
});
