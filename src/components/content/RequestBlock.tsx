import type { ReactNode } from 'react';
import type { SiteSettings } from '@/types/settings';
import { RequestForm } from '@/components/forms/RequestForm';
import { cn } from '@/lib/cn';

/** Блок заявки внизу страницы: заголовок и пояснение слева, форма справа */
export function RequestBlock({
  id = 'request',
  title,
  text,
  docs,
  defaultMessage,
  formType = 'request',
  aside,
  className,
}: {
  id?: string;
  title: string;
  text: string;
  docs: SiteSettings['docs'];
  /** Подставленный запрос: товар, услуга, текст из поиска */
  defaultMessage?: string;
  formType?: string;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className={cn('scroll-mt-28 rounded-block bg-surface p-6 md:p-10 lg:p-14', className)}>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <div>
          <h2 id={`${id}-title`} className="text-h3 font-medium text-text">
            {title}
          </h2>
          <p className="mt-4 text-body text-text-secondary md:text-lg">{text}</p>
          {aside}
        </div>
        <RequestForm docs={docs} defaultMessage={defaultMessage} formType={formType} />
      </div>
    </section>
  );
}
