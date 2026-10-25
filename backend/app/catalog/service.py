"""Writing the catalog: every change of a product recomputes its completeness and queues it for the index."""

from collections.abc import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.catalog import completeness
from app.catalog.models import (
    Brand,
    Category,
    Document,
    Packaging,
    Product,
    ProductCategory,
    SlugRedirect,
)
from app.catalog.normalize import product_slug
from app.catalog.settings import get_setting
from app.core.db import utcnow


def primary_category(db: Session, product_id: str) -> Category | None:
    return db.scalar(select(Category).join(ProductCategory, ProductCategory.category_id == Category.id)
                     .where(ProductCategory.product_id == product_id, ProductCategory.is_primary.is_(True)))


def effective_custom_packaging(product: Product, brand: Brand | None) -> bool:
    return product.custom_packaging if product.custom_packaging is not None else bool(brand and brand.custom_packaging)


def refresh_card(db: Session, product: Product, *, weights: dict[str, int] | None = None,
                 threshold: int | None = None, hide_controlled: bool | None = None) -> None:
    """Completeness, the indexing decision and the index queue of one product."""
    weights = weights or get_setting(db, 'completeness_weights')
    threshold = threshold if threshold is not None else get_setting(db, 'index_threshold')
    category = primary_category(db, product.id)
    brand = db.get(Brand, product.brand_id)
    packs = db.scalar(select(func.count()).select_from(Packaging).where(Packaging.product_id == product.id)) or 0
    docs = db.scalar(select(func.count()).select_from(Document).where(Document.product_id == product.id)) or 0
    card = completeness.facts(
        name=product.name_en, brand_id=product.brand_id, catalog_number=product.catalog_number,
        primary_category=category.path if category else None, packagings=packs,
        custom_packaging=effective_custom_packaging(product, brand), images=product.images, texts=product.texts,
        documents=docs, substance_id=product.substance_id, storage=product.storage)
    product.completeness = completeness.score(card, weights)
    product.indexable = completeness.indexable(status=product.status, completeness=product.completeness,
                                               threshold=threshold, override=product.index_override,
                                               controlled=bool(product.controlled),
                                               discontinued=product.discontinued)
    product.needs_index = True
    product.updated_at = utcnow()


def unique_product_slug(db: Session, brand_slug: str, catalog_number: str, name: str,
                        exclude_id: str | None = None) -> str:
    """URL-05 with a numeric suffix on collision."""
    base = product_slug(brand_slug, catalog_number, name) or product_slug(brand_slug, catalog_number, '')
    slug, n = base, 1
    while True:
        statement = select(Product.id).where(Product.slug == slug)
        if exclude_id:
            statement = statement.where(Product.id != exclude_id)
        if db.scalar(statement) is None:
            return slug
        n += 1
        slug = f'{base[:76]}-{n}'


def change_slug(db: Session, entity: str, target_id: str, old_slug: str, new_slug: str) -> None:
    """A published address is permanent: the old one answers 301 to the new one (URL-03)."""
    if old_slug == new_slug:
        return
    existing = db.scalar(select(SlugRedirect).where(SlugRedirect.entity == entity, SlugRedirect.old_slug == old_slug))
    if existing is None:
        db.add(SlugRedirect(entity=entity, old_slug=old_slug, target_id=target_id))
    # The new address may have been an old one of this page: it is current again.
    stale = db.scalar(select(SlugRedirect).where(SlugRedirect.entity == entity, SlugRedirect.old_slug == new_slug))
    if stale is not None:
        db.delete(stale)
    db.flush()


def set_primary_category(db: Session, product_id: str, category_id: str | None) -> None:
    rows = db.scalars(select(ProductCategory).where(ProductCategory.product_id == product_id)).all()
    for row in rows:
        row.is_primary = row.category_id == category_id
    if category_id and not any(row.category_id == category_id for row in rows):
        db.add(ProductCategory(product_id=product_id, category_id=category_id, is_primary=True))
    db.flush()


def queue_products(db: Session, *, brand_ids: Iterable[str] = (), substance_ids: Iterable[str] = (),
                   product_ids: Iterable[str] = ()) -> None:
    """Brand, substance or category data is copied into product documents: re-index the products."""
    for column, ids in ((Product.brand_id, list(brand_ids)), (Product.substance_id, list(substance_ids)),
                        (Product.id, list(product_ids))):
        if ids:
            db.execute(update(Product).where(column.in_(ids)).values(needs_index=True))


def queue_all(db: Session) -> int:
    """After a setting that changes every document (hiding controlled products, the threshold)."""
    result = db.execute(update(Product).values(needs_index=True))
    return int(getattr(result, 'rowcount', 0) or 0)
