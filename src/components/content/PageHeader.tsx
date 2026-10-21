import type { ReactNode } from 'react';
import type { BreadcrumbItem } from '@/types/content';
import { Breadcrumbs } from '@/components/layout/Breadcrumbs';
import { cn } from '@/lib/cn';

/**
 * Начало внутренней страницы: хлебные крошки (ТЗ 11.4), один H1 и вводный абзац.
 * size="title" — рабочие страницы (товар, бренд), size="h1" — страницы-посадочные (услуги, о компании).
 */
export function PageHeader({
  breadcrumbs,
  title,
  lead,
  size = 'title',
  aside,
  children,
  className,
}: {
  breadcrumbs: BreadcrumbItem[];
  title: ReactNode;
  lead?: ReactNode;
  size?: 'title' | 'h1';
  aside?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn('pt-24 lg:pt-[150px]', className)}>
      <Breadcrumbs items={breadcrumbs} />
      <div className={cn('mt-6 grid gap-8', aside && 'lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end lg:gap-12')}>
        <div className="min-w-0">
          <h1 className={cn('max-w-[24ch] font-medium text-text', size === 'h1' ? 'text-h1' : 'text-title max-w-[32ch]')}>{title}</h1>
          {lead ? <p className="mt-4 max-w-[68ch] text-lead text-text md:mt-5">{lead}</p> : null}
          {children}
        </div>
        {aside}
      </div>
    </header>
  );
}
