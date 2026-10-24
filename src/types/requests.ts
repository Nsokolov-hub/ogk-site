import type { PackUnit } from './catalog';

export type RequestKind = 'general' | 'product_rfq' | 'one_click' | 'service';

/** none — только этот товар, allowed — готовы рассмотреть аналоги, requested — подберите аналог */
export type Analogue = 'none' | 'allowed' | 'requested';

export interface SiteRequestItem {
  siteProductId?: string;
  brand?: string;
  catalogNumber?: string;
  cas?: string;
  name: string;
  packaging?: string;
  quantity: number;
  unit: 'pack' | PackUnit;
  analogue: Analogue;
  customPackaging: boolean;
  comment?: string;
  pageUrl?: string;
}

export interface SiteRequestPayload {
  kind: RequestKind;
  lang: 'ru' | 'en';
  customer: {
    name: string;
    company: string;
    /** E.164: +79991234567 */
    phone: string;
    email: string;
    inn?: string;
    city?: string;
    comment?: string;
    marketingConsent: boolean;
  };
  items: SiteRequestItem[];
  attachment?: File;
  personalDataConsent: true;
  antispam: {
    /** Поле-ловушка, у человека всегда пустое */
    website: string;
    elapsedMs: number;
  };
  pageUrl: string;
  /** Форма-источник: rfq, one_click, service, home, category, product, search… — для отчётов и «спроса без товара» */
  formType?: string;
  /** Желаемый срок поставки, YYYY-MM-DD */
  desiredDate?: string;
  /** Заявка на услугу (RFQ-08): slug услуги и значения её полей */
  service?: { slug: string; name: string; fields: Record<string, string> };
  /** Токен SmartCaptcha; его добавляет submitSiteRequest после ответа 428 */
  captchaToken?: string;
  /*
   * Источник визита (UTM, первое и последнее касание, ClientID) форма не передаёт: middleware хранит его
   * в cookie ogk_attr, а API читает её сам (ТЗ 15.3).
   */
}

export interface SiteRequestResult {
  siteRequestId: string;
  number: string;
}
