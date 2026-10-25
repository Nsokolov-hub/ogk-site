import { sitemapFileXml } from '@/lib/sitemap';

/** /sitemaps/{pages|catalog|products-N|substances|brands|services|articles}.xml (SEO-04) */
export const dynamic = 'force-dynamic';

export async function GET(_request: Request, { params }: { params: Promise<{ file: string }> }) {
  const { file } = await params;
  const name = file.replace(/\.xml$/, '');
  const xml = file.endsWith('.xml') ? await sitemapFileXml(name) : null;
  if (!xml) return new Response('Not found', { status: 404 });
  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' } });
}
