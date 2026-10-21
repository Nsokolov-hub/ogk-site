import type { ComponentProps, ReactNode } from 'react';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';

export type ButtonVariant = 'menu' | 'primary' | 'secondary' | 'ghost';
export type ButtonSize = 's' | 'm' | 'l';

const base =
  'inline-flex shrink-0 select-none items-center justify-center gap-2.5 rounded-pill border text-center whitespace-nowrap ' +
  'transition-[background-color,color,border-color,transform,opacity] duration-300 active:scale-[0.97] ' +
  'disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-60';

/** Варианты из UI-кита: кнопка меню, главная CTA, дополнительная CTA, текстовая */
const variants: Record<ButtonVariant, string> = {
  menu: 'border-accent bg-transparent text-accent hover:bg-accent hover:text-text-on-accent',
  primary: 'border-accent bg-accent text-text-on-accent hover:border-accent-hover hover:bg-accent-hover',
  secondary: 'border-transparent bg-surface-strong text-accent hover:text-accent-hover',
  ghost: 'border-transparent bg-transparent px-0 text-text hover:text-accent',
};

const sizes: Record<ButtonSize, string> = {
  s: 'h-10 px-5 text-small font-medium sm:px-6 sm:text-body',
  m: 'h-12 px-[22px] text-body font-semibold sm:text-lg',
  l: 'h-14 w-full px-6 text-lg font-normal sm:text-2xl',
};

export function buttonClasses(variant: ButtonVariant = 'primary', size: ButtonSize = 'm', className?: string) {
  return cn(base, variants[variant], sizes[size], variant === 'ghost' && 'px-0 sm:px-0', className);
}

/** Внутренний маршрут сайта (с учётом локали) или обычная ссылка */
export function isRoute(href: string) {
  return href.startsWith('/') && !href.startsWith('//') && !href.startsWith('/files/') && !href.startsWith('/images/');
}

type Common = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Иконка справа от текста */
  icon?: ReactNode;
  /** Иконка слева от текста */
  iconStart?: ReactNode;
  className?: string;
  children: ReactNode;
};

type AsLink = Common & Omit<ComponentProps<'a'>, keyof Common | 'href'> & { href: string };
type AsButton = Common & Omit<ComponentProps<'button'>, keyof Common> & { href?: undefined };

export type ButtonProps = AsLink | AsButton;

export function Button(props: ButtonProps) {
  const { variant = 'primary', size = 'm', icon, iconStart, className, children, ...rest } = props;
  const cls = buttonClasses(variant, size, className);
  const content = (
    <>
      {iconStart}
      <span>{children}</span>
      {icon}
    </>
  );

  if (typeof rest.href === 'string') {
    const { href, ...anchor } = rest as Omit<AsLink, keyof Common>;
    if (isRoute(href)) {
      return (
        <Link href={href} className={cls} {...anchor}>
          {content}
        </Link>
      );
    }
    return (
      <a href={href} className={cls} {...anchor}>
        {content}
      </a>
    );
  }

  const { type = 'button', ...button } = rest as Omit<AsButton, keyof Common>;
  return (
    <button type={type} className={cls} {...button}>
      {content}
    </button>
  );
}
