"""A reviewed manufacturer/channel identity, without merging catalog IDs or historic request lines.

The two existing Enoxaparin records were identified by the business against the manufacturer's catalog.
No CAS, stock, document, delivery term or chemical characteristic is inferred from that identity.
"""

from copy import deepcopy
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.audit import record
from app.catalog import indexnow
from app.catalog.models import Brand, Packaging, Product
from app.catalog.normalize import compact, parse_pack
from app.catalog.service import refresh_card

SOURCE_URL = 'https://www.sigmaaldrich.com/BE/en/product/usp/1235831'
MASTER_SLUG = 'usp-1235831'
CHANNEL_SLUG = 'sigma-aldrich-1235831-1amp-enoxaparin-sodium-for-bioassays-united'
NAME = 'Enoxaparin Sodium for Bioassays, USP Reference Standard'
NAME_RU = 'Эноксапарин натрия для биоанализа, стандартный образец USP'
ALIASES = ['1235831', '1235831-1AMP']
REVIEW = 'usp-enoxaparin-2026-11-15'


def verified_identity(product: Product) -> dict[str, Any] | None:
    """Only our explicit reviewed identity can affect canonical URLs or exact identifier aliases."""
    value = (product.seo or {}).get('identity')
    if not isinstance(value, dict) or value.get('review') != REVIEW or value.get('sourceUrl') != SOURCE_URL:
        return None
    if value.get('manufacturer') != 'USP' or value.get('canonicalSlug') != MASTER_SLUG:
        return None
    if not value.get('canonicalProductId') or value.get('identifierAliases') != ALIASES:
        return None
    return value


def public_identity(product: Product) -> dict[str, Any] | None:
    identity = verified_identity(product)
    if not identity:
        return None
    return {key: identity[key] for key in ('manufacturer', 'supplyChannel', 'canonicalSlug',
                                         'identifierAliases', 'sourceUrl')}


def identifier_aliases(product: Product) -> list[str]:
    identity = verified_identity(product)
    if not identity or identity['canonicalProductId'] != product.id:
        return []
    aliases = identity['identifierAliases']
    return [*aliases, *(f'USP {alias}' for alias in aliases)]


def indexed_as_alias(db: Session, product: Product) -> bool:
    """The old channel page remains addressable; its verified master alone is listed in search."""
    identity = verified_identity(product)
    if not identity or identity['canonicalProductId'] == product.id:
        return False
    master = db.get(Product, identity['canonicalProductId'])
    master_identity = verified_identity(master) if master else None
    return bool(master and master.status == 'published' and not master.controlled and not master.discontinued
                and master_identity and master_identity['canonicalProductId'] == master.id)


def enrichment_plan(db: Session) -> dict[str, Any]:
    """Dry run only. Refuse a conflicting base SKU or ambiguous packaging rather than choosing a record."""
    rows = {p.slug: p for p in db.scalars(select(Product).where(Product.slug.in_([MASTER_SLUG, CHANNEL_SLUG])))}
    errors: list[str] = []
    for slug, brand_slug in ((MASTER_SLUG, 'usp'), (CHANNEL_SLUG, 'sigma-aldrich')):
        product = rows.get(slug)
        brand = db.get(Brand, product.brand_id) if product else None
        if not product:
            errors.append(f'Не найдена существующая карточка {slug}; новые товары не создаются')
        elif not brand or brand.slug != brand_slug or product.catalog_number_norm not in {compact(a) for a in ALIASES}:
            errors.append(f'Идентификатор или бренд {slug} отличается от проверенного каталога')
    if errors:
        return {'review': REVIEW, 'sourceUrl': SOURCE_URL, 'errors': errors, 'products': [], 'changed': 0}
    master = rows[MASTER_SLUG]
    result = []
    for slug, channel in ((MASTER_SLUG, 'USP'), (CHANNEL_SLUG, 'Sigma-Aldrich')):
        product = rows[slug]
        clash = db.scalar(select(Product.id).where(Product.brand_id == product.brand_id,
                                                   Product.catalog_number_norm == compact('1235831'),
                                                   Product.id != product.id))
        if clash:
            errors.append(f'У бренда карточки {slug} уже есть другой товар 1235831: {clash}; объединение запрещено')
            continue
        packs = list(db.scalars(select(Packaging).where(Packaging.product_id == product.id)
                                .order_by(Packaging.position, Packaging.id)))
        matches = [p for p in packs if p.catalog_number_norm == compact('1235831-1AMP') or
                   (p.unit == 'ampoule' and p.amount == 1)]
        pack = matches[0] if len(matches) == 1 else packs[0] if len(packs) == 1 else None
        if len(matches) > 1 or (packs and pack is None):
            errors.append(f'У {slug} несколько неоднозначных фасовок; требуется проверка, изменения не применены')
            continue
        if any(p.key == '1-ampoule' and p is not pack for p in packs):
            errors.append(f'У {slug} ключ 1-ampoule занят другой фасовкой; объединение запрещено')
            continue
        identity = {'review': REVIEW, 'manufacturer': 'USP', 'supplyChannel': channel,
                    'canonicalProductId': master.id, 'canonicalSlug': master.slug,
                    'identifierAliases': ALIASES, 'sourceUrl': SOURCE_URL}
        wanted = {'name_en': NAME, 'name_ru': NAME_RU, 'catalog_number': '1235831',
                  'catalog_number_norm': compact('1235831'),
                  'synonyms': list(dict.fromkeys([*(product.synonyms or []), 'Enoxaparin Sodium for Bioassays',
                                                 'USP 1235831', '1235831-1AMP'])),
                  'seo': {**deepcopy(product.seo or {}), 'identity': identity},
                  # Targeted, reviewed SKU only: the polymer standard needs no invented CAS to be searchable.
                  'index_override': product.id == master.id,
                  'manual_fields': sorted({*(product.manual_fields or []), 'name_en', 'name_ru', 'catalog_number',
                                           'catalog_number_norm', 'synonyms', 'seo'})}
        changes = {key: {'before': deepcopy(getattr(product, key)), 'after': value}
                   for key, value in wanted.items() if getattr(product, key) != value}
        desired_pack = {'key': '1-ampoule', 'amount': '1', 'unit': 'ampoule', 'label_ru': '1 амп.',
                        'label_en': '1 ampoule', 'catalog_number': '1235831-1AMP',
                        'catalog_number_norm': compact('1235831-1AMP')}
        pack_changes = {key: {'before': str(getattr(pack, key)) if key == 'amount' and pack and
                             getattr(pack, key) is not None else getattr(pack, key) if pack else None,
                             'after': value} for key, value in desired_pack.items()
                        if pack is None or (str(getattr(pack, key)) if key == 'amount' and
                                            getattr(pack, key) is not None else getattr(pack, key)) != value}
        # Database Numeric may read 1.000000: compare amounts numerically for an idempotent second run.
        if pack and pack.amount == Decimal('1'):
            pack_changes.pop('amount', None)
        result.append({'id': product.id, 'slug': slug, 'changes': changes,
                       'packagingId': pack.id if pack else None, 'packagingChanges': pack_changes})
    return {'review': REVIEW, 'sourceUrl': SOURCE_URL, 'errors': errors, 'products': result,
            'changed': sum(bool(p['changes'] or p['packagingChanges']) for p in result)}


def enrich_existing(db: Session, *, apply: bool = False) -> dict[str, Any]:
    """Apply the reviewed plan atomically when called in a transaction. Existing IDs and slugs are preserved."""
    if apply:
        # Serialize our two-row operation. It never locks or edits existing requests or CRM documents.
        list(db.scalars(select(Product).where(Product.slug.in_([MASTER_SLUG, CHANNEL_SLUG]))
                        .order_by(Product.id).with_for_update().execution_options(populate_existing=True)))
    plan = enrichment_plan(db)
    if not apply or plan['errors']:
        return {**plan, 'applied': False}
    paths = []
    for item in plan['products']:
        if not item['changes'] and not item['packagingChanges']:
            continue
        product = db.get(Product, item['id'])
        assert product is not None
        for key, change in item['changes'].items():
            setattr(product, key, change['after'])
        pack = db.get(Packaging, item['packagingId']) if item['packagingId'] else None
        if pack is None:
            parsed = parse_pack('1 ampoule')
            assert parsed is not None
            pack = Packaging(product_id=product.id, key=parsed.key, label_ru=parsed.label_ru,
                             label_en=parsed.label_en)
            db.add(pack)
        for key, change in item['packagingChanges'].items():
            setattr(pack, key, Decimal(change['after']) if key == 'amount' else change['after'])
        db.flush()
        refresh_card(db, product)
        product.version += 1
        record(db, None, 'product', product.id, 'enrich_identity',
               'Проверены название, производитель, канал и фасовка USP 1235831; история заявок сохранена',
               before={'changes': item['changes'], 'packagingChanges': item['packagingChanges']})
        paths.append(f'/product/{product.slug}/')
    indexnow.queue(db, paths)
    return {**plan, 'applied': True}
