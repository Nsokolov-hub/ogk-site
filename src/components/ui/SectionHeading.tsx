import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

/**
 * Заголовок секции. Акцентное слово — приём бренда из ТЗ 11.1 («акценты в заголовках»).
 * Подзаголовок — одна строка пояснения под заголовком, действие (если есть) — сразу под ним, слева:
 * так заголовок и ссылка читаются вместе, без пустой середины во всю ширину.
 */
export function SectionHeading({
  id,
  title,
  accent,
  subtitle,
  as: Tag = 'h2',
  action,
  className,
}: {
  id: string;
  title: string;
  accent?: string;
  subtitle?: string;
  as?: 'h1' | 'h2';
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('mb-8 max-w-[880px] lg:mb-12', className)}>
      <Tag id={id} className="text-h2 font-medium text-text">
        {title}
        {accent ? (
          <>
            {' '}
            <span className="text-accent">{accent}</span>
          </>
        ) : null}
      </Tag>
      {subtitle ? <p className="mt-3 text-lead text-text-secondary md:mt-4">{subtitle}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
