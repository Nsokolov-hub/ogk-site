import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/cn';

const base = 'inline-flex h-9 items-center whitespace-nowrap rounded-pill bg-surface-strong px-4 text-small text-text md:text-body';

export function Chip({ label, href, className }: { label: string; href?: string; className?: string }) {
  if (href) {
    return (
      <Link href={href} className={cn(base, 'transition-colors hover:text-accent', className)}>
        {label}
      </Link>
    );
  }
  return <span className={cn(base, className)}>{label}</span>;
}
