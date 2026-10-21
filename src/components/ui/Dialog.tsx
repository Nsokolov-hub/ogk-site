'use client';

import type { ReactNode } from 'react';
import * as RD from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';

/**
 * Модальное окно на Radix: ловушка фокуса, Esc, возврат фокуса.
 * На телефоне — лист снизу на всю ширину, с 768 px — по центру.
 */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  closeLabel,
  children,
  onCloseAutoFocus,
  className,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  closeLabel: string;
  children: ReactNode;
  onCloseAutoFocus?: (e: Event) => void;
  className?: string;
}) {
  return (
    <RD.Root open={open} onOpenChange={onOpenChange}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-[200] bg-base-deep/70 backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <RD.Content
          // Без описания явно отключаем aria-describedby, с описанием Radix свяжет его сам
          {...(description ? {} : { 'aria-describedby': undefined })}
          onCloseAutoFocus={onCloseAutoFocus}
          className={cn(
            'fixed z-[201] flex flex-col overflow-hidden bg-surface-raised text-text shadow-[0_24px_80px_rgb(0_0_0/0.5)] outline-none',
            'inset-x-0 bottom-0 max-h-[92svh] rounded-t-block data-[state=open]:animate-sheet-up',
            'md:inset-auto md:left-1/2 md:top-1/2 md:max-h-[90svh] md:w-[min(680px,calc(100vw-48px))] md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-block md:data-[state=open]:animate-fade-in',
            className,
          )}
        >
          <div className="flex items-start justify-between gap-4 px-5 pb-2 pt-5 md:px-8 md:pt-7">
            <RD.Title className="text-h4 font-medium">{title}</RD.Title>
            <RD.Close
              aria-label={closeLabel}
              className="-mr-2 -mt-1 grid size-11 shrink-0 place-items-center rounded-full text-text-secondary transition-colors hover:text-text"
            >
              <X aria-hidden size={22} strokeWidth={1.5} />
            </RD.Close>
          </div>
          {description ? <RD.Description className="px-5 text-small text-text-secondary md:px-8">{description}</RD.Description> : null}
          <div className="overflow-y-auto overscroll-contain px-5 pb-6 pt-3 md:px-8 md:pb-8">{children}</div>
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}
