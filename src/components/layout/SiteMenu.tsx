'use client';

import { useState } from 'react';
import { ArrowRight, ChevronRight } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { SiteSettings } from '@/types/settings';
import type { MenuSection } from '@/lib/site-menu';
import { Link } from '@/i18n/navigation';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/cn';

/**
 * Меню по кнопке «Меню» (правки 02.11.2026): слева направления сайта, справа подразделы наведённого или
 * сфокусированного. Заливка — как у капсулы шапки.
 */
export function SiteMenu({
  id,
  menu,
  settings,
  onNavigate,
}: {
  id: string;
  menu: MenuSection[];
  settings: SiteSettings;
  onNavigate: () => void;
}) {
  const t = useTranslations('siteMenu');
  const [active, setActive] = useState(0);
  const current = menu[active];

  return (
    <div id={id} className="glass-overlay absolute inset-x-0 top-full mt-2 animate-fade-in rounded-block p-6 xl:p-8">
      <div className="grid grid-cols-[minmax(240px,320px)_1fr] gap-8">
        <ul aria-label={t('title')} className="flex flex-col gap-1">
          {menu.map((section, i) => (
            <li key={section.key}>
              <Link
                href={section.href}
                onMouseEnter={() => setActive(i)}
                onFocus={() => setActive(i)}
                onClick={onNavigate}
                aria-current={i === active ? 'true' : undefined}
                className={cn(
                  'flex items-center justify-between gap-3 rounded-sm px-4 py-3 text-h4 font-medium transition-colors',
                  i === active ? 'bg-surface-strong text-accent' : 'text-text hover:text-accent',
                )}
              >
                {section.label}
                <ChevronRight aria-hidden size={20} strokeWidth={1.5} className="shrink-0" />
              </Link>
            </li>
          ))}
        </ul>

        <div className="flex min-h-[280px] flex-col py-1">
          <p className="text-h4 font-medium text-text">{current.label}</p>
          {current.items.length ? (
            <ul className="mt-5 grid grid-cols-2 gap-x-6 gap-y-1 xl:grid-cols-3">
              {current.items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    className="block rounded-sm py-2 text-body text-text-secondary transition-colors hover:text-accent"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}

          {current.key === 'contacts' ? (
            <div className="mt-6 grid gap-x-10 gap-y-2 text-body text-text sm:grid-cols-2">
              <a href={settings.phone.href} onClick={() => track('click_phone', { place: 'menu' })} className="font-medium hover:text-accent">
                {settings.phone.display}
              </a>
              <a href={`mailto:${settings.emails.info}`} onClick={() => track('click_email', { place: 'menu' })} className="hover:text-accent">
                {settings.emails.info}
              </a>
              <p className="text-text-secondary">{settings.address.full}</p>
              <p className="text-text-secondary">{settings.hours}</p>
            </div>
          ) : null}

          {current.all ? (
            <Link
              href={current.all.href}
              onClick={onNavigate}
              className="mt-auto inline-flex w-fit items-center gap-2 pt-6 text-body font-medium text-accent transition-colors hover:text-accent-hover"
            >
              {current.all.label}
              <ArrowRight aria-hidden size={18} strokeWidth={1.5} />
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}
