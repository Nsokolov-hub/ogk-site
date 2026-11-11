'use client';

import { useEffect, useState } from 'react';
import { Phone } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { ProductPreview } from '@/types/catalog';
import { Button } from '@/components/ui/Button';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';
import { useOneClickStore } from '@/lib/one-click-store';

/** Пока на экране один из этих блоков, панель не нужна: действие уже перед глазами, а подвал она бы закрыла */
const HIDE_NEAR = ['#product-order', '#product-request', 'footer'];

/**
 * Нижняя панель карточки на телефоне и планшете (аудит 11.11.2026): на первом экране карточки там только название
 * и изображение, кнопки заказа и телефон — ниже. Панель держит «Запросить цену» и звонок под рукой и прячется,
 * когда видны блок фасовок, форма запроса или подвал. Кнопка открывает то же окно, что и «Заказать в 1 клик».
 */
export function ProductStickyBar({ product, phone }: { product: ProductPreview; phone: { display: string; href: string } }) {
  const t = useTranslations('productPage.order');
  const openOneClick = useOneClickStore((s) => s.open);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const targets = HIDE_NEAR.map((selector) => document.querySelector(selector)).filter((el): el is Element => el !== null);
    const inView = new Set<Element>();
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) inView.add(entry.target);
        else inView.delete(entry.target);
      }
      setVisible(inView.size === 0);
    });
    targets.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div
      aria-hidden={visible ? undefined : true}
      inert={!visible}
      className={cn(
        'glass-overlay fixed inset-x-0 bottom-0 z-[80] flex items-center gap-2 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]',
        'shadow-[0_-8px_24px_rgb(0_0_0/0.3)] transition-transform duration-300 motion-reduce:transition-none lg:hidden',
        visible ? 'translate-y-0' : 'translate-y-full',
      )}
    >
      <Button
        size="m"
        aria-haspopup="dialog"
        className="min-w-0 flex-1"
        onClick={(e) => openOneClick({ product, packagingId: product.packagings[0]?.id ?? null, trigger: e.currentTarget })}
      >
        {t('requestPrice')}
      </Button>
      <a
        href={phone.href}
        aria-label={t('call', { phone: phone.display })}
        onClick={() => track('click_phone', { place: 'product_sticky' })}
        className="inline-grid size-12 shrink-0 place-items-center rounded-full bg-surface-strong text-accent transition-colors hover:text-accent-hover"
      >
        <Phone aria-hidden size={20} strokeWidth={1.5} />
      </a>
    </div>
  );
}
