import { ArrowRight } from 'lucide-react';
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
    <section aria-labelledby="products-title" className="mt-16 md:mt-24 lg:mt-30">
      <Container>
        <SectionHeading
          id="products-title"
          title={content.title}
          accent={content.accent}
          subtitle={content.subtitle}
          action={
            <Button href="/catalog/" variant="ghost" size="m" icon={<ArrowRight aria-hidden size={20} strokeWidth={1.5} />}>
              {t('allCatalog')}
            </Button>
          }
        />
        <nav aria-label={t('categories')}>
          <ul className="scroll-row -mx-4 gap-2 px-4 md:-mx-6 md:px-6 lg:mx-0 lg:flex-wrap lg:overflow-visible lg:px-0">
            {tree.map((c) => (
              <li key={c.slug}>
                <Button href={c.href} variant="menu" size="s">
                  {categoryShortNames[c.slug] ?? c.name}
                </Button>
              </li>
            ))}
          </ul>
        </nav>
        <ProductsGrid initial={initial.items} initialTotal={initial.total} locale={locale} />
      </Container>
    </section>
  );
}
