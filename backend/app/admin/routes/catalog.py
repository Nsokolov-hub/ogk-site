"""Categories, brands and substances (ADM-02, ADM-06): lists and creation; texts go through the editor.

Brands are kept in step with the CRM registry (flow F5); spellings added here help imports find the brand.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.admin.audit import record
from app.admin.models import Draft
from app.admin.routes.content import editor_view
from app.admin.security import StaffDep, requires
from app.catalog.models import Brand, BrandAlias, Category, Product, ProductCategory, Substance
from app.catalog.normalize import brand_key, cas_or_none, slugify
from app.core.db import DB
from app.core.errors import DomainError

router = APIRouter()


def drafted(db: DB, entity: str) -> set[str]:
    return set(db.scalars(select(Draft.entity_id).where(Draft.entity == entity)))


@router.get('/categories', dependencies=[requires('taxonomy.read')])
def categories(db: DB) -> dict[str, Any]:
    counts = dict(db.execute(select(ProductCategory.category_id, func.count())
                             .where(ProductCategory.is_primary.is_(True)).group_by(ProductCategory.category_id)).all())
    drafts = drafted(db, 'category')
    rows = db.scalars(select(Category).order_by(Category.path))
    return {'items': [{'id': c.id, 'path': c.path, 'parentId': c.parent_id, 'nameRu': c.name_ru, 'nameEn': c.name_en,
                       'position': c.position, 'facets': c.facets, 'cardType': c.card_type,
                       'isIndexed': c.is_indexed, 'hasEn': bool((c.content or {}).get('en')),
                       'hasDraft': c.id in drafts, 'count': counts.get(c.id, 0)} for c in rows]}


class NewCategoryIn(BaseModel):
    parentPath: str | None = None
    slug: str = Field(min_length=1, max_length=120)
    nameRu: str = Field(min_length=1, max_length=200)


@router.post('/categories', dependencies=[requires('taxonomy.write')])
def create_category(body: NewCategoryIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    parent = db.scalar(select(Category).where(Category.path == body.parentPath)) if body.parentPath else None
    if body.parentPath and parent is None:
        raise DomainError('CATEGORY_NOT_FOUND', 'Нет такого родительского раздела', 422, 'parentPath')
    slug = slugify(body.slug)
    path = f'{parent.path}/{slug}' if parent else slug
    if db.scalar(select(Category.id).where(Category.path == path)):
        raise DomainError('SLUG_TAKEN', 'Такой раздел уже есть', 409, 'slug')
    row = Category(parent_id=parent.id if parent else None, slug=slug, path=path, name_ru=body.nameRu.strip(),
                   card_type=parent.card_type if parent else 'standard', facets=list(parent.facets) if parent else
                   ['brand', 'pack', 'storage'], content={'ru': {'h1': body.nameRu, 'title': body.nameRu,
                                                                  'description': '', 'intro': ''}})
    db.add(row)
    db.flush()
    record(db, staff, 'category', row.id, 'create', path)
    return editor_view(db, 'category', row.id)


@router.get('/brands', dependencies=[requires('taxonomy.read')])
def brands(db: DB, q: str = '', published: bool | None = None, page: int = 1) -> dict[str, Any]:
    statement = select(Brand).where(Brand.merged_into_id.is_(None))
    if q.strip():
        like = f'%{q.strip()}%'
        statement = statement.where(or_(Brand.name.ilike(like), Brand.slug.ilike(like)))
    if published is not None:
        statement = statement.where(Brand.page_published.is_(published))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(db.scalars(statement.order_by(Brand.page_published.desc(), Brand.position, Brand.name)
                           .offset((max(page, 1) - 1) * 50).limit(50)))
    counts = dict(db.execute(select(Product.brand_id, func.count()).where(Product.brand_id.in_([b.id for b in rows]))
                             .group_by(Product.brand_id)).all()) if rows else {}
    drafts = drafted(db, 'brand')
    return {'total': total, 'page': page, 'items': [{
        'id': b.id, 'slug': b.slug, 'name': b.name, 'logo': b.logo, 'pagePublished': b.page_published,
        'customPackaging': b.custom_packaging, 'crmLinked': bool(b.crm_manufacturer_id), 'count': counts.get(b.id, 0),
        'hasDraft': b.id in drafts, 'hasEn': bool((b.content or {}).get('en'))} for b in rows]}


class NewBrandIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=120)


@router.post('/brands', dependencies=[requires('taxonomy.write')])
def create_brand(body: NewBrandIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    slug = slugify(body.slug or body.name)
    key = brand_key(body.name)
    if db.scalar(select(Brand.id).where(Brand.slug == slug)) or db.scalar(
            select(BrandAlias.id).where(BrandAlias.normalized == key)):
        raise DomainError('BRAND_EXISTS', 'Такой бренд или написание уже есть', 409, 'name')
    row = Brand(slug=slug, name=body.name.strip(), content={})
    db.add(row)
    db.flush()
    db.add(BrandAlias(brand_id=row.id, name=row.name, normalized=key, source='manual'))
    record(db, staff, 'brand', row.id, 'create', row.name)
    db.flush()
    return editor_view(db, 'brand', row.id)


@router.get('/brands/{brand_id}/aliases', dependencies=[requires('taxonomy.read')])
def aliases(brand_id: str, db: DB) -> list[dict[str, Any]]:
    return [{'id': a.id, 'name': a.name, 'source': a.source} for a in
            db.scalars(select(BrandAlias).where(BrandAlias.brand_id == brand_id).order_by(BrandAlias.name))]


class AliasIn(BaseModel):
    name: str = Field(min_length=1, max_length=250)


@router.post('/brands/{brand_id}/aliases', dependencies=[requires('taxonomy.write')])
def add_alias(brand_id: str, body: AliasIn, staff: StaffDep, db: DB) -> list[dict[str, Any]]:
    """Ещё одно написание бренда: импорт прайсов узнает его (IMP-03)."""
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise DomainError('NOT_FOUND', 'Бренд не найден', 404)
    key = brand_key(body.name)
    other = db.scalar(select(BrandAlias).where(BrandAlias.normalized == key))
    if other is not None and other.brand_id != brand_id:
        owner = db.get(Brand, other.brand_id)
        raise DomainError('ALIAS_TAKEN', f'Это написание уже у бренда «{owner.name if owner else "?"}»', 409, 'name')
    if other is None:
        db.add(BrandAlias(brand_id=brand_id, name=body.name.strip(), normalized=key, source='manual'))
        record(db, staff, 'brand', brand_id, 'alias_added', body.name.strip())
        db.flush()
    return aliases(brand_id, db)


@router.delete('/brands/{brand_id}/aliases/{alias_id}', dependencies=[requires('taxonomy.write')])
def remove_alias(brand_id: str, alias_id: str, staff: StaffDep, db: DB) -> list[dict[str, Any]]:
    alias = db.get(BrandAlias, alias_id)
    if alias is not None and alias.brand_id == brand_id:
        record(db, staff, 'brand', brand_id, 'alias_removed', alias.name)
        db.delete(alias)
        db.flush()
    return aliases(brand_id, db)


@router.get('/substances', dependencies=[requires('taxonomy.read')])
def substances(db: DB, q: str = '') -> dict[str, Any]:
    statement = select(Substance)
    if q.strip():
        like = f'%{q.strip()}%'
        statement = statement.where(or_(Substance.name_ru.ilike(like), Substance.name_en.ilike(like),
                                        Substance.cas == q.strip()))
    rows = list(db.scalars(statement.order_by(Substance.name_ru).limit(300)))
    counts = dict(db.execute(select(Product.substance_id, func.count())
                             .where(Product.substance_id.in_([s.id for s in rows])).group_by(Product.substance_id))
                  .all()) if rows else {}
    drafts = drafted(db, 'substance')
    return {'items': [{'id': s.id, 'slug': s.slug, 'nameRu': s.name_ru, 'nameEn': s.name_en, 'cas': s.cas,
                       'synonyms': s.synonyms, 'count': counts.get(s.id, 0), 'hasDraft': s.id in drafts}
                      for s in rows]}


class NewSubstanceIn(BaseModel):
    nameRu: str = Field(min_length=1, max_length=250)
    nameEn: str = Field(min_length=1, max_length=250)
    cas: str | None = None


@router.post('/substances', dependencies=[requires('taxonomy.write')])
def create_substance(body: NewSubstanceIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    slug = slugify(body.nameEn)
    if db.scalar(select(Substance.id).where(Substance.slug == slug)):
        raise DomainError('SLUG_TAKEN', 'Субстанция с таким названием уже есть', 409, 'nameEn')
    cas = cas_or_none(body.cas) if body.cas else None
    if body.cas and cas is None:
        raise DomainError('CAS_INVALID', 'CAS не прошёл проверку контрольной цифры', 422, 'cas')
    row = Substance(slug=slug, name_ru=body.nameRu.strip(), name_en=body.nameEn.strip(), cas=cas, synonyms=[],
                    content={})
    db.add(row)
    db.flush()
    record(db, staff, 'substance', row.id, 'create', row.name_ru)
    return editor_view(db, 'substance', row.id)
