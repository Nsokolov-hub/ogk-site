'use client';

import type { ComponentProps } from 'react';
import { useTranslations } from 'next-intl';
import { Checkbox } from '@/components/ui/Checkbox';

type Props = Omit<ComponentProps<typeof Checkbox>, 'label'> & {
  kind: 'personalData' | 'marketing';
  docs: { consent: string; privacy: string };
};

/** Согласия оформлены отдельно друг от друга (NFR-06, NFR-07). Тексты финально проверяет юрист. */
export function ConsentCheckbox({ kind, docs, ...rest }: Props) {
  const t = useTranslations('form');
  const label =
    kind === 'personalData'
      ? t.rich('consentPersonalData', {
          consent: (chunks) => (
            <a href={docs.consent} target="_blank" rel="noopener">
              {chunks}
            </a>
          ),
          privacy: (chunks) => (
            <a href={docs.privacy} target="_blank" rel="noopener">
              {chunks}
            </a>
          ),
        })
      : t('consentMarketing');

  return <Checkbox label={label} required {...rest} />;
}
