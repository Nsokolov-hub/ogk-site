'use client';

import type { ReactNode } from 'react';
import { CircleCheck, TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/cn';

/** Итог отправки формы; объявляется скринридером */
export function FormStatus({
  kind,
  title,
  children,
  className,
}: {
  kind: 'success' | 'error';
  title: string;
  children?: ReactNode;
  className?: string;
}) {
  const Icon = kind === 'success' ? CircleCheck : TriangleAlert;
  return (
    <div
      role={kind === 'error' ? 'alert' : 'status'}
      className={cn(
        'flex gap-3 rounded-field border p-4 md:p-5',
        kind === 'success' ? 'border-accent/40 bg-accent/10' : 'border-error/50 bg-error/10',
        className,
      )}
    >
      <Icon aria-hidden size={24} strokeWidth={1.5} className={kind === 'success' ? 'text-accent' : 'text-error'} />
      <div className="flex flex-col gap-1">
        <p className="text-body font-medium text-text">{title}</p>
        {children ? <div className="text-small text-text-secondary">{children}</div> : null}
      </div>
    </div>
  );
}
