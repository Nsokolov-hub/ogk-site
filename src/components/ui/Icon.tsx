import {
  CircleCheck,
  FileText,
  Globe,
  Loader,
  Mail,
  Map as MapIcon,
  Phone,
  ShieldCheck,
  User,
  Users,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/cn';

/** Имена иконок, которые можно указывать в контенте (админке) */
const icons: Record<string, LucideIcon> = {
  map: MapIcon,
  globe: Globe,
  file: FileText,
  users: Users,
  check: CircleCheck,
  zap: Zap,
  loader: Loader,
  phone: Phone,
  user: User,
  mail: Mail,
  shield: ShieldCheck,
};

export function Icon({ name, size = 24, className }: { name: string; size?: number; className?: string }) {
  const Component = icons[name] ?? CircleCheck;
  return <Component aria-hidden size={size} strokeWidth={1.5} className={cn('shrink-0 text-accent', className)} />;
}
