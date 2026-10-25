"""Import of price lists into the catalog (TZ 9.5, 9.6).

A file is read as a stream and handled in chunks of 5 000 rows, each chunk in its own transaction, so progress
is visible and memory stays flat (IMP-07). For every row: the brand through the registry of spellings, the
catalog number normalized, CAS checked by its check digit, packagings parsed, a category by the rules (IMP-03).
Brand + normalized catalog number find the product: a new one is created, an existing one is updated except for
fields edited by hand, and a different CAS on the same number is a conflict that leaves the product as it was
(IMP-04, IMP-05). Every batch keeps a journal and can be rolled back (IMP-06).
"""

import hashlib
import html
import re
import zipfile
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.sax.saxutils import escape

from sqlalchemy import delete, func, insert, select, tuple_, update
from sqlalchemy.orm import Session, sessionmaker

from app.catalog import completeness, controlled
from app.catalog.importer.reader import read_rows
from app.catalog.importer.rules import card_type_for, category_for
from app.catalog.importer.sources import REQUIRED, TEMPLATES
from app.catalog.models import (
    Brand,
    BrandAlias,
    Category,
    Document,
    ImportBatch,
    ImportChange,
    ImportIssue,
    ImportSource,
    Packaging,
    Product,
    ProductCategory,
    Substance,
)
from app.catalog.normalize import (
    Pack,
    brand_key,
    clean_spaces,
    compact,
    parse_cas,
    parse_packs,
    product_slug,
    slugify,
    split_pack_suffix,
)
from app.catalog.settings import get_setting
from app.core.db import utcnow
from app.outbox.models import OutboxEvent

CHUNK = 5000
IN_STOCK = re.compile(r'в наличии|на складе|in stock|available', re.I)
CYRILLIC = re.compile('[а-яё]', re.I)
UPDATABLE = ('name_en', 'source_name', 'cas', 'availability')


class ImportFailed(Exception):
    pass


@dataclass
class Row:
    number: int
    brand: str
    catalog_number: str
    name: str
    cas: str | None
    packs: list[Pack]
    pack_numbers: dict[str, str]
    availability: str | None
    raw: dict[str, Any]


@dataclass
class Group:
    brand_id: str
    brand_name: str
    catalog_number: str
    norm: str
    rows: list[Row] = field(default_factory=list)

    @property
    def first(self) -> Row:
        return self.rows[0]


@dataclass
class State:
    source: ImportSource
    batch_id: str
    run_id: str
    options: dict[str, Any]
    dry_run: bool
    brand_filter: set[str]
    aliases: dict[str, str]
    brands: dict[str, Brand]
    categories: dict[str, str]
    substance_names: dict[str, str]
    register: controlled.Register
    weights: dict[str, int]
    threshold: int
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    reported_brands: set[str] = field(default_factory=set)


# ── helpers ──

def ensure_source(db: Session, code: str) -> ImportSource:
    source = db.scalar(select(ImportSource).where(ImportSource.code == code))
    if source is None:
        template = TEMPLATES.get(code)
        if template is None:
            raise ImportFailed(f'Неизвестный источник «{code}». Есть: {", ".join(TEMPLATES)}')
        source = ImportSource(code=code, name=template['name'], mapping=template['mapping'],
                              options=template['options'])
        db.add(source)
        db.flush()
    return source


def columns_of(header: list[str | None], mapping: dict[str, str]) -> dict[str, int]:
    titles = [clean_spaces(str(cell or '')).casefold() for cell in header]
    found: dict[str, int] = {}
    for field_name, title in mapping.items():
        wanted = clean_spaces(title).casefold()
        if wanted in titles:
            found[field_name] = titles.index(wanted)
    missing = [f for f in REQUIRED if f not in found]
    if missing:
        names = ', '.join(f'«{mapping.get(f, f)}»' for f in missing)
        raise ImportFailed(f'В файле нет колонок {names}. Заголовок: {", ".join(t for t in titles if t)}')
    return found


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def clean_name(value: str) -> str:
    """«& gamma; -Моноклональные…» → «γ-Моноклональные…»: entities broken by a space in the source."""
    fixed = re.sub(r'&\s*(#?\w+)\s*;\s*', lambda m: html.unescape(f'&{m.group(1)};'), value)
    return clean_spaces(fixed)[:500]


def load_state(db: Session, source: ImportSource, batch_id: str, run_id: str, dry_run: bool,
               brand_filter: Iterable[str]) -> State:
    aliases = {alias.normalized: alias.brand_id for alias in db.scalars(select(BrandAlias))}
    brands = {brand.id: brand for brand in db.scalars(select(Brand))}
    for brand in brands.values():
        aliases.setdefault(brand_key(brand.name), brand.id)
        aliases.setdefault(brand_key(brand.slug), brand.id)
    substance_names = {s.cas: s.name_en for s in db.scalars(select(Substance).where(Substance.cas.is_not(None)))
                       if s.cas}
    return State(
        source=source, batch_id=batch_id, run_id=run_id, options=source.options, dry_run=dry_run,
        brand_filter={brand_key(b) for b in brand_filter}, aliases=aliases, brands=brands,
        categories={c.path: c.id for c in db.scalars(select(Category))}, substance_names=substance_names,
        register=controlled.Register.load(db), weights=get_setting(db, 'completeness_weights'),
        threshold=get_setting(db, 'index_threshold'))


def issue(db: Session, state: State, row: int, kind: str, code: str, message: str,
          values: dict[str, Any] | None = None, product_id: str | None = None) -> None:
    state.counters[f'issues_{kind}'] += 1
    db.add(ImportIssue(batch_id=state.batch_id, row_number=row, kind=kind, code=code, message=message[:500],
                       values=values or {}, product_id=product_id))


# ── rows ──

def parse_row(db: Session, state: State, number: int, cells: list[str | None], cols: dict[str, int]) -> Row | None:
    def cell(name: str) -> str:
        index = cols.get(name)
        return clean_spaces(str(cells[index])) if index is not None and index < len(cells) and cells[index] else ''

    raw = {name: cell(name) for name in cols}
    brand, number_text = raw.get('brand', ''), raw.get('catalog_number', '')
    if not any(raw.values()):
        return None
    if brand_key(brand) in {brand_key(b) for b in state.options.get('skip_brands') or []}:
        state.counters['skipped'] += 1
        return None
    if state.brand_filter and brand_key(brand) not in state.brand_filter:
        state.counters['filtered'] += 1
        return None
    if not brand:
        issue(db, state, number, 'error', 'BRAND_EMPTY', 'Не указан производитель', raw)
        return None
    if not number_text:
        issue(db, state, number, 'error', 'CATALOG_NUMBER_EMPTY', 'Не указан каталожный номер', raw)
        return None
    cas, invalid = parse_cas(raw.get('cas'))
    if invalid:
        issue(db, state, number, 'warning', 'CAS_INVALID',
              f'CAS «{raw.get("cas")}» не проходит проверку контрольной цифры — позиция загружена без CAS', raw)
    packs = parse_packs(raw.get('pack'))
    pack_numbers: dict[str, str] = {}
    catalog_number = number_text[:150]
    if state.options.get('group_pack_suffix') and len(packs) <= 1:
        base, pack = split_pack_suffix(catalog_number, packs[0] if packs else None)
        if base != catalog_number and pack:
            pack_numbers[pack.key] = catalog_number
            catalog_number, packs = base, [pack]
    availability = None
    if state.options.get('availability') == 'column':
        availability = 'in_stock' if IN_STOCK.search(raw.get('availability', '')) else 'on_order'
    return Row(number=number, brand=brand, catalog_number=catalog_number, name=clean_name(raw.get('name', '')),
               cas=cas, packs=packs, pack_numbers=pack_numbers, availability=availability, raw=raw)


def resolve_brand(db: Session, state: State, row: Row) -> str | None:
    key = brand_key(row.brand)
    brand_id = state.aliases.get(key)
    if brand_id:
        return brand_id
    if not state.options.get('create_brands'):
        if key not in state.reported_brands:
            state.reported_brands.add(key)
            issue(db, state, row.number, 'error', 'BRAND_UNKNOWN',
                  f'Производителя «{row.brand}» нет в реестре: строки пропущены до сопоставления', row.raw)
        state.counters['unknown_brand_rows'] += 1
        return None
    if state.dry_run:
        brand_id = f'new:{key}'
    else:
        slug, n = slugify(row.brand, 100) or f'brand-{key[:20]}', 1
        while db.scalar(select(Brand.id).where(Brand.slug == slug)):
            n += 1
            slug = f'{slugify(row.brand, 95)}-{n}'
        brand = Brand(slug=slug, name=row.brand[:200], page_published=False, content={})
        db.add(brand)
        db.flush()
        db.add(BrandAlias(brand_id=brand.id, name=row.brand[:250], normalized=key, source='import'))
        state.brands[brand.id] = brand
        brand_id = brand.id
    state.aliases[key] = brand_id
    state.counters['brands_created'] += 1
    issue(db, state, row.number, 'review', 'BRAND_CREATED',
          f'Новый производитель «{row.brand}»: создан бренд без страницы, сверьте с реестром CRM', row.raw)
    return brand_id


def display_name(state: State, group: Group) -> tuple[str, str | None]:
    """(English name, the source's name kept internally)."""
    name = next((r.name for r in group.rows if r.name), '')
    if state.options.get('names') == 'latin' and CYRILLIC.search(name):
        cas = next((r.cas for r in group.rows if r.cas), None)
        fallback = state.substance_names.get(cas or '') or f'{group.brand_name} {group.catalog_number}'
        return fallback[:500], name
    return (name or f'{group.brand_name} {group.catalog_number}')[:500], None


# ── one chunk ──

def process(db: Session, state: State, rows: list[Row]) -> None:
    groups: dict[tuple[str, str], Group] = {}
    for row in rows:
        brand_id = resolve_brand(db, state, row)
        if brand_id is None:
            continue
        norm = compact(row.catalog_number)
        if not norm:
            issue(db, state, row.number, 'error', 'CATALOG_NUMBER_EMPTY', 'Каталожный номер без букв и цифр', row.raw)
            continue
        brand_name = state.brands[brand_id].name if brand_id in state.brands else row.brand
        group = groups.setdefault((brand_id, norm), Group(brand_id, brand_name, row.catalog_number, norm))
        group.rows.append(row)
    if not groups:
        return
    keys = [key for key in groups if not key[0].startswith('new:')]
    existing: dict[tuple[str, str], Product] = {}
    if keys:
        for found in db.scalars(select(Product).where(tuple_(Product.brand_id, Product.catalog_number_norm)
                                                      .in_(keys))):
            existing[(found.brand_id, found.catalog_number_norm)] = found
    if state.dry_run:
        for key, group in groups.items():
            known = existing.get(key)
            if known is None:
                state.counters['created'] += 1
            elif known.cas and (cas := next((r.cas for r in group.rows if r.cas), None)) and cas != known.cas:
                state.counters['conflicts'] += 1
                issue(db, state, group.first.number, 'conflict', 'CAS_CONFLICT',
                      f'У {group.catalog_number} в каталоге CAS {known.cas}, в файле {cas}', group.first.raw,
                      known.id)
            else:
                state.counters['updated'] += 1
        return

    now = utcnow()
    new_products: list[dict[str, Any]] = []
    new_links: list[dict[str, Any]] = []
    new_packs: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    slugs = _free_slugs(db, state, [g for k, g in groups.items() if k not in existing])
    pack_keys = _pack_keys(db, [p.id for p in existing.values()])
    for key, group in groups.items():
        cas = next((r.cas for r in group.rows if r.cas), None)
        packs: dict[str, tuple[Pack, str | None, str | None]] = {}
        for row in group.rows:
            for pack in row.packs:
                packs.setdefault(pack.key, (pack, row.pack_numbers.get(pack.key), row.availability))
        name_en, source_name = display_name(state, group)
        hit = controlled.apply(state.register, name=name_en, cas=cas, synonyms=[source_name] if source_name else [],
                               current=None, state=None)
        product = existing.get(key)
        if product is None:
            path = category_for(group.brand_name, source_name or name_en)
            path = path if path in state.categories else None
            product_id = str(uuid4())
            availability = next((r.availability for r in group.rows if r.availability), None) or 'on_order'
            facts = completeness.facts(name=name_en, brand_id=group.brand_id, catalog_number=group.catalog_number,
                                       primary_category=path, packagings=len(packs),
                                       custom_packaging=bool(state.brands[group.brand_id].custom_packaging),
                                       images=[], texts={}, documents=0, substance_id=None, storage=None)
            score = completeness.score(facts, state.weights)
            new_products.append({
                'id': product_id, 'created_at': now, 'version': 1, 'card_type': card_type_for(path),
                'brand_id': group.brand_id, 'catalog_number': group.catalog_number, 'catalog_number_norm': group.norm,
                'slug': slugs[key], 'name_en': name_en, 'name_ru': None, 'source_name': source_name, 'synonyms': [],
                'cas': cas, 'alt_cas': [], 'substance_id': None, 'substance_role': None, 'attributes': {},
                'formula': None, 'formula_hill': None, 'molecular_weight': None, 'smiles': None, 'iupac_name': None,
                'purity': None, 'storage': None, 'shipping': None, 'dangerous_goods': None, 'texts': {},
                'unique_description': False, 'images': [], 'availability': availability, 'custom_packaging': None,
                'discontinued': False, 'controlled': hit[0], 'controlled_state': hit[1],
                'source': f'import:{state.source.code}', 'created_batch_id': state.batch_id,
                'last_import_run': state.run_id, 'crm_product_id': None, 'status': 'published',
                'completeness': score,
                'index_override': None,
                'indexable': completeness.indexable(status='published', completeness=score,
                                                    threshold=state.threshold, override=None,
                                                    controlled=bool(hit[0])),
                'seo': {}, 'popularity': 0, 'manual_fields': [], 'needs_index': True, 'published_at': now,
                'updated_at': now,
            })
            if path:
                new_links.append({'product_id': product_id, 'category_id': state.categories[path], 'is_primary': True})
            else:
                state.counters['without_category'] += 1
            for i, (pack, number, pack_availability) in enumerate(packs.values()):
                new_packs.append(_pack_row(product_id, i, pack, number, pack_availability, None))
            state.counters['created'] += 1
            state.counters['packagings'] += len(packs)
            continue

        if product.cas and cas and product.cas != cas:
            state.counters['conflicts'] += 1
            issue(db, state, group.first.number, 'conflict', 'CAS_CONFLICT',
                  f'У {group.catalog_number} в каталоге CAS {product.cas}, в файле {cas}: товар не изменён',
                  group.first.raw, product.id)
            continue
        manual = set(product.manual_fields or [])
        wanted: dict[str, Any] = {'name_en': name_en, 'source_name': source_name, 'cas': product.cas or cas}
        from_file = next((r.availability for r in group.rows if r.availability), None)
        if from_file:
            wanted['availability'] = from_file
        if not product.source.startswith('import:'):
            # Products written by people or the seed keep their names; imports add only what is missing.
            wanted.pop('name_en', None)
            wanted.pop('source_name', None)
        before = {f: getattr(product, f) for f, value in wanted.items()
                  if f not in manual and getattr(product, f) != value}
        added = [(pack, number, pack_availability) for pack, number, pack_availability in packs.values()
                 if (product.id, pack.key) not in pack_keys]
        for i, (pack, number, pack_availability) in enumerate(added):
            new_packs.append(_pack_row(product.id, 100 + len(pack_keys) + i, pack, number, pack_availability,
                                       state.batch_id))
            pack_keys.add((product.id, pack.key))
        values: dict[str, Any] = {'id': product.id, 'last_import_run': state.run_id}
        if before or added:
            values.update({f: wanted[f] for f in before})
            values.update(needs_index=True, updated_at=now)
            changes.append({'batch_id': state.batch_id, 'product_id': product.id,
                            'before': {k: v for k, v in before.items()}})
            state.counters['updated'] += 1
            state.counters['packagings'] += len(added)
        else:
            state.counters['unchanged'] += 1
        updates.append(values)

    if new_products:
        db.execute(insert(Product), new_products)
    if new_links:
        db.execute(insert(ProductCategory), new_links)
    if new_packs:
        db.execute(insert(Packaging), new_packs)
    for keyset in _by_keys(updates):
        db.execute(update(Product), keyset)
    if changes:
        db.execute(insert(ImportChange), changes)


def _by_keys(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(sorted(row))].append(row)
    return list(groups.values())


def _pack_row(product_id: str, position: int, pack: Pack, number: str | None, availability: str | None,
              batch_id: str | None) -> dict[str, Any]:
    return {'id': str(uuid4()), 'created_at': utcnow(), 'version': 1, 'product_id': product_id, 'position': position,
            'key': pack.key, 'amount': pack.amount, 'unit': pack.unit, 'label_ru': pack.label_ru[:120],
            'label_en': pack.label_en[:120], 'catalog_number': number,
            'catalog_number_norm': compact(number) or None if number else None,
            'availability': availability or 'on_order', 'price_estimate': None, 'crm_packing_id': None,
            'created_batch_id': batch_id}


def _pack_keys(db: Session, product_ids: list[str]) -> set[tuple[str, str]]:
    if not product_ids:
        return set()
    return {(pid, key) for pid, key in db.execute(select(Packaging.product_id, Packaging.key)
                                                  .where(Packaging.product_id.in_(product_ids)))}


def _free_slugs(db: Session, state: State, groups: list[Group]) -> dict[tuple[str, str], str]:
    wanted: dict[tuple[str, str], str] = {}
    for group in groups:
        brand = state.brands[group.brand_id]
        name_en, source_name = display_name(state, group)
        # A card named by its number gets the brand and the number only, not them twice.
        fallback = name_en == f'{group.brand_name} {group.catalog_number}'[:500]
        wanted[(group.brand_id, group.norm)] = product_slug(brand.slug, group.catalog_number,
                                                            '' if fallback else name_en)
    taken = set(db.scalars(select(Product.slug).where(Product.slug.in_(set(wanted.values()))))) if wanted else set()
    out: dict[tuple[str, str], str] = {}
    for key, slug in wanted.items():
        candidate, n = slug, 1
        while candidate in taken:
            n += 1
            candidate = f'{slug[:76]}-{n}'
            if n > 3 and db.scalar(select(Product.id).where(Product.slug == candidate)):
                taken.add(candidate)
        taken.add(candidate)
        out[key] = candidate
    return out


# ── files ──

def import_file(session_factory: sessionmaker[Session], path: Path, *, source: str, run_id: str, dry_run: bool,
                brands: list[str], limit: int | None, progress: Callable[[int], None] | None) -> dict[str, Any]:
    with session_factory.begin() as db:
        source_row = ensure_source(db, source)
        batch = ImportBatch(source_id=source_row.id, file_name=path.name, file_sha256=file_sha256(path),
                            dry_run=dry_run, status='running')
        db.add(batch)
        db.flush()
        batch_id = batch.id
        state = load_state(db, source_row, batch_id, run_id, dry_run, brands)
    rows_seen = 0
    try:
        reader = read_rows(path)
        header = next(reader, None)
        if header is None:
            raise ImportFailed('Файл пустой')
        cols = columns_of(header, state.source.mapping)
        pending: list[tuple[int, list[str | None]]] = []

        def flush() -> None:
            with session_factory.begin() as db:
                parsed = [r for r in (parse_row(db, state, n, cells, cols) for n, cells in pending) if r]
                process(db, state, parsed)
                db.execute(update(ImportBatch).where(ImportBatch.id == batch_id).values(
                    rows_done=rows_seen, counters=dict(state.counters)))
            pending.clear()
            if progress:
                progress(rows_seen)

        for number, cells in enumerate(reader, start=2):
            if limit and rows_seen >= limit:
                break
            rows_seen += 1
            pending.append((number, cells))
            if len(pending) >= CHUNK:
                flush()
        if pending:
            flush()
    except Exception as exc:
        with session_factory.begin() as db:
            db.execute(update(ImportBatch).where(ImportBatch.id == batch_id).values(
                status='failed', error=str(exc)[:2000], finished_at=utcnow(), rows_done=rows_seen,
                counters=dict(state.counters)))
        raise
    with session_factory.begin() as db:
        db.execute(update(ImportBatch).where(ImportBatch.id == batch_id).values(
            status='done', finished_at=utcnow(), rows_total=rows_seen, rows_done=rows_seen,
            counters=dict(state.counters)))
    return {'batch': batch_id, 'file': path.name, 'rows': rows_seen, **dict(state.counters)}


def import_files(session_factory: sessionmaker[Session], files: list[Path], *, source: str, dry_run: bool = False,
                 brands: list[str] | None = None, limit: int | None = None,
                 progress: Callable[[int], None] | None = None) -> dict[str, Any]:
    run_id = str(uuid4())
    results = [import_file(session_factory, path, source=source, run_id=run_id, dry_run=dry_run, brands=brands or [],
                           limit=limit, progress=progress) for path in files]
    marked = 0
    template = TEMPLATES.get(source, {})
    if not dry_run and not brands and not limit and template.get('options', {}).get('full_source'):
        with session_factory.begin() as db:
            marked = mark_unseen(db, source, run_id)
    return {'run': run_id, 'files': results, 'marked_on_order': marked}


def mark_unseen(db: Session, source: str, run_id: str) -> int:
    """A product the full source no longer lists stays on the site «Под заказ» (IMP-05)."""
    result = db.execute(update(Product).where(
        Product.source == f'import:{source}', Product.availability == 'in_stock',
        (Product.last_import_run.is_(None)) | (Product.last_import_run != run_id),
    ).values(availability='on_order', needs_index=True, updated_at=utcnow()))
    return int(getattr(result, 'rowcount', 0) or 0)


# ── journal, rollback ──

def rollback(db: Session, batch_id: str) -> dict[str, int]:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise ImportFailed('Партия не найдена')
    if batch.status == 'rolled_back':
        raise ImportFailed('Партия уже откачена')
    if batch.dry_run:
        raise ImportFailed('Это предпросмотр: в каталоге ничего не менялось')
    created = list(db.scalars(select(Product.id).where(Product.created_batch_id == batch_id)))
    for start in range(0, len(created), 5000):
        ids = created[start:start + 5000]
        db.execute(delete(Packaging).where(Packaging.product_id.in_(ids)))
        db.execute(delete(ProductCategory).where(ProductCategory.product_id.in_(ids)))
        db.execute(delete(Document).where(Document.product_id.in_(ids)))
        db.execute(delete(ImportChange).where(ImportChange.product_id.in_(ids)))
        db.execute(delete(Product).where(Product.id.in_(ids)))
        db.add(OutboxEvent(event_key=f'search-delete:{batch_id}:{start}', kind='search.delete',
                           payload={'ids': ids}))
    packs = db.execute(delete(Packaging).where(Packaging.created_batch_id == batch_id))
    restored = 0
    for change in db.scalars(select(ImportChange).where(ImportChange.batch_id == batch_id)
                             .order_by(ImportChange.id.desc())):
        values = {k: v for k, v in change.before.items() if k in UPDATABLE}
        db.execute(update(Product).where(Product.id == change.product_id).values(
            **values, needs_index=True, updated_at=utcnow()))
        restored += 1
    batch.status = 'rolled_back'
    batch.finished_at = utcnow()
    db.flush()
    return {'deleted': len(created), 'restored': restored, 'packagings_removed': int(getattr(packs, 'rowcount', 0))}


def issue_summary(db: Session, batch_id: str) -> list[str]:
    lines = [f'{kind:<9} {code:<22} {count}' for kind, code, count in db.execute(
        select(ImportIssue.kind, ImportIssue.code, func.count()).where(ImportIssue.batch_id == batch_id)
        .group_by(ImportIssue.kind, ImportIssue.code).order_by(func.count().desc()))]
    for row in db.scalars(select(ImportIssue).where(ImportIssue.batch_id == batch_id)
                          .order_by(ImportIssue.id).limit(20)):
        lines.append(f'  строка {row.row_number}: {row.message}')
    return lines or ['Замечаний нет.']


def export_issues(db: Session, batch_id: str, path: Path) -> int:
    """Errors and conflicts of a batch as xlsx (IMP-06): row, kind, code, message and the source values."""
    header = ['Строка', 'Тип', 'Код', 'Сообщение', 'Производитель', 'Кат. №', 'Наименование', 'CAS', 'Фасовка']
    rows: list[list[Any]] = [header]
    for issue_row in db.scalars(select(ImportIssue).where(ImportIssue.batch_id == batch_id).order_by(ImportIssue.id)):
        v = issue_row.values or {}
        rows.append([issue_row.row_number, issue_row.kind, issue_row.code, issue_row.message, v.get('brand'),
                     v.get('catalog_number'), v.get('name'), v.get('cas'), v.get('pack')])
    write_xlsx(path, rows)
    return len(rows) - 1


def write_xlsx(path: Path, rows: list[list[Any]]) -> None:
    def cell(ref: str, value: Any) -> str:
        if value is None or value == '':
            return ''
        if isinstance(value, int | float) and not isinstance(value, bool):
            return f'<c r="{ref}"><v>{value}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'

    def ref(col: int, row: int) -> str:
        letters = ''
        col += 1
        while col:
            col, rem = divmod(col - 1, 26)
            letters = chr(65 + rem) + letters
        return f'{letters}{row}'

    body = ''.join(f'<row r="{r + 1}">' + ''.join(cell(ref(c, r + 1), v) for c, v in enumerate(values)) + '</row>'
                   for r, values in enumerate(rows))
    ns = 'http://schemas.openxmlformats.org'
    files = {
        '[Content_Types].xml': f'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="{ns}/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        '_rels/.rels': f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{ns}/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{ns}/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="{ns}/spreadsheetml/2006/main" '
        f'xmlns:r="{ns}/officeDocument/2006/relationships"><sheets><sheet name="Замечания" sheetId="1" r:id="rId1"/>'
        '</sheets></workbook>',
        'xl/_rels/workbook.xml.rels': f'<?xml version="1.0" encoding="UTF-8"?><Relationships '
        f'xmlns="{ns}/package/2006/relationships"><Relationship Id="rId1" '
        f'Type="{ns}/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': f'<?xml version="1.0" encoding="UTF-8"?><worksheet '
        f'xmlns="{ns}/spreadsheetml/2006/main"><sheetData>{body}</sheetData></worksheet>',
    }
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


# ── catalog-wide rechecks ──

def recheck_controlled(db: Session) -> int:
    """After the lists change: every product against the register; the chemist's decisions stay."""
    register = controlled.Register.load(db)
    changed, last_id = 0, ''
    while True:
        rows = db.execute(select(Product.id, Product.name_en, Product.source_name, Product.synonyms, Product.cas,
                                 Product.controlled, Product.controlled_state).where(Product.id > last_id)
                          .order_by(Product.id).limit(10000)).all()
        if not rows:
            return changed
        updates = []
        for pid, name, source_name, synonyms, cas, current, state in rows:
            value = controlled.apply(register, name=name, cas=cas,
                                     synonyms=[*(synonyms or []), *([source_name] if source_name else [])],
                                     current=current, state=state)
            if value != (current, state):
                updates.append({'id': pid, 'controlled': value[0], 'controlled_state': value[1], 'needs_index': True})
        if updates:
            db.execute(update(Product), updates)
            changed += len(updates)
        last_id = rows[-1][0]


def refresh_all(db: Session) -> None:
    """After the threshold, the weights or the controlled setting change: indexability of every product."""
    threshold = get_setting(db, 'index_threshold')
    db.execute(update(Product).values(indexable=(Product.status == 'published') & Product.controlled.is_(None) & (
        Product.discontinued.is_(False)) & func.coalesce(Product.index_override, Product.completeness >= threshold)))
