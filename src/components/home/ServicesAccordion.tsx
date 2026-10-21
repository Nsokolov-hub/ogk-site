'use client';

import { useState } from 'react';
import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
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
    <ul className="flex flex-col gap-3 md:gap-6 lg:gap-8">
      {items.map((s) => {
        const isOpen = s.id === open;
        const btnId = `svc-btn-${s.id}`;
        const panelId = `svc-panel-${s.id}`;
        return (
          <li key={s.id} data-active={isOpen} className="glow overflow-hidden rounded-block bg-surface">
            <h3>
              <button
                id={btnId}
                type="button"
                aria-expanded={isOpen}
                aria-controls={panelId}
                aria-disabled={isOpen || undefined}
                onClick={() => setOpen(s.id)}
                className={cn(
                  'flex w-full items-center gap-4 p-5 text-left text-h3 font-medium text-text transition-colors md:gap-6 md:p-8',
                  !isOpen && 'hover:text-accent',
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    'grid size-10 shrink-0 place-items-center rounded-full border transition-colors md:size-12',
                    isOpen ? 'border-accent text-accent' : 'border-text text-text',
                  )}
                >
                  <ArrowRight size={20} strokeWidth={1.5} className={cn('transition-transform duration-300', isOpen && 'rotate-90')} />
                </span>
                {s.title}
              </button>
            </h3>
            <div
              id={panelId}
              role="region"
              aria-labelledby={btnId}
              inert={!isOpen}
              className={cn('grid transition-[grid-template-rows] duration-500 ease-out', isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]')}
            >
              <div className="min-h-0 overflow-hidden">
                <div className="grid gap-6 px-5 pb-6 md:px-8 md:pb-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:gap-10 xl:grid-cols-[minmax(0,1fr)_380px]">
                  <div className="min-w-0 lg:pl-[72px]">
                    <p className="max-w-[880px] text-body text-text md:text-lg">{s.text}</p>
                    <p className="mt-6 text-small font-medium text-accent md:text-body">{s.captionLabel}</p>
                    <ul className="scroll-row -mx-5 mt-3 gap-2 px-5 md:-mx-8 md:px-8 lg:mx-0 lg:flex-wrap lg:overflow-visible lg:px-0">
                      {s.chips.map((c) => (
                        <li key={c.label}>
                          <Chip label={c.label} href={c.href} />
                        </li>
                      ))}
                    </ul>
                    <div className="mt-8 flex flex-wrap gap-3">
                      <Button href={s.href} size="m" icon={<ArrowRight aria-hidden size={20} strokeWidth={2} />}>
                        {t('more')}
                      </Button>
                      <Button href={`${s.href}#form`} variant="secondary" size="m" icon={<span aria-hidden className="size-1.5 rounded-full bg-current" />}>
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
