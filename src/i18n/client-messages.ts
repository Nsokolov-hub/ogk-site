import type { AbstractIntlMessages } from 'next-intl';

/**
 * Разделы словаря, которые нужны в браузере, — их читает хук useTranslations. Остальные (тексты страниц через
 * getTranslations: бренды, статьи, услуги, указатель CAS…) остаются на сервере. Раньше в HTML каждой страницы
 * уходил весь словарь — около 55 КБ (аудит 12.11.2026).
 *
 * Новый раздел в клиентском компоненте — допишите его сюда: scripts/check-client-messages.mjs (npm run lint)
 * не пропустит расхождение.
 */
export const CLIENT_NAMESPACES = [
  'captcha',
  'cartDrawer',
  'catalog',
  'common',
  'cookie',
  'errors',
  'form',
  'header',
  'home',
  'oneClick',
  'product',
  'productPage',
  'rfq',
  'search',
  'serviceForm',
  'siteMenu',
  'subscribe',
  'substancePage',
  'unsubscribe',
] as const;

export function clientMessages(messages: AbstractIntlMessages): AbstractIntlMessages {
  return Object.fromEntries(CLIENT_NAMESPACES.filter((key) => key in messages).map((key) => [key, messages[key]]));
}
