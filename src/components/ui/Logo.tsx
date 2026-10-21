import Image from 'next/image';
import { cn } from '@/lib/cn';

/** Основной логотип «ogk chem» — шапка и подвал */
export function Logo({ className, alt = 'ОГК-ХИМ' }: { className?: string; alt?: string }) {
  return (
    <Image
      src="/images/brand/logo.svg"
      alt={alt}
      width={132}
      height={56}
      unoptimized
      priority
      className={cn('h-10 w-auto', className)}
    />
  );
}
