"""Products of the catalog (ADM-03): the list with filters and mass actions, the editor by card type.

A field changed by hand joins ``manual_fields`` and imports no longer overwrite it (IMP-05). Every save goes to the
journal with the card before and after; any version can be put back.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.orm import Session

from app.admin.audit import changed_fields, history, record
from app.admin.models import AuditEntry, ProductDemand
from app.admin.security import StaffDep, requires
from app.catalog.models import (
    CARD_TYPES,
    PRODUCT_STATUSES,
    Brand,
    Category,
    Document,
    Packaging,
    Product,
    ProductCategory,
    ProductRelation,
    Substance,
)
from app.catalog.normalize import cas_or_none, compact, hill_key, looks_like_number, parse_pack, slugify
from app.catalog.service import change_slug, refresh_card, set_primary_category, unique_product_slug
from app.core.config import settings
from app.core.db import DB, utcnow
from app.core.errors import DomainError

router = APIRouter()
PAGE = 50
BULK_LIMIT = 2000
# Fields an import would otherwise rewrite: changed by hand, they are protected (IMP-05).
PROTECTED = {'nameEn': 'name_en', 'cas': 'cas', 'formula': 'formula', 'molecularWeight': 'molecular_weight',
             'availability': 'availability'}
SIMPLE = {'cardType': 'card_type', 'nameEn': 'name_en', 'nameRu': 'name_ru', 'synonyms': 'synonyms',
          'altCas': 'alt_cas', 'substanceRole': 'substance_role', 'attributes': 'attributes', 'formula': 'formula',
          'molecularWeight': 'molecular_weight', 'smiles': 'smiles', 'iupacName': 'iupac_name', 'purity': 'purity',
          'storage': 'storage', 'shipping': 'shipping', 'dangerousGoods': 'dangerous_goods', 'texts': 'texts',
          'uniqueDescription': 'unique_description', 'images': 'images', 'availability': 'availability',
          'customPackaging': 'custom_packaging', 'discontinued': 'discontinued', 'indexOverride': 'index_override',
          'seo': 'seo'}


def filtered(q: str = '', brand: str = '', category: str = '', status: str = '', source: str = '',
             indexable: bool | None = None, controlled: str = '', min_completeness: int | None = None,
             max_completeness: int | None = None, no_category: bool = False) -> Select[Any]:
    statement = select(Product)
    text = q.strip()
    if text:
        if looks_like_number(text):
            norm = compact(text)
            pack_owner = select(Packaging.product_id).where(Packaging.catalog_number_norm == norm)
            statement = statement.where(or_(Product.catalog_number_norm == norm, Product.cas == text,
                                            Product.id.in_(pack_owner)))
        else:
            statement = statement.where(or_(Product.name_en.ilike(f'%{text}%'), Product.name_ru.ilike(f'%{text}%')))
    if brand:
        statement = statement.where(Product.brand_id == select(Brand.id).where(Brand.slug == brand).scalar_subquery())
    if category:
        inside = select(ProductCategory.product_id).join(Category, Category.id == ProductCategory.category_id).where(
            or_(Category.path == category, Category.path.like(f'{category}/%')))
        statement = statement.where(Product.id.in_(inside))
    if no_category:
        statement = statement.where(~select(ProductCategory.product_id).where(
            ProductCategory.product_id == Product.id).exists())
    if status:
        statement = statement.where(Product.status == status)
    if source:
        statement = statement.where(Product.source.like(f'{source}%'))
    if indexable is not None:
        statement = statement.where(Product.indexable.is_(indexable))
    if controlled == 'yes':
        statement = statement.where(Product.controlled.is_not(None))
    elif controlled == 'review':
        statement = statement.where(Product.controlled_state == 'review')
    elif controlled == 'no':
        statement = statement.where(Product.controlled.is_(None))
    if min_completeness is not None:
        statement = statement.where(Product.completeness >= min_completeness)
    if max_completeness is not None:
        statement = statement.where(Product.completeness <= max_completeness)
    return statement


@router.get('/products', dependencies=[requires('products.read')])
def products(db: DB, q: str = '', brand: str = '', category: str = '', status: str = '', source: str = '',
             indexable: bool | None = None, controlled: str = '', min_completeness: int | None = None,
             max_completeness: int | None = None, no_category: bool = False, sort: str = 'updated',
             page: int = 1) -> dict[str, Any]:
    statement = filtered(q, brand, category, status, source, indexable, controlled, min_completeness,
                         max_completeness, no_category)
    orders: dict[str, Any] = {'updated': Product.updated_at.desc(), 'completeness': Product.completeness.desc(),
                              'popularity': Product.popularity.desc(), 'name': Product.name_en}
    order = orders.get(sort, orders['updated'])
    total = db.scalar(select(func.count()).select_from(statement.with_only_columns(Product.id).subquery())) or 0
    rows = list(db.scalars(statement.order_by(order, Product.id).offset((max(page, 1) - 1) * PAGE).limit(PAGE)))
    brands = {b.id: b for b in db.scalars(select(Brand).where(Brand.id.in_({p.brand_id for p in rows})))}
    primary = dict(db.execute(select(ProductCategory.product_id, Category.path)
                              .join(Category, Category.id == ProductCategory.category_id)
                              .where(ProductCategory.product_id.in_([p.id for p in rows]),
                                     ProductCategory.is_primary.is_(True))).all()) if rows else {}
    return {'total': total, 'page': page, 'pageSize': PAGE, 'items': [{
        'id': p.id, 'slug': p.slug, 'catalogNumber': p.catalog_number, 'name': p.name_en, 'cas': p.cas,
        'brand': brands[p.brand_id].name if p.brand_id in brands else '', 'category': primary.get(p.id),
        'status': p.status, 'completeness': p.completeness, 'indexable': p.indexable, 'source': p.source,
        'controlled': p.controlled, 'availability': p.availability, 'updatedAt': p.updated_at.isoformat()}
        for p in rows], 'statuses': list(PRODUCT_STATUSES)}


class BulkIn(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=BULK_LIMIT)
    action: str
    value: Any = None


@router.post('/products/bulk', dependencies=[requires('products.write')])
def bulk(body: BulkIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Массовые действия (ADM-03): статус, раздел, наличие, решение об индексации, переиндексация."""
    if not body.ids:
        raise DomainError('NOTHING_SELECTED', 'Выберите товары', 422, 'ids')
    rows = list(db.scalars(select(Product).where(Product.id.in_(body.ids))))
    category = None
    if body.action in ('primary_category', 'add_category', 'remove_category'):
        category = db.scalar(select(Category).where(Category.path == str(body.value or '')))
        if category is None:
            raise DomainError('CATEGORY_NOT_FOUND', 'Нет такого раздела', 422, 'value')
    for product in rows:
        if body.action == 'status':
            if body.value not in PRODUCT_STATUSES:
                raise DomainError('STATUS_INVALID', 'Нет такого статуса', 422, 'value')
            product.status = body.value
            if body.value == 'published' and product.published_at is None:
                product.published_at = utcnow()
        elif body.action == 'availability':
            if body.value not in ('on_order', 'in_stock'):
                raise DomainError('VALUE_INVALID', 'Наличие: on_order или in_stock', 422, 'value')
            product.availability = body.value
            product.manual_fields = sorted(set(product.manual_fields or []) | {'availability'})
        elif body.action == 'index_override':
            product.index_override = body.value if body.value in (True, False) else None
        elif body.action == 'primary_category' and category is not None:
            set_primary_category(db, product.id, category.id)
        elif body.action == 'add_category' and category is not None:
            if db.get(ProductCategory, (product.id, category.id)) is None:
                db.add(ProductCategory(product_id=product.id, category_id=category.id, is_primary=False))
        elif body.action == 'remove_category' and category is not None:
            db.execute(delete(ProductCategory).where(ProductCategory.product_id == product.id,
                                                     ProductCategory.category_id == category.id))
        elif body.action != 'reindex':
            raise DomainError('ACTION_INVALID', 'Нет такого действия', 422, 'action')
        db.flush()
        refresh_card(db, product)
    record(db, staff, 'product', 'bulk', 'bulk', f'{body.action}={body.value!s:.60} для {len(rows)} товаров',
           None, {'ids': [p.id for p in rows], 'action': body.action, 'value': body.value})
    return {'updated': len(rows)}


def snapshot(db: Session, product: Product) -> dict[str, Any]:
    """The editable state of a card: what the editor shows and the journal keeps."""
    data: dict[str, Any] = {key: getattr(product, column) for key, column in SIMPLE.items()}
    data.update({'slug': product.slug, 'catalogNumber': product.catalog_number, 'brandId': product.brand_id,
                 'cas': product.cas, 'substanceId': product.substance_id, 'status': product.status,
                 'controlledState': product.controlled_state})
    data['categories'] = [{'path': path, 'primary': primary} for path, primary in db.execute(
        select(Category.path, ProductCategory.is_primary).join(Category, Category.id == ProductCategory.category_id)
        .where(ProductCategory.product_id == product.id).order_by(ProductCategory.is_primary.desc(), Category.path))]
    data['packagings'] = [{'id': p.id, 'amount': str(p.amount) if p.amount is not None else None, 'unit': p.unit,
                           'labelRu': p.label_ru, 'labelEn': p.label_en, 'catalogNumber': p.catalog_number,
                           'availability': p.availability} for p in db.scalars(
        select(Packaging).where(Packaging.product_id == product.id).order_by(Packaging.position))]
    data['documents'] = [{'id': d.id, 'type': d.type, 'lang': d.lang, 'titleRu': d.title_ru, 'titleEn': d.title_en,
                          'href': d.href, 'access': d.access, 'rightsBasis': d.rights_basis} for d in db.scalars(
        select(Document).where(Document.product_id == product.id).order_by(Document.position))]
    data['relations'] = [{'relatedId': r.related_id, 'kind': r.kind} for r in db.scalars(
        select(ProductRelation).where(ProductRelation.product_id == product.id, ProductRelation.source == 'manual'))]
    return data


def editor(db: Session, product: Product) -> dict[str, Any]:
    brand = db.get(Brand, product.brand_id)
    substance = db.get(Substance, product.substance_id) if product.substance_id else None
    related_ids = [r['relatedId'] for r in snapshot(db, product)['relations']]
    related = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(related_ids)))} if related_ids else {}
    demand = db.execute(select(func.coalesce(func.sum(ProductDemand.views), 0),
                               func.coalesce(func.sum(ProductDemand.requests), 0))
                        .where(ProductDemand.product_id == product.id)).one()
    return {'id': product.id, 'data': snapshot(db, product),
            'brand': {'id': brand.id, 'name': brand.name, 'slug': brand.slug} if brand else None,
            'substance': {'id': substance.id, 'name': substance.name_ru} if substance else None,
            'related': {pid: f'{p.catalog_number} — {p.name_en}' for pid, p in related.items()},
            'completeness': product.completeness, 'indexable': product.indexable, 'source': product.source,
            'controlled': product.controlled, 'manualFields': product.manual_fields or [],
            'url': f'{settings.site_url.rstrip("/")}/product/{product.slug}/',
            'demand': {'views': int(demand[0]), 'requests': int(demand[1])},
            'history': history(db, 'product', product.id, limit=30)}


def get_product(db: Session, product_id: str, lock: bool = False) -> Product:
    statement = select(Product).where(Product.id == product_id)
    product = db.scalar(statement.with_for_update() if lock else statement)
    if product is None:
        raise DomainError('NOT_FOUND', 'Товар не найден', 404)
    return product


@router.get('/products/{product_id}', dependencies=[requires('products.read')])
def product_editor(product_id: str, db: DB) -> dict[str, Any]:
    return editor(db, get_product(db, product_id))


def decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value).replace(',', '.'))
    except InvalidOperation:
        raise DomainError('VALUE_INVALID', f'Не число: {value}', 422, 'packagings') from None


def apply(db: Session, product: Product, data: dict[str, Any]) -> None:
    """Write the editor's state; checks the rules of the card (TZ 5.2) and protects hand-made changes."""
    before = snapshot(db, product)
    if data.get('cardType', product.card_type) not in CARD_TYPES:
        raise DomainError('VALUE_INVALID', 'Тип карточки: standard, equipment или other', 422, 'cardType')
    if not str(data.get('nameEn') or '').strip():
        raise DomainError('VALUE_INVALID', 'Название EN обязательно (ТЗ 5.2)', 422, 'nameEn')
    cas = (data.get('cas') or '').strip() or None
    if cas and cas_or_none(cas) is None:
        raise DomainError('CAS_INVALID', 'CAS не прошёл проверку контрольной цифры', 422, 'cas')
    if data.get('status', product.status) not in PRODUCT_STATUSES:
        raise DomainError('STATUS_INVALID', 'Нет такого статуса', 422, 'status')
    for key, column in SIMPLE.items():
        if key in data:
            setattr(product, column, data[key])
    product.cas = cas_or_none(cas) if cas else None
    product.formula_hill = hill_key(product.formula) if product.formula else None
    product.status = data.get('status', product.status)
    if product.status == 'published' and product.published_at is None:
        product.published_at = utcnow()
    if data.get('controlledState') in ('confirmed', 'cleared') and product.controlled_state != data['controlledState']:
        product.controlled_state = data['controlledState']
        if data['controlledState'] == 'cleared':
            product.controlled = None
    substance_id = data.get('substanceId') or None
    if substance_id and db.get(Substance, substance_id) is None:
        raise DomainError('VALUE_INVALID', 'Нет такой субстанции', 422, 'substanceId')
    product.substance_id = substance_id
    slug = slugify(str(data.get('slug') or product.slug))
    if slug != product.slug:
        if db.scalar(select(Product.id).where(Product.slug == slug, Product.id != product.id)):
            raise DomainError('SLUG_TAKEN', 'Такой адрес уже у другого товара', 409, 'slug')
        change_slug(db, 'product', product.id, product.slug, slug)
        product.slug = slug
    manual = set(product.manual_fields or [])
    for key, column in PROTECTED.items():
        if before.get(key) != (product.cas if key == 'cas' else data.get(key, before.get(key))):
            manual.add(column)
    product.manual_fields = sorted(manual)
    write_categories(db, product, data.get('categories'))
    write_packagings(db, product, data.get('packagings'))
    write_documents(db, product, data.get('documents'))
    write_relations(db, product, data.get('relations'))
    product.version = (product.version or 0) + 1
    db.flush()
    refresh_card(db, product)


def write_categories(db: Session, product: Product, rows: list[dict[str, Any]] | None) -> None:
    if rows is None:
        return
    paths = {str(r.get('path')): bool(r.get('primary')) for r in rows if r.get('path')}
    found = {c.path: c for c in db.scalars(select(Category).where(Category.path.in_(paths)))}
    missing = sorted(set(paths) - set(found))
    if missing:
        raise DomainError('CATEGORY_NOT_FOUND', f'Нет раздела {missing[0]}', 422, 'categories')
    if paths and sum(paths.values()) != 1:
        raise DomainError('VALUE_INVALID', 'Отметьте один основной раздел (для хлебных крошек)', 422, 'categories')
    db.execute(delete(ProductCategory).where(ProductCategory.product_id == product.id))
    for path, primary in paths.items():
        db.add(ProductCategory(product_id=product.id, category_id=found[path].id, is_primary=primary))


def write_packagings(db: Session, product: Product, rows: list[dict[str, Any]] | None) -> None:
    if rows is None:
        return
    existing = {p.id: p for p in db.scalars(select(Packaging).where(Packaging.product_id == product.id))}
    keep: set[str] = set()
    keys: set[str] = set()
    for position, raw in enumerate(rows):
        label_ru, label_en = str(raw.get('labelRu') or '').strip(), str(raw.get('labelEn') or '').strip()
        amount, unit = decimal_or_none(raw.get('amount')), (raw.get('unit') or None)
        # The key of the «Фасовка» filter is the import's own (100-mg), so both meet in one facet value.
        parsed = parse_pack(f'{amount} {unit}') if amount is not None and unit else parse_pack(label_en or label_ru)
        if parsed is None:
            raise DomainError('VALUE_INVALID', 'Фасовка: количество и единица или подпись, например «100 мг»', 422,
                              f'packagings.{position}')
        amount, unit, key = parsed.amount, parsed.unit, parsed.key
        label_ru, label_en = label_ru or parsed.label_ru, label_en or parsed.label_en
        if key in keys:
            raise DomainError('VALUE_INVALID', f'Фасовка «{label_ru or label_en}» повторяется', 422, 'packagings')
        keys.add(key)
        row = existing.get(str(raw.get('id') or ''))
        if row is None:
            row = Packaging(product_id=product.id)
            db.add(row)
        number = (raw.get('catalogNumber') or '').strip() or None
        row.position, row.key, row.amount, row.unit = position, key, amount, unit
        row.label_ru, row.label_en = label_ru or label_en, label_en or label_ru
        row.catalog_number, row.catalog_number_norm = number, compact(number) if number else None
        row.availability = str(raw.get('availability')) if raw.get('availability') in ('on_order', 'in_stock') \
            else 'on_order'
        if row.id:
            keep.add(row.id)
    for row_id, row in existing.items():
        if row_id not in keep:
            db.delete(row)
    db.flush()


DOC_TYPES = ('coa', 'sds', 'spec', 'datasheet', 'manual', 'certificate', 'strain-passport', 'leaflet', 'spectrum')


def write_documents(db: Session, product: Product, rows: list[dict[str, Any]] | None) -> None:
    if rows is None:
        return
    existing = {d.id: d for d in db.scalars(select(Document).where(Document.product_id == product.id))}
    keep: set[str] = set()
    for position, raw in enumerate(rows):
        if raw.get('type') not in DOC_TYPES:
            raise DomainError('VALUE_INVALID', f'Тип документа: {", ".join(DOC_TYPES)}', 422, f'documents.{position}')
        if raw.get('href') and not str(raw.get('rightsBasis') or '').strip():
            # NFR-09: a manufacturer's file is published only with the right to publish it.
            raise DomainError('VALUE_INVALID', 'Укажите основание права на публикацию файла', 422,
                              f'documents.{position}.rightsBasis')
        row = existing.get(str(raw.get('id') or ''))
        if row is None:
            row = Document(product_id=product.id)
            db.add(row)
        row.position, row.type, row.lang = position, raw['type'], raw.get('lang') or 'en'
        row.title_ru, row.title_en = raw.get('titleRu') or None, raw.get('titleEn') or None
        row.href, row.rights_basis = raw.get('href') or None, raw.get('rightsBasis') or None
        row.access = str(raw.get('access')) if raw.get('access') in ('public', 'registered', 'request') else 'public'
        if row.id:
            keep.add(row.id)
    for row_id, row in existing.items():
        if row_id not in keep:
            db.delete(row)
    db.flush()


def write_relations(db: Session, product: Product, rows: list[dict[str, Any]] | None) -> None:
    if rows is None:
        return
    db.execute(delete(ProductRelation).where(ProductRelation.product_id == product.id,
                                             ProductRelation.source == 'manual'))
    seen: set[tuple[str, str]] = set()
    for raw in rows:
        related, kind = str(raw.get('relatedId') or ''), raw.get('kind')
        if kind not in ('analogue', 'related', 'accessory') or not related or related == product.id:
            continue
        if (related, kind) in seen or db.get(Product, related) is None:
            continue
        seen.add((related, kind))
        db.add(ProductRelation(product_id=product.id, related_id=related, kind=kind, source='manual'))
    db.flush()


class ProductIn(BaseModel):
    data: dict[str, Any]


@router.put('/products/{product_id}', dependencies=[requires('products.write')])
def save(product_id: str, body: ProductIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    product = get_product(db, product_id, lock=True)
    before = snapshot(db, product)
    apply(db, product, body.data)
    after = snapshot(db, product)
    record(db, staff, 'product', product.id, 'update',
           f'{product.catalog_number}: {", ".join(changed_fields(before, after)) or "без изменений"}', before, after)
    return editor(db, product)


@router.post('/products/{product_id}/restore/{entry_id}', dependencies=[requires('products.write')])
def restore(product_id: str, entry_id: int, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Вернуть карточку к версии из журнала (ADM-01)."""
    entry = db.get(AuditEntry, entry_id)
    if entry is None or entry.entity != 'product' or entry.entity_id != product_id or not entry.after:
        raise DomainError('NOT_FOUND', 'Версия не найдена', 404)
    product = get_product(db, product_id, lock=True)
    before = snapshot(db, product)
    apply(db, product, entry.after)
    record(db, staff, 'product', product.id, 'restore', f'{product.catalog_number}: версия от {entry.at:%d.%m.%Y %H:%M}',
           before, snapshot(db, product))
    return editor(db, product)


class NewProductIn(BaseModel):
    brandId: str
    catalogNumber: str = Field(min_length=1, max_length=150)
    nameEn: str = Field(min_length=1, max_length=500)
    cardType: str = 'standard'
    categoryPath: str | None = None


@router.post('/products', dependencies=[requires('products.write')])
def create(body: NewProductIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    brand = db.get(Brand, body.brandId)
    if brand is None:
        raise DomainError('NOT_FOUND', 'Бренд не найден', 422, 'brandId')
    norm = compact(body.catalogNumber)
    if db.scalar(select(Product.id).where(Product.brand_id == brand.id, Product.catalog_number_norm == norm)):
        raise DomainError('PRODUCT_EXISTS', 'У этого бренда уже есть товар с таким кат. №', 409, 'catalogNumber')
    product = Product(brand_id=brand.id, catalog_number=body.catalogNumber.strip(), catalog_number_norm=norm,
                      name_en=body.nameEn.strip(), card_type=body.cardType if body.cardType in CARD_TYPES
                      else 'standard', slug=unique_product_slug(db, brand.slug, body.catalogNumber, body.nameEn),
                      source='manual', status='draft', manual_fields=[])
    db.add(product)
    db.flush()
    if body.categoryPath:
        category = db.scalar(select(Category).where(Category.path == body.categoryPath))
        if category is not None:
            set_primary_category(db, product.id, category.id)
    refresh_card(db, product)
    record(db, staff, 'product', product.id, 'create', f'{brand.name} {product.catalog_number}', None,
           snapshot(db, product))
    return editor(db, product)
