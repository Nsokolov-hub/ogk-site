'use client';

import { useTranslations } from 'next-intl';
import type { Analogue } from '@/types/requests';
import { RadioGroup } from '@/components/ui/RadioGroup';

/** RFQ-12: только этот товар / готовы рассмотреть аналоги / подберите аналог */
export function AnalogueChoice({
  name,
  value,
  onChange,
  className,
}: {
  name: string;
  value: Analogue;
  onChange: (value: Analogue) => void;
  className?: string;
}) {
  const t = useTranslations('product');
  return (
    <RadioGroup<Analogue>
      legend={t('analogue')}
      name={name}
      value={value}
      onChange={onChange}
      className={className}
      options={[
        { value: 'none', label: t('analogueNone') },
        { value: 'allowed', label: t('analogueAllowed') },
        { value: 'requested', label: t('analogueRequested') },
      ]}
    />
  );
}
