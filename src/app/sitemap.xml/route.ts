import { sitemapIndexXml } from '@/lib/sitemap';

/** /sitemap.xml — индекс файлов Sitemap (SEO-04) */
export const dynamic = 'force-dynamic';

export async function GET() {
  return new Response(await sitemapIndexXml(), {
    headers: { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
  });
}
