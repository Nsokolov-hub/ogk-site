import type { ComponentProps } from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';
import { isRoute } from './Button';

type Direction = 'left' | 'right' | 'down' | 'down-right';

const rotation: Record<Direction, string> = {
  right: '',
  left: 'rotate-180',
  down: 'rotate-90',
  'down-right': 'rotate-45',
};

const cls =
  'inline-grid size-11 shrink-0 place-items-center rounded-full border border-text text-text transition-colors duration-300 ' +
  'hover:border-accent hover:text-accent disabled:pointer-events-none disabled:opacity-30';

type Common = { label: string; direction?: Direction; className?: string; iconClassName?: string };

/** Круглая кнопка-стрелка перехода / действия из UI-кита */
export function RoundArrowButton(
  props: Common & ({ href: string } | (Omit<ComponentProps<'button'>, 'children'> & { href?: undefined })),
) {
  const { label, direction = 'right', className, iconClassName, ...rest } = props;
  const icon = (
    <ArrowRight
      aria-hidden
      size={20}
      strokeWidth={1.5}
      className={cn('transition-transform duration-300', rotation[direction], iconClassName)}
    />
  );

  if (typeof rest.href === 'string') {
    const href = rest.href;
    return isRoute(href) ? (
      <Link href={href} aria-label={label} className={cn(cls, className)}>
        {icon}
      </Link>
    ) : (
      <a href={href} aria-label={label} className={cn(cls, className)}>
        {icon}
      </a>
    );
  }

  const { type = 'button', ...button } = rest as Omit<ComponentProps<'button'>, 'children'>;
  return (
    <button type={type} aria-label={label} className={cn(cls, className)} {...button}>
      {icon}
    </button>
  );
}
