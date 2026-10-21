import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

/** Заголовок секции: последние слова — акцентным цветом, под ним подзаголовок */
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
    <div className={cn('mb-6 flex flex-wrap items-end justify-between gap-x-8 gap-y-4 lg:mb-12', className)}>
      <div className="max-w-[900px]">
        <Tag id={id} className="text-h2 font-medium text-text">
          {title}
          {accent ? (
            <>
              {' '}
              <span className="text-accent">{accent}</span>
            </>
          ) : null}
        </Tag>
        {subtitle ? <p className="mt-3 text-body text-text-secondary lg:text-lg">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}
