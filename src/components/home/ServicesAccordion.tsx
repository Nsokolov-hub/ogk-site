'use client';

import { useState } from 'react';
import Image from 'next/image';
import { ChevronDown } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { ServiceItem } from '@/types/content';
import { Button } from '@/components/ui/Button';
import { Chip } from '@/components/ui/Chip';
import { cn } from '@/lib/cn';

/**
 * Аккордеон услуг как на лендинге: всегда открыт ровно один пункт.
 * Текст закрытых пунктов остаётся в HTML (для поисковиков), но недоступен для фокуса.
 */
export function ServicesAccordion({ items }: { items: ServiceItem[] }) {
  const t = useTranslations('home.services');
  const [open, setOpen] = useState(items[0]?.id);

  return (
    <ul className="flex flex-col gap-3 md:gap-4">
      {items.map((s) => {
        const isOpen = s.id === open;
        const btnId = `svc-btn-${s.id}`;
        const panelId = `svc-panel-${s.id}`;
        return (
          <li key={s.id} className={cn('overflow-hidden rounded-block transition-colors duration-300', isOpen ? 'bg-surface-strong' : 'bg-surface hover:bg-surface-strong')}>
            <h3>
              <button
                id={btnId}
                type="button"
                aria-expanded={isOpen}
                aria-controls={panelId}
                aria-disabled={isOpen || undefined}
                onClick={() => setOpen(s.id)}
                className={cn(
                  'flex w-full items-center justify-between gap-6 p-5 text-left text-h3 font-medium text-text transition-colors md:p-8',
                  !isOpen && 'hover:text-accent',
                )}
              >
                {s.title}
                <ChevronDown
                  aria-hidden
                  size={28}
                  strokeWidth={1.5}
                  className={cn('shrink-0 transition-transform duration-300', isOpen ? 'rotate-180 text-accent' : 'text-text-secondary')}
                />
              </button>
            </h3>
            <div
              id={panelId}
              role="region"
              aria-labelledby={btnId}
              inert={!isOpen}
              className={cn('grid transition-[grid-template-rows] duration-500 ease-out', isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]')}
            >
              {/* Свёрнутая панель невидима (после анимации) — её текст остаётся в HTML для поисковиков */}
              <div
                className={cn(
                  'min-h-0 overflow-hidden',
                  isOpen ? 'visible [transition:visibility_0s]' : 'invisible [transition:visibility_0s_linear_0.5s]',
                )}
              >
                <div className="grid gap-6 px-5 pb-6 md:px-8 md:pb-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:gap-10 xl:grid-cols-[minmax(0,1fr)_380px]">
                  <div className="min-w-0">
                    <p className="max-w-[880px] text-body text-text md:text-lg">{s.text}</p>
                    <p className="mt-6 text-small font-medium text-accent md:text-body">{s.captionLabel}</p>
                    <ul className="mt-3 flex flex-wrap gap-2">
                      {s.chips.map((c) => (
                        <li key={c.label}>
                          <Chip label={c.label} href={c.href} />
                        </li>
                      ))}
                    </ul>
                    <div className="mt-8 flex flex-wrap gap-3">
                      <Button href={s.href} size="m">
                        {t('more')}
                      </Button>
                      <Button href={`${s.href}#form`} variant="secondary" size="m">
                        {t('order')}
                      </Button>
                    </div>
                  </div>
                  <div aria-hidden className="relative h-56 md:h-72 lg:h-[380px]">
                    <Image
                      src={s.image.src}
                      alt=""
                      fill
                      sizes="(min-width: 1280px) 380px, (min-width: 1024px) 300px, 90vw"
                      className={cn(
                        'object-contain transition-[transform,opacity] duration-700 ease-out lg:object-cover lg:object-top',
                        isOpen ? 'translate-x-0 opacity-100' : 'translate-x-10 opacity-0',
                      )}
                    />
                  </div>
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
