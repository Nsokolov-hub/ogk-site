import { sitemapIndexXml } from '@/lib/sitemap';

/** /sitemap.xml — индекс файлов Sitemap (SEO-04) */
export const revalidate = 3600;

export function GET() {
  return new Response(sitemapIndexXml(), { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
