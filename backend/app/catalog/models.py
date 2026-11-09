"""Catalog of the site (TZ 5.1): brands, categories, substances, products, packagings, documents, relations.

PostgreSQL is the source of truth; the Meilisearch index is derived from it and can be rebuilt at any time
(TZ 12.3). A product that changes sets ``needs_index``; the worker pushes such products to the index.
Page texts of categories and brands live in ``content`` as ``{"ru": {...}, "en": {...}}`` in the shape the
storefront renders, until the admin panel edits them field by field.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Entity, utcnow

# JSONB in PostgreSQL (indexable, compact), plain JSON in SQLite tests.
Doc = JSON().with_variant(postgresql.JSONB(), 'postgresql')

CARD_TYPES = ('standard', 'equipment', 'other')
# draft → moderation → published → archived (TZ 5.6). Published products are on the site and in its search;
# whether search engines index them is decided by completeness (SEO-07).
PRODUCT_STATUSES = ('draft', 'moderation', 'published', 'archived')
AVAILABILITY = ('on_order', 'in_stock')
SUBSTANCE_ROLES = ('api', 'impurity', 'metabolite', 'labeled')
RELATION_KINDS = ('analogue', 'related', 'accessory')
CONTROLLED_LISTS = ('pp681', 'pp964')
# auto — matched the register on import or edit; review — a disputed match waiting for the chemist;
# confirmed / cleared — the chemist's decision, which imports never overwrite.
CONTROLLED_STATES = ('auto', 'review', 'confirmed', 'cleared')


class Brand(Entity):
    __tablename__ = 'brands'
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    logo: Mapped[str | None] = mapped_column(String(300))
    country: Mapped[str | None] = mapped_column(String(100))
    is_partner: Mapped[bool] = mapped_column(Boolean, default=False)
    # «Любая фасовка под запрос» for every product of the brand (TZ 5.2.2); a product may override it.
    custom_packaging: Mapped[bool] = mapped_column(Boolean, default=False)
    # The brand page /brands/{slug}/ exists only when it has content.
    page_published: Mapped[bool] = mapped_column(Boolean, default=False)
    wave: Mapped[int | None] = mapped_column(Integer)
    # Order of brand pages in lists (the order of the landing's logos, TZ 4.2).
    position: Mapped[int] = mapped_column(Integer, default=1000)
    crm_manufacturer_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    merged_into_id: Mapped[str | None] = mapped_column(ForeignKey('brands.id'))
    content: Mapped[dict[str, Any]] = mapped_column(Doc, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BrandAlias(Entity):
    """A known spelling of a brand; imports find the brand by the normalized spelling (IMP-03)."""

    __tablename__ = 'brand_aliases'
    brand_id: Mapped[str] = mapped_column(ForeignKey('brands.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(250))
    normalized: Mapped[str] = mapped_column(String(250), unique=True)
    # seed, import, crm (flow F5) or manual.
    source: Mapped[str] = mapped_column(String(20), default='manual')


class Category(Entity):
    __tablename__ = 'categories'
    parent_id: Mapped[str | None] = mapped_column(ForeignKey('categories.id'), index=True)
    slug: Mapped[str] = mapped_column(String(120))
    # Full path without /catalog/: reference-standards/edqm.
    path: Mapped[str] = mapped_column(String(400), unique=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    name_ru: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200))
    short_ru: Mapped[str | None] = mapped_column(String(100))
    short_en: Mapped[str | None] = mapped_column(String(100))
    card_type: Mapped[str] = mapped_column(String(20), default='standard')
    # Filters of the category page (TZ 5.5), in the storefront's facet keys.
    facets: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=True)
    content: Mapped[dict[str, Any]] = mapped_column(Doc, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CasPage(Base):
    """A substance by its CAS number (/cas/<cas>/): every offer of the catalog with that CAS on one page.

    Built from the products every night (app.catalog.cas_pages) for CAS numbers that several brands sell; the name
    is the one most brands use, the other names are its synonyms. Precursors and substances with their own page
    (Substance) get none."""

    __tablename__ = 'cas_pages'
    cas: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    formula: Mapped[str | None] = mapped_column(String(200))
    molecular_weight: Mapped[str | None] = mapped_column(String(40))
    offers: Mapped[int] = mapped_column(Integer)
    # Brand names and top-level category paths, most offers first.
    brands: Mapped[list[str]] = mapped_column(JSON, default=list)
    sections: Mapped[list[str]] = mapped_column(JSON, default=list)
    # The name as the index /cas/ sorts it: lower case, locants and stereo prefixes off («DL-Lactic acid» → «lactic
    # acid»); its first letter is the page's letter of the index (app.catalog.cas_pages.sort_key).
    sort_key: Mapped[str | None] = mapped_column(String(300), index=True)
    # Changes only when the page's content does: the Sitemap's lastmod.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IndexNowUrl(Base):
    """A page whose change search engines should learn about now (IndexNow, app.catalog.indexnow)."""

    __tablename__ = 'indexnow_queue'
    path: Mapped[str] = mapped_column(String(500), primary_key=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Substance(Entity):
    """An API (INN): the parent of standards, impurities, metabolites and labelled compounds."""

    __tablename__ = 'substances'
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name_ru: Mapped[str] = mapped_column(String(250))
    name_en: Mapped[str] = mapped_column(String(250))
    cas: Mapped[str | None] = mapped_column(String(20), index=True)
    formula: Mapped[str | None] = mapped_column(String(200))
    molecular_weight: Mapped[str | None] = mapped_column(String(40))
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    content: Mapped[dict[str, Any]] = mapped_column(Doc, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Product(Entity):
    __tablename__ = 'products'
    __table_args__ = (
        UniqueConstraint('brand_id', 'catalog_number_norm'),
        # The indexing queue: only rows waiting for the index are in this index.
        Index('ix_products_needs_index', 'needs_index', postgresql_where=text('needs_index'),
              sqlite_where=text('needs_index')),
        # Products seen in stock at a supplier: a few thousand of 1.5 million, so only they are in this index.
        Index('ix_products_supplier_stock', 'supplier_stock', postgresql_where=text('supplier_stock'),
              sqlite_where=text('supplier_stock')),
        # The queue of 2D structures to draw: only cards whose SMILES changed since the last drawing.
        Index('ix_products_structure_pending', 'id', postgresql_where=text('structure_smiles IS DISTINCT FROM smiles'),
              sqlite_where=text('structure_smiles IS NOT smiles')),
        # «Название содержит…» of the admin list (pg_trgm in schema public, migration 0004); a plain index in SQLite.
        Index('ix_products_name_en_trgm', 'name_en', postgresql_using='gin',
              postgresql_ops={'name_en': 'public.gin_trgm_ops'}),
    )
    card_type: Mapped[str] = mapped_column(String(20), default='standard')
    brand_id: Mapped[str] = mapped_column(ForeignKey('brands.id'), index=True)
    catalog_number: Mapped[str] = mapped_column(String(150))
    catalog_number_norm: Mapped[str] = mapped_column(String(150), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    name_en: Mapped[str] = mapped_column(String(500))
    name_ru: Mapped[str | None] = mapped_column(String(500))
    # The name the source gave in another language; internal, never shown or indexed (TZ 9.6, NFR-09).
    source_name: Mapped[str | None] = mapped_column(String(500))
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    cas: Mapped[str | None] = mapped_column(String(20), index=True)
    alt_cas: Mapped[list[str]] = mapped_column(JSON, default=list)
    substance_id: Mapped[str | None] = mapped_column(ForeignKey('substances.id'), index=True)
    substance_role: Mapped[str | None] = mapped_column(String(20))
    # Values for the category filters (TZ 5.5): facet key → values.
    attributes: Mapped[dict[str, list[str]]] = mapped_column(Doc, default=dict)
    formula: Mapped[str | None] = mapped_column(String(200))
    formula_hill: Mapped[str | None] = mapped_column(String(200), index=True)
    molecular_weight: Mapped[str | None] = mapped_column(String(40))
    smiles: Mapped[str | None] = mapped_column(Text)
    # The SMILES the 2D structure was last drawn from (or found unreadable); differs from smiles — draw again.
    structure_smiles: Mapped[str | None] = mapped_column(Text)
    iupac_name: Mapped[str | None] = mapped_column(Text)
    purity: Mapped[str | None] = mapped_column(String(200))
    storage: Mapped[str | None] = mapped_column(String(20))
    shipping: Mapped[str | None] = mapped_column(String(20))
    dangerous_goods: Mapped[bool | None] = mapped_column(Boolean)
    # Localized texts: {"ru": {"description": [...], "specs": [...], "faq": [...], "monograph": ...}, "en": {...}}.
    texts: Mapped[dict[str, Any]] = mapped_column(Doc, default=dict)
    # True when the description was written for this product (checked by the chemist), not a template.
    unique_description: Mapped[bool] = mapped_column(Boolean, default=False)
    images: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    availability: Mapped[str] = mapped_column(String(20), default='on_order')
    # Seen in stock at a supplier's warehouse in the last days (app.catalog.competitors): the storefront shows
    # «В наличии» as for our own stock. Kept apart from availability, which imports and managers set.
    supplier_stock: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # None — as the brand says (TZ 5.2.2).
    custom_packaging: Mapped[bool | None] = mapped_column(Boolean)
    discontinued: Mapped[bool] = mapped_column(Boolean, default=False)
    controlled: Mapped[str | None] = mapped_column(String(10))
    controlled_state: Mapped[str | None] = mapped_column(String(20))
    # seed, manual, crm or import:<source code>.
    source: Mapped[str] = mapped_column(String(60), default='manual')
    created_batch_id: Mapped[str | None] = mapped_column(ForeignKey('import_batches.id'), index=True)
    # The import run that last saw the product in its source: a full load marks the rest «Под заказ» (IMP-05).
    last_import_run: Mapped[str | None] = mapped_column(String(36))
    crm_product_id: Mapped[str | None] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(20), default='draft', index=True)
    completeness: Mapped[int] = mapped_column(Integer, default=0)
    # None — decided by completeness; True / False — set by hand in the admin panel (SEO-07).
    index_override: Mapped[bool | None] = mapped_column(Boolean)
    indexable: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    seo: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    # Fields edited by hand: imports do not overwrite them (IMP-05).
    manual_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    needs_index: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


def shown_availability(product: Product) -> str:
    """What the storefront says: our own stock, or a supplier's stock we buy from — both are «В наличии»."""
    return 'in_stock' if product.availability == 'in_stock' or product.supplier_stock else 'on_order'


class CompetitorOffer(Entity):
    """A position in stock on a supplier's site, as its last check saw it (app.catalog.competitors).

    Only what the site shows to everyone: brand, catalog number, packaging, quantity and price. ``product_id`` — our
    product with the same brand and catalog number; offers without one stay for the managers' statistics.
    """

    __tablename__ = 'competitor_offers'
    __table_args__ = (UniqueConstraint('source', 'external_id'),)
    source: Mapped[str] = mapped_column(String(20), index=True)
    external_id: Mapped[str] = mapped_column(String(100))
    brand_name: Mapped[str] = mapped_column(String(250))
    brand_id: Mapped[str | None] = mapped_column(ForeignKey('brands.id', ondelete='SET NULL'), index=True)
    catalog_number: Mapped[str] = mapped_column(String(150))
    catalog_number_norm: Mapped[str] = mapped_column(String(150), index=True)
    name: Mapped[str] = mapped_column(String(500))
    cas: Mapped[str | None] = mapped_column(String(40))
    pack: Mapped[str | None] = mapped_column(String(120))
    # None — the site says «in stock» without a number.
    quantity: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[str | None] = mapped_column(String(60))
    url: Mapped[str] = mapped_column(String(500))
    product_id: Mapped[str | None] = mapped_column(ForeignKey('products.id', ondelete='SET NULL'), index=True)
    packaging_id: Mapped[str | None] = mapped_column(String(36))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ProductCategory(Base):
    __tablename__ = 'product_categories'
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey('categories.id'), primary_key=True, index=True)
    # The primary category gives the breadcrumbs (TZ 5.1).
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class Packaging(Entity):
    """A fixed packaging of the manufacturer; «100 мг | 1 г» from a price list becomes two rows (TZ 5.1)."""

    __tablename__ = 'packagings'
    __table_args__ = (UniqueConstraint('product_id', 'key'),)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Facet key: 100-mg, 2-5-l, 1-pcs.
    key: Mapped[str] = mapped_column(String(80), index=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str | None] = mapped_column(String(10))
    label_ru: Mapped[str] = mapped_column(String(120))
    label_en: Mapped[str] = mapped_column(String(120))
    catalog_number: Mapped[str | None] = mapped_column(String(150))
    catalog_number_norm: Mapped[str | None] = mapped_column(String(150), index=True)
    availability: Mapped[str] = mapped_column(String(20), default='on_order')
    # Hidden estimate for managers; public prices are P2.
    price_estimate: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    crm_packing_id: Mapped[str | None] = mapped_column(String(36))
    # The import batch that added the packaging to an existing product: removed on its rollback (IMP-06).
    created_batch_id: Mapped[str | None] = mapped_column(String(36), index=True)


class Document(Entity):
    __tablename__ = 'documents'
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    # coa, sds, spec, datasheet, manual, certificate, strain-passport, leaflet.
    type: Mapped[str] = mapped_column(String(30))
    lang: Mapped[str] = mapped_column(String(2), default='en')
    title_ru: Mapped[str | None] = mapped_column(String(250))
    title_en: Mapped[str | None] = mapped_column(String(250))
    # No file — the storefront shows «Запросить» (a CoA of a batch is always on request).
    href: Mapped[str | None] = mapped_column(String(500))
    access: Mapped[str] = mapped_column(String(20), default='public')
    rights_basis: Mapped[str | None] = mapped_column(Text)


class ProductRelation(Base):
    __tablename__ = 'product_relations'
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
    related_id: Mapped[str] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default='manual')


class SlugRedirect(Entity):
    """An old address of a published page: the storefront answers 301 to the current one (URL-03)."""

    __tablename__ = 'slug_redirects'
    __table_args__ = (UniqueConstraint('entity', 'old_slug'),)
    entity: Mapped[str] = mapped_column(String(20))
    old_slug: Mapped[str] = mapped_column(String(400))
    target_id: Mapped[str] = mapped_column(String(36), index=True)


class ControlledEntry(Entity):
    """An entry of the lists of controlled substances (TZ 5.2.1): Government Decrees No. 681 and No. 964."""

    __tablename__ = 'controlled_register'
    list_name: Mapped[str] = mapped_column('list', String(10))
    name: Mapped[str] = mapped_column(String(500))
    cas: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Names and synonyms, lower case.
    names: Mapped[list[str]] = mapped_column(JSON, default=list)


class CatalogSetting(Base):
    __tablename__ = 'catalog_settings'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ImportSource(Entity):
    """A source of price lists with its saved column template (IMP-02)."""

    __tablename__ = 'import_sources'
    code: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ImportBatch(Entity):
    """One loaded file: what was created, updated, refused or conflicted (IMP-06)."""

    __tablename__ = 'import_batches'
    source_id: Mapped[str] = mapped_column(ForeignKey('import_sources.id'), index=True)
    file_name: Mapped[str] = mapped_column(String(300))
    file_sha256: Mapped[str] = mapped_column(String(64))
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    # running → done | failed; done → rolled_back.
    status: Mapped[str] = mapped_column(String(20), default='running', index=True)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_done: Mapped[int] = mapped_column(Integer, default=0)
    counters: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(100), default='cli')
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportChange(Base):
    """Values a batch replaced in an existing product, to put them back on rollback."""

    __tablename__ = 'import_changes'
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True,
                                    autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey('import_batches.id', ondelete='CASCADE'), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), index=True)
    before: Mapped[dict[str, Any]] = mapped_column(JSON)


class ImportIssue(Base):
    """A row a person has to look at: an error, a conflict, an unknown brand, a disputed controlled match."""

    __tablename__ = 'import_issues'
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True,
                                    autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey('import_batches.id', ondelete='CASCADE'), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    # error (row skipped), conflict (product kept as it was), warning (row loaded, value dropped), review.
    kind: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(String(500))
    values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    product_id: Mapped[str | None] = mapped_column(String(36))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class SearchMiss(Base):
    """Demand without a product (SRCH-06, SRCH-12): a normalized query that found nothing."""

    __tablename__ = 'search_misses'
    __table_args__ = (UniqueConstraint('query', 'lang'),)
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True,
                                    autoincrement=True)
    query: Mapped[str] = mapped_column(String(200))
    lang: Mapped[str] = mapped_column(String(2))
    count: Mapped[int] = mapped_column(Integer, default=1)
    first_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Cart(Base):
    """A guest's request cart by an anonymous cookie, 90 days (RFQ-01); localStorage keeps a copy."""

    __tablename__ = 'carts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
