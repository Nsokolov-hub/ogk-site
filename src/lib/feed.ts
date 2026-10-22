/**
 * YML-фид для Яндекс Директа (ТЗ 15.4): товарные кампании, динамические объявления, смарт-баннеры.
 * В фид попадают опубликованные позиции выбранных разделов и брендов; подконтрольные вещества — никогда (5.2.1).
 *
 * Цены. На сайте их нет, поэтому <price> не выводим: offers без цены допустимы не для всех форматов Директа —
 * это открытый вопрос ТЗ 15.4, до запуска сверяем требования и выбираем типы кампаний.
 * Когда появятся публичные цены (P2), добавим <price> только позициям с флагом показа.
 */
import type { Category, ProductPreview } from '@/types/catalog';
import { catalogTree } from '@/data/mock/categories';
import { catalogSettings, siteSettings } from '@/data/mock/settings';
import { catalogProducts } from '@/data/mock/catalog-products';
import { getProductDetail } from './product-api';
import { absoluteUrl, SITE_NAME } from './seo';

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');

/** Числовые id категорий для YML: в проде — id из базы, здесь — порядок в дереве */
function feedCategories() {
  const list: { id: number; parentId?: number; name: string; path: string }[] = [];
  let id = 0;
  const walk = (cats: Category[], parentPath?: string, parentId?: number) => {
    for (const c of cats) {
      id += 1;
      const path = parentPath ? `${parentPath}/${c.slug}` : c.slug;
      list.push({ id, parentId, name: c.name, path });
      if (c.children?.length) walk(c.children, path, id);
    }
  };
  walk(catalogTree);
  return list;
}

export function feedProducts(): ProductPreview[] {
  const { categories, brands } = catalogSettings.feed;
  return catalogProducts.filter(
    (p) =>
      !p.controlled &&
      !p.discontinued &&
      categories.some((c) => p.categorySlug === c || p.categorySlug.startsWith(`${c}/`)) &&
      (!brands.length || brands.includes(p.brand.slug)),
  );
}

/** Яндекс принимает изображения JPEG, PNG, WebP; SVG-структуры в фид не отдаём */
const feedPicture = (p: ProductPreview) =>
  p.image && !p.image.src.endsWith('.svg') ? `${siteSettings.siteUrl}${p.image.src}` : undefined;

export function yandexDirectYml(now = new Date()): string {
  const cats = feedCategories();
  const catId = new Map(cats.map((c) => [c.path, c.id]));
  const products = feedProducts();
  // В фиде только разделы, из которых есть позиции, и их родители
  const used = new Set<number>();
  for (const p of products) {
    const id = catId.get(p.categorySlug);
    if (!id) continue;
    used.add(id);
    const parent = cats.find((c) => c.id === id)?.parentId;
    if (parent) used.add(parent);
  }

  const categoriesXml = cats
    .filter((c) => used.has(c.id))
    .map((c) => `      <category id="${c.id}"${c.parentId ? ` parentId="${c.parentId}"` : ''}>${esc(c.name)}</category>`)
    .join('\n');

  const offersXml = products
    .map((p) => {
      const d = getProductDetail(p.slug);
      const description = (d?.description ?? []).join(' ').slice(0, 3000);
      const picture = feedPicture(p);
      const params = [
        p.cas ? `        <param name="CAS">${esc(p.cas)}</param>` : '',
        p.packagings.length ? `        <param name="Фасовка">${esc(p.packagings.map((x) => x.label).join(', '))}</param>` : '',
        p.customPackaging ? '        <param name="Фасовка под запрос">да</param>' : '',
      ].filter(Boolean);
      return [
        // available="false" — позиция под заказ: так у всех позиций каталога (ТЗ 9.6)
        `      <offer id="${esc(p.id)}" available="false">`,
        `        <url>${esc(absoluteUrl('ru', `/product/${p.slug}/`))}</url>`,
        `        <name>${esc(p.name)}</name>`,
        `        <vendor>${esc(p.brand.name)}</vendor>`,
        `        <vendorCode>${esc(p.catalogNumber)}</vendorCode>`,
        `        <categoryId>${catId.get(p.categorySlug) ?? catId.get(p.categorySlug.split('/')[0])}</categoryId>`,
        picture ? `        <picture>${esc(picture)}</picture>` : '',
        description ? `        <description>${esc(description)}</description>` : '',
        '        <sales_notes>Цена по запросу, КП за 2 рабочих часа</sales_notes>',
        ...params,
        '      </offer>',
      ]
        .filter(Boolean)
        .join('\n');
    })
    .join('\n');

  // Дата в формате YML: YYYY-MM-DDTHH:mm+03:00 (московское время)
  const msk = new Date(now.getTime() + 3 * 3600_000).toISOString().slice(0, 16);

  return `<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="${msk}+03:00">
  <shop>
    <name>${esc(SITE_NAME)}</name>
    <company>${esc(siteSettings.legal.name)}</company>
    <url>${esc(siteSettings.siteUrl)}/</url>
    <currencies>
      <currency id="RUR" rate="1"/>
    </currencies>
    <categories>
${categoriesXml}
    </categories>
    <offers>
${offersXml}
    </offers>
  </shop>
</yml_catalog>
`;
}
