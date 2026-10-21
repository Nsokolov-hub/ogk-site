import type { ElementType, ReactNode } from 'react';
import { cn } from '@/lib/cn';

/** Контейнер: до 1640 px вместе с полями; поля 16 / 24 / 40 / 80 px */
export function Container({
  as: Tag = 'div',
  className,
  children,
}: {
  as?: ElementType;
  className?: string;
  children: ReactNode;
}) {
  return <Tag className={cn('mx-auto w-full max-w-[1640px] px-4 md:px-6 lg:px-10 2xl:px-20', className)}>{children}</Tag>;
}
