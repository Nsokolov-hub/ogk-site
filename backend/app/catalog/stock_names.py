"""Recover imported placeholder names from exactly matched stock evidence and the CAS directory."""

import re

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.catalog.cas_pages import stand_in
from app.catalog.models import Brand, CasPage, CompetitorOffer, Packaging, Product, Substance
from app.catalog.normalize import clean_spaces, compact

CYRILLIC = re.compile('[а-яё]', re.I)


def restore_names(db: Session, product_ids: set[str] | None = None) -> list[str]:
    from app.catalog.competitors import fresh_offers

    offers = fresh_offers(db).join(Packaging, and_(
        Packaging.id == CompetitorOffer.packaging_id, Packaging.product_id == CompetitorOffer.product_id))

    if product_ids is not None:
        if not product_ids:
            return []
        offers = offers.where(CompetitorOffer.product_id.in_(product_ids))
    by_product: dict[str, list[CompetitorOffer]] = {}
    for offer in db.scalars(offers.order_by(CompetitorOffer.seen_at.desc(), CompetitorOffer.id)):
        if offer.product_id:
            by_product.setdefault(offer.product_id, []).append(offer)
    if not by_product:
        return []
    products = list(db.execute(select(Product, Brand).join(Brand).where(Product.id.in_(by_product))))
    numbers = {p.cas for p, _ in products if p.cas}
    cas_names = {row.cas: row for row in db.scalars(select(CasPage).where(CasPage.cas.in_(numbers)))}
    substances = {row.cas: row for row in db.scalars(select(Substance).where(Substance.cas.in_(numbers)))}
    changed = []
    for product, brand in products:
        def placeholder(name: str | None, brand_name: str = brand.name,
                        number_norm: str = product.catalog_number_norm) -> bool:
            return not name or stand_in(name, brand_name, number_norm)

        if not placeholder(product.name_ru or product.name_en):
            continue
        names: dict[str, str | None] = {'ru': None, 'en': None}
        for offer in by_product[product.id]:
            if product.cas and offer.cas and product.cas != offer.cas:
                continue
            name = clean_spaces(offer.name).strip('"; .')[:500]
            if not name or placeholder(name) or compact(name) == product.catalog_number_norm:
                continue
            language = 'ru' if CYRILLIC.search(name) else 'en'
            names[language] = names[language] or name
        cas = cas_names.get(product.cas or '')
        substance = substances.get(product.cas or '')
        names['en'] = names['en'] or (cas.name if cas else None) or (substance.name_en if substance else None)
        names['ru'] = names['ru'] or (substance.name_ru if substance else None)
        updated = False
        for language, candidate in names.items():
            field = f'name_{language}'
            if candidate and field not in (product.manual_fields or []) and placeholder(getattr(product, field)):
                setattr(product, field, candidate)
                updated = True
        if product.name_ru and placeholder(product.name_ru) and not placeholder(product.name_en) and \
                'name_ru' not in (product.manual_fields or []):
            product.name_ru = None
            updated = True
        if updated:
            product.needs_index = True
            changed.append(product.id)
    db.flush()
    return changed
