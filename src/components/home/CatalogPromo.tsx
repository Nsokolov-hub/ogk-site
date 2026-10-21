import Image from 'next/image';
import { ArrowDownRight } from 'lucide-react';
import type { HomeContent } from '@/types/content';
import { Button } from '@/components/ui/Button';

/** Промо-блок из UI-кита «Нужен конкретный товар?»: флаконы выступают над плашкой */
export function CatalogPromo({ promo }: { promo: HomeContent['promo'] }) {
  return (
    <div className="relative isolate mt-16 grid items-end gap-6 md:mt-24 md:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] md:gap-10">
      <div aria-hidden className="absolute inset-x-0 bottom-0 top-[38%] -z-10 rounded-block bg-surface md:top-[30%]" />
      <div className="relative mx-auto w-full max-w-[640px] px-4 md:px-8">
        <Image
          src={promo.image.src}
          alt={promo.image.alt}
          width={promo.image.width}
          height={promo.image.height}
          sizes="(min-width: 768px) 50vw, 92vw"
          className="h-auto w-full"
        />
      </div>
      <div className="px-5 pb-8 md:px-0 md:pb-14 md:pr-10 lg:pb-20 lg:pr-16">
        <h3 className="text-h3 font-medium text-accent">{promo.title}</h3>
        <p className="mt-3 max-w-[460px] text-lead text-text">{promo.text}</p>
        <Button href={promo.cta.href} size="m" className="mt-6 md:mt-8" icon={<ArrowDownRight aria-hidden size={20} strokeWidth={2} />}>
          {promo.cta.label}
        </Button>
      </div>
    </div>
  );
}
