import { expect, type Page } from '@playwright/test';

/** Баннер cookie: только необходимые (так же поступил бы осторожный посетитель) */
export async function dismissCookies(page: Page) {
  const consent = await page.evaluate(() => localStorage.getItem('ogk-cookie-consent'));
  const banner = page.getByRole('region', { name: 'Согласие на использование cookies' });
  if (consent !== 'necessary' && consent !== 'all') {
    // The banner appears after hydration; an immediate isVisible() can miss it and leave it over mobile CTAs.
    const button = banner.getByRole('button', { name: 'Только необходимые', exact: true });
    await expect(button).toBeVisible();
    await button.click();
    await expect.poll(() => page.evaluate(() => localStorage.getItem('ogk-cookie-consent'))).toBe('necessary');
  }
  await expect(banner).not.toBeVisible();
}

/** Контакты формы заявки; форма закрыта от ботов, поэтому заполняем её не быстрее живого человека */
export async function fillContacts(page: Page, scope = page.locator('body')) {
  // Полная форма: «ФИО», «Наименование организации»; окно «Заказать в 1 клик»: «Имя», «Компания»
  await scope.getByLabel(/^(ФИО|Имя)/).fill('Иван Петров');
  await scope.getByLabel(/^(Наименование организации|Компания)/).fill('ООО «Пример-Фарма»');
  await scope.getByLabel(/^E-mail/).fill('e2e@ogk-chem.ru');
  await scope.getByLabel(/^Телефон/).fill('+7 999 123-45-67');
  await scope.getByLabel(/Подтверждаю согласие на обработку персональных данных/).check();
  await page.waitForTimeout(3500);
}

export async function expectRequestNumber(page: Page) {
  await expect(page.getByText(/S-\d+/).first()).toBeVisible();
}
