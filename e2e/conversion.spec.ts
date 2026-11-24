import { expect, test, type Locator, type Page, type Request } from '@playwright/test';
import type { SiteRequestPayload } from '../src/types/requests';
import { dismissCookies } from './helpers';

const MULTI_PACK = 'lgc-mm0080-02-10-11-dihydrocarbamazepine';
const CUSTOM_PACK = 'synzeal-sz-o004004-omeprazole-sulfone';
const fixtureFile = { name: 'laboratory-request.csv', mimeType: 'text/csv', buffer: Buffer.from('catalogNumber,quantity\n1235831-1AMP,9\n') };

function payloadOf(request: Request): SiteRequestPayload {
  const body = request.postDataBuffer()?.toString('utf8') ?? '';
  const payload = body.match(/name="payload"\r\n\r\n([\s\S]*?)\r\n--/);
  if (!payload) throw new Error('Expected multipart request payload');
  return JSON.parse(payload[1]) as SiteRequestPayload;
}

async function interceptSubmit(page: Page) {
  const submissions: { payload: SiteRequestPayload; body: string }[] = [];
  await page.route(/\/api\/v1\/public\/requests\/?$/, async (route) => {
    if (route.request().method() !== 'POST') return route.continue();
    submissions.push({ payload: payloadOf(route.request()), body: route.request().postDataBuffer()?.toString('utf8') ?? '' });
    await route.fulfill({ json: { siteRequestId: 'e2e-request', number: 'S-900001' } });
  });
  return submissions;
}

async function emailOnly(scope: Locator) {
  await scope.getByLabel(/^E-mail/).fill('e2e@ogk-chem.ru');
  await scope.getByLabel(/^E-mail/).press('Tab');
  await scope.getByLabel(/Подтверждаю согласие на обработку персональных данных/).check();
}

test.describe('Закупочные сценарии и сохранение намерения покупателя', () => {
  test('выбранная фасовка, количество и аналоги переходят в один клик и API', async ({ page }) => {
    const submissions = await interceptSubmit(page);
    await page.goto(`/product/${MULTI_PACK}/`);
    await dismissCookies(page);
    const panel = page.locator('#product-order');
    const selectedPack = panel.getByRole('radio', { name: '25 мг', exact: true });
    const selectedPackId = await selectedPack.inputValue();
    await selectedPack.press('Space');
    await panel.getByLabel('Количество упаковок', { exact: true }).fill('5');
    await panel.getByRole('radio', { name: 'Готовы рассмотреть аналоги' }).press('Space');
    await panel.getByRole('button', { name: 'Заказать в 1 клик' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByLabel('Количество упаковок', { exact: true })).toHaveValue('5');
    await expect(dialog.getByLabel('Фасовка', { exact: true })).toHaveValue(selectedPackId);
    await expect(dialog.getByLabel('Фасовка', { exact: true }).locator('option:checked')).toHaveText('25 мг');
    await expect(dialog.getByRole('radio', { name: 'Готовы рассмотреть аналоги' })).toBeChecked();
    await emailOnly(dialog);
    await dialog.getByRole('button', { name: 'Отправить запрос' }).click();
    await expect(dialog.getByText(/Запрос № S-900001 отправлен/)).toBeVisible();
    expect(submissions).toHaveLength(1);
    expect(submissions[0].payload.items[0]).toMatchObject({ sitePackagingId: selectedPackId, packaging: '25 мг', quantity: 5, analogue: 'allowed', customPackaging: false });
    expect(submissions[0].payload.customer).toMatchObject({ name: '', company: '', phone: '', email: 'e2e@ogk-chem.ru' });
  });

  test('произвольная фасовка сохраняется и при открытии с нижней мобильной панели', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/product/${CUSTOM_PACK}/`);
    await dismissCookies(page);
    const panel = page.locator('#product-order');
    await panel.getByRole('radio', { name: 'Своя фасовка', exact: true }).press('Space');
    await panel.getByRole('textbox', { name: /Количество в упаковке/ }).fill('7,5');
    await panel.getByLabel('Единица', { exact: true }).selectOption('g');
    await panel.getByLabel('Количество упаковок', { exact: true }).fill('9');
    await panel.getByRole('radio', { name: 'Готовы рассмотреть аналоги' }).press('Space');
    // Blur commits the quantity draft before the sticky CTA is used.
    await panel.getByRole('heading').click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.getByRole('button', { name: 'Запросить цену', exact: true }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByLabel('Фасовка', { exact: true })).toHaveValue('__custom__');
    await expect(dialog.getByRole('textbox', { name: /Количество в упаковке/ })).toHaveValue('7,5');
    await expect(dialog.getByLabel('Единица', { exact: true })).toHaveValue('g');
    await expect(dialog.getByLabel('Количество упаковок', { exact: true })).toHaveValue('9');
    await expect(dialog.getByRole('radio', { name: 'Готовы рассмотреть аналоги' })).toBeChecked();
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Запросить цену', exact: true })).toBeFocused();
  });

  test('общую заявку можно отправить с файлом и e-mail без повторного ввода списка', async ({ page }) => {
    const submissions = await interceptSubmit(page);
    await page.goto('/contacts/');
    await dismissCookies(page);
    const form = page.locator('form').filter({ has: page.getByLabel(/^Опишите запрос/) });
    await emailOnly(form);
    await form.locator('input[type="file"]').setInputFiles(fixtureFile);
    await form.getByRole('button', { name: 'Отправить', exact: true }).click();
    await expect(page.getByText(/S-900001/)).toBeVisible();
    expect(submissions).toHaveLength(1);
    expect(submissions[0].payload).toMatchObject({ kind: 'general', items: [], customer: { name: '', company: '', phone: '', email: 'e2e@ogk-chem.ru' } });
    expect(submissions[0].body).toContain('filename="laboratory-request.csv"');
  });

  test('корзина принимает файл без ручного создания товарных строк', async ({ page }) => {
    const submissions = await interceptSubmit(page);
    await page.goto('/rfq/#file');
    await dismissCookies(page);
    const form = page.locator('#rfq-form form');
    await emailOnly(form);
    await form.locator('input[type="file"]').setInputFiles(fixtureFile);
    await form.getByRole('button', { name: 'Отправить запрос' }).click();
    await expect(page.getByText(/S-900001/)).toBeVisible();
    await expect(page.getByText(/laboratory-request.csv/)).toBeVisible();
    expect(submissions).toHaveLength(1);
    expect(submissions[0].payload).toMatchObject({ kind: 'product_rfq', items: [], customer: { email: 'e2e@ogk-chem.ru', name: '', phone: '', company: '' } });
    expect(submissions[0].body).toContain('filename="laboratory-request.csv"');
  });

  test('неточное совпадение и фасовка требуют явного подтверждения', async ({ page, request }) => {
    const response = await request.get(`/api/v1/public/products/${MULTI_PACK}/`);
    const { product } = await response.json();
    product.packagings = product.packagings.map((pack: { id: string; label: string }, index: number) => ({ ...pack, catalogNumber: `${product.catalogNumber}-${index + 1}` }));
    await page.route(/\/api\/v1\/public\/search\/batch\/?(?:\?.*)?$/, (route) => route.fulfill({ json: { lines: [{ line: 'Carbamazepine impurity 9', query: 'Carbamazepine impurity', quantity: 9, status: 'multiple', candidates: [{ ...product, match: 'name', matchedPackagingId: null }] }] } }));
    await page.goto('/rfq/#bulk');
    await dismissCookies(page);
    await page.getByLabel('Список позиций').fill('Carbamazepine impurity 9');
    await page.getByRole('button', { name: /Найти в каталоге/ }).click();
    const add = page.getByRole('button', { name: /Добавить в корзину/ });
    await expect(add).toBeDisabled();
    await page.getByLabel('Что добавить', { exact: true }).selectOption(product.id);
    await expect(add).toBeDisabled();
    await page.getByLabel('Фасовка', { exact: true }).selectOption(product.packagings[1].id);
    await add.click();
    await expect(page.getByText(/Добавлен[оа]? 1 позици/)).toBeVisible();
    const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('ogk-rfq') ?? '{}'));
    expect(stored.state.items).toHaveLength(1);
    expect(stored.state.items[0]).toMatchObject({ productId: product.id, quantity: 9, packagingId: product.packagings[1].id, packagingLabel: '25 мг', catalogNumber: `${product.catalogNumber}-2` });
    await page.locator('li').filter({ has: page.getByRole('link', { name: product.name, exact: true }) }).getByLabel('Фасовка', { exact: true }).selectOption(product.packagings[0].id);
    const changed = await page.evaluate(() => JSON.parse(localStorage.getItem('ogk-rfq') ?? '{}'));
    expect(changed.state.items[0].catalogNumber).toBe(`${product.catalogNumber}-1`);
  });

  test('повторная ссылка очищает токен и добавляет подтверждённые строки к существующей корзине', async ({ page }) => {
    const submissions = await interceptSubmit(page);
    const restored = { name: 'Enoxaparin sodium USP reference standard', brand: 'USP', catalogNumber: '1235831-1AMP', packaging: '1 амп.', quantity: 9, unit: 'pack', analogue: 'allowed', customPackaging: false };
    await page.route(/\/api\/v1\/public\/requests\/repeat\/resolve\/?$/, async (route) => {
      expect(route.request().postDataJSON()).toEqual({ token: 'test-only-repeat-token' });
      await route.fulfill({ json: { items: [restored], expiresAt: '2027-01-01T00:00:00Z' } });
    });
    await page.goto(`/product/${MULTI_PACK}/`);
    await dismissCookies(page);
    await page.locator('#product-order').getByRole('button', { name: 'В корзину', exact: true }).click();
    // A fresh navigation retains the cart but must not silently replace it with the repeat list.
    await page.goto('/rfq/#repeat=test-only-repeat-token');
    await expect(page).toHaveURL(/\/rfq\/$/);
    const preview = page.getByRole('region', { name: 'Повторить запрос' });
    await expect(preview.getByText('1235831-1AMP', { exact: false })).toBeVisible();
    await expect(page.locator('#rfq-items')).toHaveText(/1/);
    await preview.getByRole('button', { name: 'Добавить позиции в текущую корзину' }).click();
    await expect(page.locator('#rfq-items')).toHaveText(/2/);
    await emailOnly(page.locator('#rfq-form form'));
    await page.locator('#rfq-form').getByRole('button', { name: 'Отправить запрос' }).click();
    await expect(page.getByText(/S-900001/)).toBeVisible();
    expect(submissions).toHaveLength(1);
    expect(submissions[0].payload.items).toHaveLength(2);
    expect(submissions[0].payload.items[1]).toMatchObject(restored);
    expect(JSON.stringify(submissions[0].payload)).not.toContain('test-only-repeat-token');
  });

  test('главная показывает слайды, пять тематических ссылок и вход в запрос по списку', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    for (const width of [1440, 1024, 768, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto('/');
      await dismissCookies(page);
      const hero = page.getByRole('region', { name: 'Главные предложения', exact: true }).last();
      await expect(hero.getByRole('heading', { level: 1 })).toBeInViewport();
      await hero.getByRole('button', { name: 'Следующий слайд' }).click();
      await expect(hero.getByRole('heading', { name: /хроматографии/ })).toBeVisible();
      const offers = page.locator('.offer-rail');
      await expect(offers.getByRole('link')).toHaveCount(5);
      await expect(offers.getByRole('link', { name: 'Alpha-D-Glucose Monohydrate' })).toHaveAttribute('href', /aozeal-d0147-28/);
      await expect(page.getByRole('link', { name: 'Отправить список', exact: true })).toHaveAttribute('href', '/rfq/#file');
      await expect(page.locator('h1')).toHaveCount(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    }
  });
});
