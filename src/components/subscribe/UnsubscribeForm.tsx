'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { FormStatus } from '@/components/forms/FormStatus';
import { Button } from '@/components/ui/Button';
import { unsubscribe } from '@/lib/api';

export function UnsubscribeForm({ token }: { token: string }) {
  const t = useTranslations('unsubscribe');
  const [state, setState] = useState<'idle' | 'sending' | 'done' | 'error'>('idle');

  if (token.length < 16) return <FormStatus kind="error" title={t('missingTitle')}>{t('missingText')}</FormStatus>;
  if (state === 'done') return <FormStatus kind="success" title={t('doneTitle')}>{t('doneText')}</FormStatus>;

  const submit = async () => {
    setState('sending');
    try {
      await unsubscribe(token);
      setState('done');
    } catch {
      setState('error');
    }
  };

  return (
    <div className="flex max-w-xl flex-col gap-4">
      <Button type="button" size="m" onClick={submit} aria-disabled={state === 'sending' || undefined}>
        {state === 'sending' ? t('sending') : t('submit')}
      </Button>
      {state === 'error' ? <FormStatus kind="error" title={t('errorTitle')}>{t('errorText')}</FormStatus> : null}
    </div>
  );
}
