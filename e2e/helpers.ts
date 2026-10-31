import { expect, type Page } from '@playwright/test';

/** Баннер cookie: только необходимые (так же поступил бы осторожный посетитель) */
export async function dismissCookies(page: Page) {
  const button = page.getByRole('button', { name: 'Только необходимые' });
  if (await button.isVisible().catch(() => false)) await button.click();
}

/** Контакты формы заявки; форма закрыта от ботов, поэтому заполняем её не быстрее живого человека */
export async function fillContacts(page: Page, scope = page.locator('body')) {
  // Полная форма: «ФИО», «Наименование организации»; окно «Заказать в 1 клик»: «Имя», «Компания»
  await scope.getByLabel(/^(ФИО|Имя)/).fill('Иван Петров');
  await scope.getByLabel(/^(Наименование организации|Компания)/).fill('ООО «Пример-Фарма»');
  await scope.getByLabel(/^E-mail/).fill('e2e@example.ru');
  await scope.getByLabel(/^Телефон/).fill('+7 999 123-45-67');
  await scope.getByLabel(/Подтверждаю согласие на обработку персональных данных/).check();
  await page.waitForTimeout(3500);
}

export async function expectRequestNumber(page: Page) {
  await expect(page.getByText(/S-\d+/).first()).toBeVisible();
}
