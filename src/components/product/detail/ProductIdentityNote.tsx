import { Link } from '@/i18n/navigation';
import type { ProductIdentity } from '@/types/catalog';

/** Reviewed manufacturer/channel identity; stock, documents and delivery terms are separate. */
export function ProductIdentityNote({ identity, slug, locale }: {
  identity?: ProductIdentity;
  slug: string;
  locale: string;
}) {
  if (!identity) return null;
  const ru = locale === 'ru';
  const channel = identity.supplyChannel !== identity.manufacturer;
  return (
    <aside
      aria-label={ru ? 'Производитель и каталожные номера' : 'Manufacturer and catalog identifiers'}
      className="mt-6 max-w-[1100px] rounded-field bg-surface px-4 py-3 text-small text-text-secondary md:px-5"
    >
      <p>
        {ru ? 'Производитель' : 'Manufacturer'}: <strong className="font-medium text-text">{identity.manufacturer}</strong>
        {channel ? ` · ${ru ? 'Канал каталога' : 'Catalog channel'}: ${identity.supplyChannel}` : ''}
      </p>
      <p className="mt-1">
        {ru ? 'Номера одной позиции' : 'Identifiers of the same product'}: {identity.identifierAliases.join(' / ')}.
        {' '}
        <a href={identity.sourceUrl} target="_blank" rel="noreferrer" className="text-accent underline-offset-4 hover:underline">
          {ru ? 'Источник идентификации' : 'Catalog identity reference'}
        </a>
      </p>
      {identity.canonicalSlug !== slug ? (
        <p className="mt-1">
          <Link href={`/product/${identity.canonicalSlug}/`} className="text-accent underline-offset-4 hover:underline">
            {ru ? 'Основная карточка стандарта USP' : 'Main USP reference standard page'}
          </Link>
        </p>
      ) : null}
    </aside>
  );
}
