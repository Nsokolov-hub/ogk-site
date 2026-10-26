/**
 * YML-фид для Яндекс Директа (ТЗ 15.4): товарные кампании, динамические объявления, смарт-баннеры.
 * В фид попадают опубликованные позиции выбранных разделов и брендов; подконтрольные вещества — никогда (5.2.1).
 *
 * Цены. На сайте их нет, поэтому <price> не выводим: offers без цены допустимы не для всех форматов Директа —
 * это открытый вопрос ТЗ 15.4, до запуска сверяем требования и выбираем типы кампаний.
 * Когда появятся публичные цены (P2), добавим <price> только позициям с флагом показа.
 */
import { getSiteSettings } from './api';
import type { Schemas } from './api-types';
import { api } from './backend';
import { absoluteUrl, SITE_NAME } from './seo';

type FeedNode = Schemas['CategoryNode'];

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');

/** Числовые id категорий для YML — порядок в дереве каталога */
function feedCategories(tree: FeedNode[]) {
  const list: { id: number; parentId?: number; name: string; path: string }[] = [];
  let id = 0;
  const walk = (nodes: FeedNode[], parentId?: number) => {
    for (const c of nodes) {
      id += 1;
      list.push({ id, parentId, name: c.nameRu, path: c.path });
      if (c.children?.length) walk(c.children, id);
    }
  };
  walk(tree);
  return list;
}

/** Яндекс принимает изображения JPEG, PNG, WebP; SVG-структуры в фид не отдаём */
const feedPicture = (siteUrl: string, src?: string | null) => (src && !src.endsWith('.svg') ? `${siteUrl}${src}` : undefined);

export async function yandexDirectYml(now = new Date()): Promise<string> {
  const siteSettings = await getSiteSettings('ru');
  // Состав фида (разделы и бренды) задаётся настройкой каталога; подконтрольные и снятые позиции API не отдаёт
  const feed = await api<Schemas['FeedOut']>('/public/catalog/feed', undefined, { revalidate: 21600, tags: ['catalog'] });
  const cats = feedCategories(feed.categories);
  const catId = new Map(cats.map((c) => [c.path, c.id]));
  const products = feed.items;
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
      const description = (p.description ?? '').slice(0, 3000);
      const picture = feedPicture(siteSettings.siteUrl, p.image);
      const params = [
        p.cas ? `        <param name="CAS">${esc(p.cas)}</param>` : '',
        p.packagings?.length ? `        <param name="Фасовка">${esc(p.packagings.join(', '))}</param>` : '',
        p.customPackaging ? '        <param name="Фасовка под запрос">да</param>' : '',
      ].filter(Boolean);
      return [
        // available="false" — позиция под заказ: так у всех позиций каталога (ТЗ 9.6)
        `      <offer id="${esc(p.id)}" available="false">`,
        `        <url>${esc(absoluteUrl('ru', `/product/${p.slug}/`))}</url>`,
        `        <name>${esc(p.name)}</name>`,
        `        <vendor>${esc(p.brand)}</vendor>`,
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
