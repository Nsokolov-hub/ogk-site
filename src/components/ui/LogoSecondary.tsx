import Image from 'next/image';
import { cn } from '@/lib/cn';

/** Дополнительный логотип «ОГК ХИМ» в капсуле — декоративный элемент */
export function LogoSecondary({ className }: { className?: string }) {
  return (
    <Image
      src="/images/brand/logo-secondary.svg"
      alt=""
      width={92}
      height={24}
      unoptimized
      className={cn('h-6 w-auto', className)}
    />
  );
}
