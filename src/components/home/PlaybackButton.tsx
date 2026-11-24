'use client';

import { Pause, Play } from 'lucide-react';
import { useTranslations } from 'next-intl';

export function PlaybackButton({ paused, toggle }: { paused: boolean; toggle: () => void }) {
  const t = useTranslations('home.hero');
  const Icon = paused ? Play : Pause;
  return (
    <button type="button" onClick={toggle} aria-label={t(paused ? 'play' : 'pause')}
      className="grid size-9 place-items-center rounded-full bg-black/40 text-text-secondary hover:text-accent motion-reduce:hidden">
      <Icon size={16} aria-hidden />
    </button>
  );
}
