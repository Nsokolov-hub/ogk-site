import { getTranslations } from 'next-intl/server';
import type { Locale } from '@/i18n/routing';
import type { HomeContent } from '@/types/content';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { categoryShortNames } from '@/data/mock/categories';
import { getCatalogTree, getHomeProducts } from '@/lib/api';
import { ProductsGrid } from './ProductsGrid';

/** «Каталог товаров»: кнопки разделов, переключатель сортировки, 12 карточек с сервера и «Загрузить ещё» */
export async function ProductsSection({ content, locale }: { content: HomeContent['products']; locale: Locale }) {
  const t = await getTranslations('home.products');
  const [tree, initial] = await Promise.all([
    getCatalogTree(locale),
    getHomeProducts({ sort: 'popular', offset: 0, limit: 12, locale }),
  ]);

  return (
    <section aria-labelledby="products-title" className="mt-24 md:mt-32 lg:mt-40">
      <Container>
        <SectionHeading
          id="products-title"
          title={content.title}
          accent={content.accent}
          subtitle={content.subtitle}
        />
        <nav aria-label={t('categories')}>
          <ul className="flex flex-wrap gap-2">
            {tree.map((c) => (
              <li key={c.slug}>
                <Button href={c.href} variant="menu" size="s">
                  {categoryShortNames[c.slug] ?? c.name}
                </Button>
              </li>
            ))}
          </ul>
        </nav>
        <ProductsGrid
          initial={initial.items}
          initialTotal={initial.total}
          locale={locale}
          extraAction={
            <Button href="/catalog/" variant="secondary" size="m">
              {t('allCatalog')}
            </Button>
          }
        />
      </Container>
    </section>
  );
}
