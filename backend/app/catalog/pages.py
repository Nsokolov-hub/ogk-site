"""Page data read from PostgreSQL: product, substance, brand, category tree, Sitemap and the feed.

Lists of products here are short (a card's neighbours, a brand's top eight); long lists and counts come from
the search engine (app.catalog.search.query).
"""

from collections import defaultdict
from typing import Any

from sqlalchemy import Select, and_, func, literal, or_, select, tuple_
from sqlalchemy.orm import Session

from app.catalog import cas_pages as cas_build
from app.catalog.models import (
    Brand,
    CasPage,
    Category,
    Document,
    Product,
    ProductCategory,
    ProductRelation,
    SlugRedirect,
    Substance,
)
from app.catalog.search import documents
from app.catalog.search.query import brand_pages, preview
from app.catalog.settings import get_setting

ROLE_ORDER = ['api', 'impurity', 'metabolite', 'labeled']
HPLC = 'chromatography/hplc-columns'


def visible(db: Session) -> Any:
    """Published, and not a controlled product while they are hidden (TZ 5.2.1)."""
    condition = Product.status == 'published'
    if get_setting(db, 'hide_controlled'):
        condition = and_(condition, Product.controlled.is_(None))
    return condition


def previews(db: Session, products: list[Product], lang: str) -> list[dict[str, Any]]:
    if not products:
        return []
    ctx = documents.Context(db, get_setting(db, 'hide_controlled'))
    docs, _ = documents.build(db, products, ctx)
    by_id = {doc['id']: doc for doc in docs}
    linked = brand_pages(db)
    return [preview(by_id[p.id], lang, linked) for p in products if p.id in by_id]


def iso(value: Any) -> str:
    return value.date().isoformat() if value else ''


def moved(db: Session, entity: str, slug: str, model: Any) -> str | None:
    redirect = db.scalar(select(SlugRedirect).where(SlugRedirect.entity == entity, SlugRedirect.old_slug == slug))
    if redirect is None:
        return None
    target = db.get(model, redirect.target_id)
    return getattr(target, 'slug', None) or getattr(target, 'path', None)


# ── categories ──

def hidden_category(path: str, hidden: list[str]) -> bool:
    """The category or one of its parents is kept off the storefront (setting hidden_categories)."""
    return any(path == h or path.startswith(f'{h}/') for h in hidden)


def tree(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(select(Category).order_by(Category.position, Category.name_ru)).all()
    hidden = get_setting(db, 'hidden_categories')
    children: dict[str | None, list[Category]] = defaultdict(list)
    for row in rows:
        if not hidden_category(row.path, hidden):
            children[row.parent_id].append(row)

    def node(row: Category) -> dict[str, Any]:
        return {'slug': row.slug, 'path': row.path, 'nameRu': row.name_ru, 'nameEn': row.name_en,
                'shortRu': row.short_ru, 'shortEn': row.short_en, 'hasEn': bool((row.content or {}).get('en')),
                'updatedAt': iso(row.updated_at), 'children': [node(c) for c in children[row.id]]}

    return [node(row) for row in children[None]]


def category(db: Session, path: str) -> dict[str, Any] | None:
    if not path:
        root = get_setting(db, 'catalog_root') or {}
        facets = (root.get('ru') or {}).get('facets') or ['brand', 'pack', 'storage']
        return {'path': '', 'nameRu': 'Каталог', 'nameEn': 'Catalog', 'cardType': 'standard', 'facets': facets,
                'isIndexed': True, 'content': root, 'updatedAt': '', 'casPages': popular_cas(db)}
    row = db.scalar(select(Category).where(Category.path == path))
    if row is None or hidden_category(row.path, get_setting(db, 'hidden_categories')):
        return None
    linked = ((get_setting(db, 'cas_links') or {}).get('categories') or {}).get(row.path) or []
    return {'path': row.path, 'nameRu': row.name_ru, 'nameEn': row.name_en, 'cardType': row.card_type,
            'facets': row.facets, 'isIndexed': row.is_indexed, 'content': row.content, 'updatedAt': iso(row.updated_at),
            'casPages': cas_refs(db, linked)}


def breadcrumb(db: Session, path: str | None, lang: str) -> list[dict[str, Any]]:
    if not path:
        return []
    parts = path.split('/')
    paths = ['/'.join(parts[: i + 1]) for i in range(len(parts))]
    rows = {c.path: c for c in db.scalars(select(Category).where(Category.path.in_(paths)))}
    return [{'slug': rows[p].slug, 'name': (rows[p].name_en or rows[p].name_ru) if lang == 'en' else rows[p].name_ru,
             'href': f'/catalog/{p}/'} for p in paths if p in rows]


# ── substances ──

def substance_out(row: Substance) -> dict[str, Any]:
    return {'slug': row.slug, 'nameRu': row.name_ru, 'nameEn': row.name_en, 'cas': row.cas, 'formula': row.formula,
            'molecularWeight': row.molecular_weight, 'synonyms': row.synonyms, 'content': row.content}


def _role_order() -> Any:
    from sqlalchemy import case

    return case({role: i for i, role in enumerate(ROLE_ORDER)}, value=Product.substance_role, else_=len(ROLE_ORDER))


def substance_page(db: Session, slug: str, lang: str) -> dict[str, Any]:
    row = db.scalar(select(Substance).where(Substance.slug == slug))
    if row is None:
        return {'moved': moved(db, 'substance', slug, Substance)}
    items = db.scalars(select(Product).where(Product.substance_id == row.id, visible(db))
                       .order_by(_role_order(), Product.popularity.desc(), Product.name_en).limit(500)).all()
    return {'substance': substance_out(row), 'items': previews(db, list(items), lang)}


def substances(db: Session) -> list[dict[str, Any]]:
    counts = dict(db.execute(select(Product.substance_id, func.count()).where(visible(db), Product.substance_id
                                                                              .is_not(None))
                             .group_by(Product.substance_id)).all())
    rows = db.scalars(select(Substance).order_by(Substance.name_ru)).all()
    return [{**substance_out(row), 'count': counts.get(row.id, 0)} for row in rows if counts.get(row.id)]


# ── substances by CAS number (app.catalog.cas_pages) ──

CAS_ITEMS = 300


INDEX_PAGE = 500
NEIGHBOURS = 6
POPULAR = 60


def cas_ref(row: CasPage, names_ru: dict[str, str] | None = None) -> dict[str, Any]:
    return {'cas': row.cas, 'name': row.name, 'offers': row.offers, 'nameRu': (names_ru or {}).get(row.cas) or None}


def cas_refs(db: Session, numbers: list[str]) -> list[dict[str, Any]]:
    """The CAS pages of these numbers that exist now, in the given order."""
    if not numbers:
        return []
    rows = {row.cas: row for row in db.scalars(select(CasPage).where(CasPage.cas.in_(numbers)))}
    names = get_setting(db, 'cas_names_ru') or {}
    return [cas_ref(rows[cas], names) for cas in numbers if cas in rows]


def popular_cas(db: Session, limit: int = cas_build.LINKS) -> list[dict[str, Any]]:
    names = get_setting(db, 'cas_names_ru') or {}
    return [cas_ref(row, names) for row in db.scalars(select(CasPage).order_by(CasPage.offers.desc(), CasPage.cas)
                                                     .limit(limit))]


def _letter_condition(letter: str) -> Any:
    first = func.substr(CasPage.sort_key, 1, 1)
    if letter == '0':
        return or_(CasPage.sort_key.is_(None), first < 'a', first > 'z')
    return first == letter


def cas_index(db: Session) -> dict[str, Any]:
    """The index /cas/: how many pages each letter has, and the pages with the most offers."""
    counts: dict[str, int] = defaultdict(int)
    for key, n in db.execute(select(func.substr(CasPage.sort_key, 1, 1), func.count())
                             .group_by(func.substr(CasPage.sort_key, 1, 1))):
        counts[cas_build.letter(key)] += n
    letters = [{'letter': letter, 'count': counts[letter],
                'pageCount': max(1, -(-counts[letter] // INDEX_PAGE))} for letter in sorted(counts)]
    return {'letters': letters, 'total': sum(counts.values()), 'popular': popular_cas(db, POPULAR)}


def cas_letter(db: Session, letter: str, page: int) -> dict[str, Any] | None:
    """One letter of the index, INDEX_PAGE names per page in the index's order; None — no such letter."""
    if letter != '0' and not ('a' <= letter <= 'z' and len(letter) == 1):
        return None
    condition = _letter_condition(letter)
    total = db.scalar(select(func.count()).select_from(CasPage).where(condition)) or 0
    if not total:
        return None
    page_count = max(1, -(-total // INDEX_PAGE))
    if page > page_count:
        return None
    names = get_setting(db, 'cas_names_ru') or {}
    rows = db.scalars(select(CasPage).where(condition).order_by(CasPage.sort_key, CasPage.cas)
                      .offset((page - 1) * INDEX_PAGE).limit(INDEX_PAGE))
    return {'letter': letter, 'page': page, 'pageCount': page_count, 'total': total,
            'items': [cas_ref(row, names) for row in rows]}


def cas_neighbours(db: Session, row: CasPage) -> list[dict[str, Any]]:
    """The names next to this one in the index: NEIGHBOURS before and after (every page is linked from others)."""
    if row.sort_key is None:
        return []
    key = tuple_(CasPage.sort_key, CasPage.cas)
    here = tuple_(literal(row.sort_key), literal(row.cas))
    before = list(db.scalars(select(CasPage).where(CasPage.sort_key.is_not(None), key < here)
                             .order_by(CasPage.sort_key.desc(), CasPage.cas.desc()).limit(NEIGHBOURS)))
    after = list(db.scalars(select(CasPage).where(CasPage.sort_key.is_not(None), key > here)
                            .order_by(CasPage.sort_key, CasPage.cas).limit(NEIGHBOURS)))
    names = get_setting(db, 'cas_names_ru') or {}
    return [cas_ref(r, names) for r in [*reversed(before), *after]]


def cas_page(db: Session, cas: str, lang: str) -> dict[str, Any] | None:
    """The page of a CAS number with its offers; a substance with its own page is sent there."""
    row = db.get(CasPage, cas)
    if row is None:
        own = db.scalar(select(Substance.slug).where(Substance.cas == cas).limit(1))
        return {'substance': own} if own else None
    hidden = get_setting(db, 'hidden_categories')
    items = [p for p in db.scalars(select(Product).where(Product.cas == cas, visible(db))
                                   .order_by(Product.popularity.desc(), Product.name_en).limit(CAS_ITEMS))]
    out = previews(db, items, lang)
    out = [p for p in out if not hidden_category(p['categorySlug'], hidden)]
    paths = sorted({p['categorySlug'].split('/')[0] for p in out})
    sections: list[dict[str, Any]] = [{'path': c.path, 'nameRu': c.name_ru, 'nameEn': c.name_en}
                for c in db.scalars(select(Category).where(Category.path.in_(paths)))]
    order = {path: i for i, path in enumerate(row.sections)}
    sections.sort(key=lambda s: order.get(s['path'], len(order)))
    names = get_setting(db, 'cas_names_ru') or {}
    return {'page': {**cas_ref(row, names), 'synonyms': row.synonyms, 'formula': row.formula,
                     'molecularWeight': row.molecular_weight, 'brands': row.brands, 'updatedAt': iso(row.updated_at),
                     'letter': cas_build.letter(row.sort_key)},
            'sections': sections, 'items': out, 'neighbours': cas_neighbours(db, row)}


def cas_sitemap(db: Session, page: int) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(CasPage)) or 0
    page_count = max(1, -(-total // SITEMAP_PAGE))
    page = max(1, min(page, page_count))
    rows = db.execute(select(CasPage.cas, CasPage.updated_at).order_by(CasPage.cas)
                      .offset((page - 1) * SITEMAP_PAGE).limit(SITEMAP_PAGE)).all()
    return {'items': [{'cas': cas, 'updatedAt': iso(updated)} for cas, updated in rows], 'total': total,
            'page': page, 'pageCount': page_count}


# ── products ──

def _column_key(product: Product) -> tuple[Any, ...]:
    a: dict[str, list[Any]] = product.attributes or {}
    return tuple((a.get(k) or [None])[0] for k in ('phase', 'length', 'diameter', 'particle'))


def _in_category(path: str) -> Select[Any]:
    return select(ProductCategory.product_id).join(Category, Category.id == ProductCategory.category_id) \
        .where(Category.path == path)


def product_page(db: Session, slug: str, lang: str) -> dict[str, Any]:
    product = db.scalar(select(Product).where(Product.slug == slug, visible(db)))
    if product is None:
        return {'moved': moved(db, 'product', slug, Product)}
    ctx = documents.Context(db, get_setting(db, 'hide_controlled'))
    docs, _ = documents.build(db, [product], ctx)
    base = preview(docs[0], lang, brand_pages(db))
    substance = db.get(Substance, product.substance_id) if product.substance_id else None
    primary = docs[0]['category']

    same: list[Product] = []
    same_total = 0
    if substance:
        condition = and_(Product.substance_id == substance.id, Product.id != product.id, visible(db))
        same_total = db.scalar(select(func.count()).select_from(Product).where(condition)) or 0
        same = list(db.scalars(select(Product).where(condition)
                               .order_by(_role_order(), Product.popularity.desc()).limit(8)))

    analogues: list[Product] = []
    if product.cas:
        analogues = list(db.scalars(select(Product).where(
            Product.cas == product.cas, Product.brand_id != product.brand_id, Product.id != product.id, visible(db))
            .order_by(Product.popularity.desc()).limit(4)))
    elif primary == HPLC:
        columns = list(db.scalars(select(Product).where(Product.id.in_(_in_category(HPLC)),
                                                        Product.brand_id != product.brand_id, visible(db))
                                  .order_by(Product.popularity.desc()).limit(500)))
        key = _column_key(product)
        analogues = [p for p in columns if _column_key(p) == key] or \
            [p for p in columns if _column_key(p)[:2] == key[:2]]
        analogues = analogues[:4]
    manual = db.scalars(select(Product).join(ProductRelation, ProductRelation.related_id == Product.id).where(
        ProductRelation.product_id == product.id, ProductRelation.kind == 'analogue', visible(db))).all()
    analogues = list(dict.fromkeys([*manual, *analogues]))[:4]

    accessories = list(db.scalars(select(Product).join(ProductRelation, ProductRelation.related_id == Product.id)
                                  .where(ProductRelation.product_id == product.id,
                                         ProductRelation.kind == 'accessory', visible(db))))
    if not accessories and primary == HPLC:
        phase = (product.attributes or {}).get('phase', [None])[0]
        guards = [p for p in db.scalars(select(Product).where(
            Product.id.in_(_in_category('chromatography/precolumns')), visible(db))
            .order_by(Product.popularity.desc()).limit(200)) if (p.attributes or {}).get('phase', [None])[0] == phase]
        guards.sort(key=lambda p: p.brand_id != product.brand_id)
        filters = list(db.scalars(select(Product).where(Product.id.in_(_in_category('chromatography/filters')),
                                                        visible(db)).limit(1)))
        accessories = guards[:3] + filters

    docs_rows = db.scalars(select(Document).where(Document.product_id == product.id).order_by(Document.position))
    detail = {
        **base,
        'nameRu': product.name_ru, 'synonyms': product.synonyms, 'altCas': product.alt_cas,
        'formula': product.formula, 'molecularWeight': product.molecular_weight, 'iupacName': product.iupac_name,
        'purity': product.purity, 'storage': product.storage, 'shipping': product.shipping,
        'dangerousGoods': product.dangerous_goods, 'texts': product.texts,
        'uniqueDescription': product.unique_description,
        'documents': [{'type': d.type, 'lang': d.lang, 'titleRu': d.title_ru, 'titleEn': d.title_en, 'href': d.href}
                      for d in docs_rows],
        'completeness': product.completeness, 'indexable': product.indexable, 'availability': product.availability,
        'seo': product.seo or {}, 'updatedAt': iso(product.updated_at),
    }
    return {
        'product': detail,
        'categories': breadcrumb(db, primary, lang),
        'substance': substance_out(substance) if substance else None,
        'sameSubstance': previews(db, same, lang),
        'sameSubstanceTotal': same_total,
        'analogues': previews(db, analogues, lang),
        'accessories': previews(db, accessories, lang),
        'casPage': cas_ref(found, get_setting(db, 'cas_names_ru')) if product.cas and (found := db.get(CasPage, product.cas))
        else None,
    }


# ── brands ──

def brand_out(db: Session, row: Brand) -> dict[str, Any]:
    count = db.scalar(select(func.count()).select_from(Product).where(Product.brand_id == row.id, visible(db))) or 0
    return {'slug': row.slug, 'name': row.name, 'logo': row.logo, 'country': row.country,
            'customPackaging': row.custom_packaging, 'wave': row.wave, 'content': row.content, 'count': count,
            'updatedAt': iso(row.updated_at)}


def brands(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(select(Brand).where(Brand.page_published.is_(True), Brand.merged_into_id.is_(None))
                      .order_by(Brand.position, Brand.name)).all()
    return [brand_out(db, row) for row in rows]


def brand_page(db: Session, slug: str, lang: str, *, include_hidden: bool = False) -> dict[str, Any]:
    """``include_hidden`` — the preview of a page not published yet (the admin panel's signed link)."""
    statement = select(Brand).where(Brand.slug == slug)
    row = db.scalar(statement if include_hidden else statement.where(Brand.page_published.is_(True)))
    if row is None or row.merged_into_id:
        target = db.get(Brand, row.merged_into_id) if row is not None and row.merged_into_id else None
        return {'moved': target.slug if target else moved(db, 'brand', slug, Brand)}
    top = list(db.scalars(select(Product).where(Product.brand_id == row.id, visible(db))
                          .order_by(Product.popularity.desc()).limit(8)))
    counted = db.execute(select(Category.path, func.count()).select_from(ProductCategory)
                         .join(Category, Category.id == ProductCategory.category_id)
                         .join(Product, Product.id == ProductCategory.product_id)
                         .where(Product.brand_id == row.id, ProductCategory.is_primary.is_(True), visible(db))
                         .group_by(Category.path).order_by(func.count().desc())).all()
    linked = ((get_setting(db, 'cas_links') or {}).get('brands') or {}).get(row.slug) or []
    return {'brand': brand_out(db, row), 'products': previews(db, top, lang),
            'categories': [{'slug': path, 'count': n} for path, n in counted], 'casPages': cas_refs(db, linked)}


# ── Sitemap (SEO-04, SEO-07) and the feed (TZ 15.4) ──

SITEMAP_PAGE = 25000


def sitemap(db: Session, page: int) -> dict[str, Any]:
    condition = and_(visible(db), Product.indexable.is_(True))
    total = db.scalar(select(func.count()).select_from(Product).where(condition)) or 0
    page_count = max(1, -(-total // SITEMAP_PAGE))
    page = max(1, min(page, page_count))
    rows = db.execute(select(Product.slug, Product.updated_at, Product.texts, Product.unique_description)
                      .where(condition).order_by(Product.id).offset((page - 1) * SITEMAP_PAGE)
                      .limit(SITEMAP_PAGE)).all()
    # The English card exists when the description is a template or translated (EN-05).
    items = [{'slug': slug, 'updatedAt': iso(updated), 'hasEn': not unique or bool((texts or {}).get('en'))}
             for slug, updated, texts, unique in rows]
    return {'items': items, 'total': total, 'page': page, 'pageCount': page_count}


def feed(db: Session, limit: int = 50000) -> dict[str, Any]:
    settings_value = get_setting(db, 'feed')
    prefixes = settings_value.get('categories') or []
    brand_slugs = settings_value.get('brands') or []
    in_scope = select(ProductCategory.product_id).join(Category, Category.id == ProductCategory.category_id).where(
        ProductCategory.is_primary.is_(True))
    if prefixes:
        in_scope = in_scope.where(or_(*[or_(Category.path == p, Category.path.like(f'{p}/%')) for p in prefixes]))
    statement = select(Product).where(visible(db), Product.discontinued.is_(False), Product.id.in_(in_scope)) \
        .order_by(Product.popularity.desc())
    if brand_slugs:
        statement = statement.where(Product.brand_id.in_(select(Brand.id).where(Brand.slug.in_(brand_slugs))))
    products = list(db.scalars(statement.limit(limit)))
    ctx = documents.Context(db, get_setting(db, 'hide_controlled'))
    docs, _ = documents.build(db, products, ctx)
    by_id = {doc['id']: doc for doc in docs}
    items = []
    for product in products:
        doc = by_id.get(product.id)
        if not doc:
            continue
        description = ' '.join((product.texts.get('ru') or {}).get('description') or [])[:3000] or None
        items.append({'id': product.id, 'slug': product.slug, 'name': product.name_en, 'brand': doc['brand'],
                      'catalogNumber': product.catalog_number, 'cas': product.cas,
                      'categorySlug': doc['category'] or '', 'image': (doc['image'] or {}).get('src'),
                      'description': description, 'packagings': [p['label_ru'] for p in doc['packagings']],
                      'customPackaging': doc['custom_packaging']})
    return {'items': items, 'categories': tree(db)}
