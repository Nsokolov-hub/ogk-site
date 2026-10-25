"""Product documents of the search index and the index settings (TZ 6, «Настройка индекса»).

A document carries everything a product preview needs, so category pages and search results are served by the
engine alone. Catalog numbers, P/N and CAS are stored compacted in separate fields, searched first and without
typo tolerance (SRCH-02, SRCH-03).
"""

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import Brand, BrandAlias, Category, Packaging, Product, ProductCategory, Substance
from app.catalog.normalize import compact

# Facet keys of the storefront → document attributes.
FACET_FIELDS = {'brand': 'brand_slug', 'pack': 'packs', 'storage': 'storage', 'purpose': 'purpose', 'type': 'type',
                'phase': 'phase', 'length': 'length', 'diameter': 'diameter', 'particle': 'particle', 'ph': 'ph'}
ATTRIBUTE_FACETS = ('storage', 'purpose', 'type', 'phase', 'length', 'diameter', 'particle', 'ph')
NUMBER_FIELDS = ['numbers', 'cas_numbers']

INDEX_SETTINGS: dict[str, Any] = {
    'searchableAttributes': ['numbers', 'cas_numbers', 'name', 'name_ru', 'synonyms', 'substance_names', 'brand',
                             'brand_aliases'],
    'filterableAttributes': ['id', 'all', 'categories', 'category_top', 'brand_slug', 'availability', 'packs',
                             'formula_hill', 'substance_slug', 'numbers', 'cas_numbers', *ATTRIBUTE_FACETS],
    'sortableAttributes': ['name_sort', 'popularity', 'in_stock', 'completeness'],
    # SRCH-04: on equal relevance products in stock and with fuller cards go first.
    'rankingRules': ['words', 'typo', 'proximity', 'attribute', 'sort', 'exactness', 'in_stock:desc',
                     'completeness:desc', 'popularity:desc'],
    # SRCH-03: numbers and CAS are found exactly, never «corrected».
    'typoTolerance': {'disableOnAttributes': NUMBER_FIELDS, 'disableOnNumbers': True,
                      'minWordSizeForTypos': {'oneTypo': 5, 'twoTypos': 9}},
    # NFR-05: no deep pagination; totals come from the «all» facet.
    'pagination': {'maxTotalHits': 4800},
    'faceting': {'maxValuesPerFacet': 300, 'sortFacetValuesBy': {'*': 'count'}},
    'separatorTokens': [],
}


def index_settings(db: Session) -> dict[str, Any]:
    """Settings with RU ↔ EN synonyms from the substance directory (SRCH-05)."""
    synonyms: dict[str, set[str]] = defaultdict(set)
    for substance in db.scalars(select(Substance)):
        en = substance.name_en.casefold()
        for ru in {substance.name_ru.casefold(), *(s.casefold() for s in substance.synonyms if s)}:
            if ru and ru != en and ' ' not in ru and ' ' not in en:
                synonyms[ru].add(en)
                synonyms[en].add(ru)
    return {**INDEX_SETTINGS, 'synonyms': {word: sorted(values) for word, values in synonyms.items()}}


class Context:
    """Directories shared by all documents of a batch, loaded once."""

    def __init__(self, db: Session, hide_controlled: bool):
        self.hide_controlled = hide_controlled
        self.brands = {b.id: b for b in db.scalars(select(Brand))}
        self.aliases: dict[str, list[str]] = defaultdict(list)
        for alias in db.scalars(select(BrandAlias)):
            self.aliases[alias.brand_id].append(alias.name)
        self.categories = {c.id: c for c in db.scalars(select(Category))}
        self.substances: dict[str, Substance] = {}

    def ancestors(self, category: Category) -> list[str]:
        parts = category.path.split('/')
        return ['/'.join(parts[: i + 1]) for i in range(len(parts))]


def visible(product: Product, ctx: Context) -> bool:
    if product.status != 'published':
        return False
    return not (ctx.hide_controlled and product.controlled)


def build(db: Session, products: list[Product], ctx: Context) -> tuple[list[dict[str, Any]], list[str]]:
    """(documents to upsert, ids to delete)."""
    ids = [p.id for p in products]
    packs: dict[str, list[Packaging]] = defaultdict(list)
    for pack in db.scalars(select(Packaging).where(Packaging.product_id.in_(ids))
                           .order_by(Packaging.product_id, Packaging.position)):
        packs[pack.product_id].append(pack)
    links: dict[str, list[ProductCategory]] = defaultdict(list)
    for link in db.scalars(select(ProductCategory).where(ProductCategory.product_id.in_(ids))):
        links[link.product_id].append(link)
    missing = {p.substance_id for p in products if p.substance_id and p.substance_id not in ctx.substances}
    if missing:
        for substance in db.scalars(select(Substance).where(Substance.id.in_(missing))):
            ctx.substances[substance.id] = substance

    documents, deleted = [], []
    for product in products:
        if not visible(product, ctx):
            deleted.append(product.id)
            continue
        documents.append(document(product, ctx, packs[product.id], links[product.id]))
    return documents, deleted


def document(product: Product, ctx: Context, packs: list[Packaging], links: list[ProductCategory]) -> dict[str, Any]:
    brand = ctx.brands[product.brand_id]
    substance = ctx.substances.get(product.substance_id or '')
    primary = next((ctx.categories[link.category_id] for link in links if link.is_primary), None)
    paths: list[str] = []
    for link in links:
        for path in ctx.ancestors(ctx.categories[link.category_id]):
            if path not in paths:
                paths.append(path)
    custom = product.custom_packaging if product.custom_packaging is not None else brand.custom_packaging
    numbers = [compact(product.catalog_number)] + [compact(p.catalog_number) for p in packs if p.catalog_number]
    image = product.images[0] if product.images else None
    doc: dict[str, Any] = {
        'id': product.id,
        'all': 1,
        'slug': product.slug,
        'card_type': product.card_type,
        'name': product.name_en,
        'name_ru': product.name_ru,
        'name_sort': product.name_en.casefold()[:100],
        'synonyms': product.synonyms,
        'brand': brand.name,
        'brand_slug': brand.slug,
        'brand_logo': brand.logo,
        'brand_aliases': [a for a in ctx.aliases.get(brand.id, []) if a.casefold() != brand.name.casefold()],
        'catalog_number': product.catalog_number,
        'numbers': list(dict.fromkeys(n for n in numbers if n)),
        'cas': product.cas,
        'cas_numbers': [compact(c) for c in [product.cas, *product.alt_cas] if c],
        'substance_slug': substance.slug if substance else None,
        'substance_role': product.substance_role if substance else None,
        'substance_names': [substance.name_en, substance.name_ru, *substance.synonyms] if substance else [],
        'categories': paths,
        'category': primary.path if primary else None,
        'category_top': primary.path.split('/')[0] if primary else None,
        'availability': product.availability,
        'in_stock': 1 if product.availability == 'in_stock' else 0,
        'packs': [p.key for p in packs] + (['custom'] if custom else []),
        'packagings': [{'key': p.key, 'label_ru': p.label_ru, 'label_en': p.label_en,
                        'catalog_number': p.catalog_number} for p in packs],
        'custom_packaging': bool(custom),
        'formula_hill': product.formula_hill,
        'completeness': product.completeness,
        'popularity': product.popularity,
        'discontinued': product.discontinued,
        'image': image,
    }
    for key in ATTRIBUTE_FACETS:
        doc[key] = (product.attributes or {}).get(key) or []
    return doc
