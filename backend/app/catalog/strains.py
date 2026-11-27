"""Import reviewed manufacturer records with separate reference-culture and saleable catalogue identifiers."""

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.cas_pages import stand_in
from app.catalog.competitors import Brands
from app.catalog.indexnow import queue
from app.catalog.models import Brand, BrandAlias, Category, Packaging, Product
from app.catalog.normalize import brand_key, compact, slugify
from app.catalog.service import refresh_card, set_primary_category, unique_product_slug


class StrainRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    manufacturer: str = Field(min_length=1, max_length=200)
    article: str = Field(min_length=1, max_length=150)
    name: str = Field(min_length=1, max_length=500)
    strain_code: str = Field(pattern=r'^ATCC [A-Z0-9-]+$')
    line: str = Field(min_length=1, max_length=200)
    packaging_ru: str = Field(min_length=1, max_length=120)
    packaging_en: str = Field(min_length=1, max_length=120)
    pack_count: int = Field(gt=0, le=1000)
    source_url: str = Field(max_length=500)
    biosafety_level: int | None = None
    attenuated: bool = False


def import_reviewed(db: Session, raw: list[dict]) -> dict:
    records = [StrainRecord.model_validate(row) for row in raw]
    allowed = {'Microbiologics': 'www.microbiologics.com',
               'Thermo Fisher Scientific': 'www.thermofisher.com'}
    keys = set()
    for row in records:
        address = urlsplit(row.source_url)
        if address.scheme != 'https' or address.netloc != allowed.get(row.manufacturer):
            raise ValueError('Подтверждение должно ссылаться на официальный каталог производителя')
        key = (row.manufacturer, compact(row.article))
        if key in keys:
            raise ValueError(f'Повторный артикул {row.manufacturer} {row.article}')
        keys.add(key)
    category = db.scalar(select(Category).where(Category.path == 'biological-standards'))
    if category is None:
        raise ValueError('В каталоге отсутствует раздел микроорганизмов')
    directory = Brands(db)
    brands = {}
    for name in dict.fromkeys(row.manufacturer for row in records):
        identifier = directory.find(name)
        brand = db.get(Brand, identifier) if identifier else None
        if brand is None:
            brand = Brand(name=name, slug=slugify(name))
            db.add(brand)
            db.flush()
            db.add(BrandAlias(brand_id=brand.id, name=name, normalized=brand_key(name), source='import'))
        brands[name] = brand
    result: dict = {'created': 0, 'updated': 0, 'skipped': [], 'products': []}
    for row in records:
        brand = brands[row.manufacturer]
        product = db.scalar(select(Product).where(Product.brand_id == brand.id,
                                                  Product.catalog_number_norm == compact(row.article)))
        created = product is None
        if product and (product.manual_fields or product.status == 'archived'):
            result['skipped'].append({'article': row.article, 'reason': 'Карточка изменена вручную или архивирована'})
            continue
        if product is None:
            product = Product(brand_id=brand.id, catalog_number=row.article, catalog_number_norm=compact(row.article),
                              slug=unique_product_slug(db, brand.slug, row.article, row.name), name_en=row.name,
                              card_type='other', status='published', availability='on_order',
                              source='import:strains-2026-11-27', index_override=True)
            db.add(product)
            db.flush()
        elif stand_in(product.name_en, brand.name, product.catalog_number_norm):
            product.name_en = row.name
        attributes = {**(product.attributes or {}), 'strain_code': [row.strain_code],
                      'product_format': [row.line], 'manufacturer_source': [row.source_url]}
        if row.biosafety_level is not None:
            attributes['biosafety_level'] = [str(row.biosafety_level)]
        product.attributes = attributes
        if created:
            qualifier = ' Аттенуированный контрольный штамм.' if row.attenuated else ''
            product.texts = {'ru': {'description': [
                f'Контрольный микроорганизм {row.manufacturer}, {row.strain_code}. '
                f'Артикул производителя {row.article}, формат {row.line}.{qualifier}',
                f'Фасовка производителя — {row.packaging_ru}. Цену и срок поставки уточняем по запросу.'],
                'specs': [{'label': 'Код штамма', 'value': row.strain_code},
                          {'label': 'Формат', 'value': row.line},
                          {'label': 'Фасовка', 'value': row.packaging_ru}]}}
        set_primary_category(db, product.id, category.id)
        pack = db.scalar(select(Packaging).where(Packaging.product_id == product.id,
                                                 Packaging.key == 'manufacturer-pack'))
        if pack is None:
            pack = Packaging(product_id=product.id, key='manufacturer-pack')
            db.add(pack)
        pack.label_ru, pack.label_en = row.packaging_ru, row.packaging_en
        pack.catalog_number, pack.catalog_number_norm = row.article, compact(row.article)
        db.flush()
        refresh_card(db, product)
        result['created' if created else 'updated'] += 1
        result['products'].append({'id': product.id, 'slug': product.slug, 'article': product.catalog_number,
                                   'strain_code': row.strain_code})
    queue(db, [f'/product/{row["slug"]}/' for row in result['products']])
    return result
