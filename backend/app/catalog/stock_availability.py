"""Private, exact-pack stock evidence. Public forms supply identity, never supplier evidence."""

from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.catalog.identity import public_packagings, verified_identity
from app.catalog.models import Brand, BrandAlias, Category, CompetitorOffer, Packaging, Product, ProductCategory
from app.catalog.normalize import brand_key, cas_or_none, compact, parse_pack
from app.catalog.settings import get_setting
from app.core.db import as_utc, utcnow


def iso(value: datetime) -> str:
    return as_utc(value).isoformat()


def offer_view(db: Session, offer: CompetitorOffer) -> dict[str, Any]:
    from app.catalog.competitors import NAMES, offer_valid_until

    return {'source': offer.source, 'source_name': NAMES.get(offer.source, offer.source),
            'offer_id': offer.id, 'external_id': offer.external_id, 'catalog_number': offer.catalog_number,
            'pack': offer.pack, 'site_packaging_id': offer.packaging_id,
            'match': 'exact_pack' if offer.packaging_id else 'product_only',
            'seen_at': iso(offer.seen_at), 'valid_until': iso(offer_valid_until(db, offer)),
            'quantity': offer.quantity, 'url': offer.url}


def resolve_pack(packs: list[Packaging], item: dict[str, Any]) -> Packaging | None:
    identifier = item.get('site_packaging_id')
    label = str(item.get('packaging') or '').strip()
    candidates = [p for p in packs if p.id == identifier] if identifier else packs
    if identifier and not candidates and label:
        # Older search documents used a deterministic public ID rather than the packaging's database ID.
        # Accept it only for this product's exact key and a matching label; never strip or guess an ID suffix.
        candidates = [p for p in packs if identifier == f'{p.product_id}-{p.key}']
    if identifier and len(candidates) != 1:
        return None
    if label:
        parsed = parse_pack(label)
        candidates = [p for p in candidates if label.casefold() in
                      (p.label_ru.casefold(), p.label_en.casefold()) or parsed and parsed.key == p.key]
    # A missing label/ID is not an implicit choice from several packagings.
    return candidates[0] if len(candidates) == 1 else None


def own_stock(product: Product, pack: Packaging | None, packs: list[Packaging]) -> bool:
    if pack and pack.availability == 'in_stock':
        return True
    return product.availability == 'in_stock' and len(packs) <= 1


def public_products(db: Session):
    from app.catalog.pages import visible

    condition = visible(db)
    for path in get_setting(db, 'hidden_categories') or []:
        hidden = select(ProductCategory.product_id).join(Category).where(or_(
            Category.path == path, Category.path.startswith(path + '/', autoescape=True)))
        condition = and_(condition, Product.id.not_in(hidden))
    return condition


def capture_stock(db: Session, item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    from app.catalog.competitors import fresh_offers

    now = now or utcnow()
    snapshot: dict[str, Any] = {'version': 1, 'captured_at': iso(now), 'availability': 'unknown',
                              'origin': 'unknown', 'site_product_id': item.get('site_product_id'),
                              'site_packaging_id': item.get('site_packaging_id'),
                              'packaging_match': 'unmatched', 'offers': []}
    product = db.scalar(select(Product).where(Product.id == item.get('site_product_id'), public_products(db)))
    if product is None:
        return snapshot
    packs = public_packagings(product, list(db.scalars(select(Packaging).where(Packaging.product_id == product.id))))
    pack = resolve_pack(packs, item)
    brand = db.get(Brand, product.brand_id)
    aliases = {brand_key(brand.name), brand_key(brand.slug)} if brand else set()
    aliases.update(db.scalars(select(BrandAlias.normalized).where(BrandAlias.brand_id == product.brand_id)))
    identity = verified_identity(product)
    if identity:
        aliases.add(brand_key(identity['manufacturer']))
    if item.get('brand') and brand_key(str(item['brand'])) not in aliases:
        return snapshot
    numbers = {compact(product.catalog_number), compact(pack.catalog_number) if pack else ''}
    if item.get('catalog_number') and compact(str(item['catalog_number'])) not in numbers:
        return snapshot
    if item.get('cas') and product.cas and cas_or_none(str(item['cas'])) != product.cas:
        return snapshot
    if item.get('custom_packaging') or pack is None:
        hints = list(db.scalars(fresh_offers(db, now).where(CompetitorOffer.product_id == product.id)
                               .order_by(CompetitorOffer.source, CompetitorOffer.id).limit(30)))
        snapshot.update(packaging_match='custom' if item.get('custom_packaging') else 'product_only',
                        offers=[{**offer_view(db, offer), 'match': 'product_only'} for offer in hints])
        return snapshot
    snapshot.update(site_packaging_id=pack.id if pack else None,
                    packaging_match='exact' if pack else 'product_only')
    rows = list(db.scalars(fresh_offers(db, now).where(CompetitorOffer.product_id == product.id,
                       CompetitorOffer.packaging_id == pack.id if pack else CompetitorOffer.packaging_id.is_(None))
                          .order_by(CompetitorOffer.source, CompetitorOffer.id).limit(200))) if pack else []
    snapshot['offers'] = [offer_view(db, offer) for offer in rows]
    own = own_stock(product, pack, packs)
    snapshot['availability'] = 'in_stock' if own or rows else 'on_order'
    snapshot['origin'] = 'own' if own else 'supplier' if rows else 'none'
    return snapshot
