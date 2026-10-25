"""Search and category listings over the engine (TZ 5.5, 6).

Order of results (SRCH-04): exact catalog number or CAS → gross formula → full-text relevance; on equal
relevance products in stock and with fuller cards go first. The exact matches are found by a separate filter
query and put first, so «Y0001897 → EDQM first» never depends on ranking settings. When nothing is found the
query is retried in the other keyboard layout (SRCH-05).
"""

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import Brand, Category, Packaging, SearchMiss, Substance
from app.catalog.normalize import compact, hill_key, looks_like_number, normalize_query, switch_layout
from app.catalog.search.documents import FACET_FIELDS, NUMBER_FIELDS
from app.catalog.search.engine import Query, Result, SearchEngine, any_of, quote
from app.core.config import settings
from app.core.db import utcnow

SUGGEST_MIN = 2
SUGGEST_LIMIT = 6
SEARCH_PAGE_SIZE = 24
EXACT_LIMIT = 50
BATCH_LIMIT = 200
TRANSLATED_FACETS = ('storage', 'purpose', 'type')


# ── documents → storefront shapes ──

def preview(hit: dict[str, Any], lang: str) -> dict[str, Any]:
    """A product preview in the storefront's shape (ProductPreview)."""
    ru = lang != 'en'
    attributes = {key: hit.get(key) or [] for key in ('storage', 'purpose', 'type', 'phase', 'length', 'diameter',
                                                       'particle', 'ph') if hit.get(key)}
    attributes['brand'] = [hit['brand_slug']]
    attributes['pack'] = hit.get('packs') or []
    brand = {'slug': hit['brand_slug'], 'name': hit['brand'], 'logo': hit.get('brand_logo')}
    if not ru and hit['brand_slug'] == 'various':
        brand['name'] = 'Various manufacturers'
    return {
        'id': hit['id'],
        'slug': hit['slug'],
        'cardType': hit['card_type'],
        'name': hit['name'],
        'brand': brand,
        'catalogNumber': hit['catalog_number'],
        'cas': hit.get('cas'),
        'categorySlug': hit.get('category') or '',
        'packagings': [{'id': f'{hit["id"]}-{p["key"]}', 'label': p['label_ru'] if ru else p['label_en'],
                        'catalogNumber': p.get('catalog_number')} for p in hit.get('packagings') or []],
        'customPackaging': bool(hit.get('custom_packaging')),
        'image': hit.get('image'),
        'discontinued': bool(hit.get('discontinued')),
        'substance': {'slug': hit['substance_slug'], 'role': hit['substance_role']} if hit.get('substance_slug')
        else None,
        'attributes': attributes,
        'popularity': hit.get('popularity') or 0,
    }


def candidate(hit: dict[str, Any], lang: str) -> dict[str, Any]:
    full = preview(hit, lang)
    return {key: full[key] for key in ('id', 'slug', 'name', 'brand', 'catalogNumber', 'cas', 'categorySlug',
                                       'packagings', 'customPackaging', 'cardType')}


# ── the ranked product search ──

@dataclass
class Found:
    hits: list[dict[str, Any]]
    total: int
    matches: dict[str, str] = field(default_factory=dict)
    facets: dict[str, dict[str, int]] = field(default_factory=dict)
    corrected: str | None = None


def _and(*parts: str | None) -> str | None:
    present = [p for p in parts if p]
    return ' AND '.join(f'({p})' for p in present) if present else None


def _find_once(engine: SearchEngine, q: str, *, base: str | None, offset: int, limit: int,
               facets: list[str]) -> Found:
    qn, qc = normalize_query(q), compact(q)
    number = looks_like_number(q)
    formula = hill_key(q)
    queries: list[Query] = []
    exact_at = formula_at = -1
    if number:
        exact_at = len(queries)
        queries.append(Query(filter=_and(base, f'numbers = {quote(qc)} OR cas_numbers = {quote(qc)}'),
                             limit=EXACT_LIMIT, sort=['in_stock:desc', 'completeness:desc', 'popularity:desc']))
    if formula:
        formula_at = len(queries)
        queries.append(Query(filter=_and(base, f'formula_hill = {quote(formula)}'), limit=EXACT_LIMIT,
                             sort=['in_stock:desc', 'completeness:desc', 'popularity:desc']))
    results = engine.search(settings.meili_index, queries) if queries else []
    exact = results[exact_at].hits if exact_at >= 0 else []
    by_formula = results[formula_at].hits if formula_at >= 0 else []
    first: list[dict[str, Any]] = []
    matches: dict[str, str] = {}
    for hit in exact:
        first.append(hit)
        matches[hit['id']] = 'cas' if qc in (hit.get('cas_numbers') or []) and qc not in hit.get('numbers', []) \
            else 'catalogNumber'
    for hit in by_formula:
        if hit['id'] not in matches:
            first.append(hit)
            matches[hit['id']] = 'formula'
    exclude = f'NOT id IN [{", ".join(quote(h["id"]) for h in first)}]' if first else None

    # Full text: number-like queries search numbers only (prefixes of catalog numbers), the rest everything.
    text = Query(q=qc if number else qn, attributes=NUMBER_FIELDS if number else None,
                 matching_strategy='all' if number else 'last', filter=_and(base, exclude),
                 offset=max(0, offset - len(first)), limit=max(0, limit - max(0, len(first) - offset)) or 1)
    queries = [text]
    if facets:
        queries.append(Query(q=text.q, attributes=text.attributes, matching_strategy=text.matching_strategy,
                             filter=base, limit=0, facets=[*facets, 'all']))
    answers = engine.search(settings.meili_index, queries)
    rest = answers[0]
    if number and not rest.total and not first:
        # «C18», «4-hydroxy…»: digits in a name — search everything.
        text = Query(q=qn, filter=_and(base, exclude), offset=offset, limit=limit)
        queries = [text] + ([Query(q=qn, filter=base, limit=0, facets=[*facets, 'all'])] if facets else [])
        answers = engine.search(settings.meili_index, queries)
        rest = answers[0]
    page = (first[offset:offset + limit] + rest.hits)[:limit] if offset < len(first) else rest.hits[:limit]
    for hit in page:
        matches.setdefault(hit['id'], 'catalogNumber' if number else 'name')
    facet_result = answers[1].facets if facets and len(answers) > 1 else {}
    total = len(first) + rest.total
    if facet_result.get('all'):
        total = max(total, sum(facet_result['all'].values()))
    return Found(hits=page, total=total, matches=matches, facets=facet_result)


def find(engine: SearchEngine, query: str, *, base: str | None = None, offset: int = 0, limit: int = 20,
         facets: list[str] | None = None) -> Found:
    if len(normalize_query(query)) < SUGGEST_MIN:
        return Found(hits=[], total=0)
    found = _find_once(engine, query, base=base, offset=offset, limit=limit, facets=facets or [])
    if found.total:
        return found
    switched = switch_layout(normalize_query(query))
    if switched != normalize_query(query):
        alt = _find_once(engine, switched, base=base, offset=offset, limit=limit, facets=facets or [])
        if alt.total:
            alt.corrected = switched
            return alt
    return found


# ── suggestions (SRCH-01) ──

_DIRECTORY: dict[str, Any] = {'at': 0.0}


def _directory(db: Session) -> dict[str, Any]:
    """Substances, categories and brands for suggestion groups; small tables, cached for a minute."""
    if time.monotonic() - _DIRECTORY['at'] > 60:
        _DIRECTORY.update(
            at=time.monotonic(),
            substances=[(s.slug, s.name_ru, s.name_en, s.cas, s.synonyms) for s in db.scalars(select(Substance))],
            categories=[(c.path, c.name_ru, c.name_en, c.parent_id, c.id) for c in
                        db.scalars(select(Category).order_by(Category.position))],
            brands=[(b.slug, b.name) for b in db.scalars(select(Brand).where(Brand.page_published.is_(True),
                                                                             Brand.merged_into_id.is_(None)))],
        )
    return _DIRECTORY


def reset_directory() -> None:
    _DIRECTORY['at'] = 0.0


def _starts_word(text: str | None, q: str) -> bool:
    lowered = (text or '').casefold()
    return lowered.startswith(q) or any(w.startswith(q) for w in re.split(r'[\s,;()\[\]/«»"-]+', lowered) if w)


def suggest_groups(db: Session, q: str, lang: str) -> dict[str, Any]:
    directory, qc = _directory(db), compact(q)
    subs = [{'slug': slug, 'name': ru, 'nameEn': en} for slug, ru, en, cas, synonyms in directory['substances']
            if any(_starts_word(n, q) for n in (ru, en, *synonyms)) or (cas and compact(cas) == qc)][:3]
    names = {cid: (path, ru, en) for path, ru, en, _parent, cid in directory['categories']}
    categories = []
    if len(q) >= 3:
        for path, ru, en, parent, _cid in directory['categories']:
            name = (en or ru) if lang == 'en' else ru
            if not _starts_word(name, q):
                continue
            if parent and parent in names:
                parent_path, parent_ru, parent_en = names[parent]
                name = f'{name} — {(parent_en or parent_ru) if lang == "en" else parent_ru}'
            categories.append({'name': name, 'href': f'/catalog/{path}/'})
    brands = [{'slug': slug, 'name': name} for slug, name in directory['brands']
              if _starts_word(name, q) or slug.startswith(q)][:3]
    return {'substances': subs, 'categories': categories[:3], 'brands': brands}


def suggest(db: Session, engine: SearchEngine, query: str, lang: str, limit: int = SUGGEST_LIMIT) -> dict[str, Any]:
    q = normalize_query(query)
    if len(q) < SUGGEST_MIN:
        return {'query': query, 'items': [], 'total': 0, 'substances': [], 'categories': [], 'brands': []}
    found = find(engine, q, limit=limit)
    items = []
    for hit in found.hits:
        match = found.matches.get(hit['id'], 'name')
        item = {'id': hit['id'], 'slug': hit['slug'], 'name': hit['name'], 'brand': hit['brand'],
                'catalogNumber': hit['catalog_number'], 'cas': hit.get('cas'), 'cardType': hit['card_type'],
                'match': match}
        if match == 'formula':
            item['formula'] = hit.get('formula_hill')
        items.append(item)
    return {'query': query, 'corrected': found.corrected, 'total': found.total, 'items': items,
            **suggest_groups(db, found.corrected or q, lang)}


# ── facets ──

def _facet_values(db: Session, key: str, counts: dict[str, int], selected: list[str], lang: str,
                  brand_names: dict[str, str] | None = None) -> list[dict[str, Any]]:
    labels: dict[str, str] = {}
    if key == 'brand':
        labels = brand_names if brand_names is not None else _brand_names(db, list(counts) + selected)
    elif key == 'pack':
        labels = _pack_labels(db, [v for v in list(counts) + selected if v != 'custom'], lang)
    values: list[dict[str, Any]] = [{'value': value, 'label': labels.get(value, value), 'count': count,
                                     'selected': value in selected} for value, count in counts.items()]
    for value in selected:
        if value not in counts:
            values.append({'value': value, 'label': labels.get(value, value), 'count': 0, 'selected': True})
    values.sort(key=lambda v: (-int(v['count']), str(v['label']).casefold()))
    return values


_PACK_LABELS: dict[str, tuple[str, str]] = {}


def _pack_labels(db: Session, keys: list[str], lang: str) -> dict[str, str]:
    """Labels of packaging keys; a key always means the same packaging, so they are cached in the process."""
    missing = [k for k in keys if k not in _PACK_LABELS]
    if missing:
        for pack_key, ru, en in db.execute(select(Packaging.key, Packaging.label_ru, Packaging.label_en)
                                           .where(Packaging.key.in_(missing)).group_by(Packaging.key, Packaging.label_ru,
                                                                                       Packaging.label_en)):
            _PACK_LABELS.setdefault(pack_key, (ru, en))
        if len(_PACK_LABELS) > 50000:
            _PACK_LABELS.clear()
    return {k: _PACK_LABELS[k][1 if lang == 'en' else 0] for k in keys if k in _PACK_LABELS}


def _brand_names(db: Session, slugs: list[str]) -> dict[str, str]:
    if not slugs:
        return {}
    return {slug: name for slug, name in db.execute(select(Brand.slug, Brand.name).where(Brand.slug.in_(slugs)))}


def _filters(filters: dict[str, list[str]], skip: str | None = None) -> str | None:
    parts = [any_of(FACET_FIELDS[key], values) for key, values in filters.items()
             if values and key in FACET_FIELDS and key != skip]
    return ' AND '.join(parts) if parts else None


# ── category listing (TZ 5.5) ──

SORTS = {'popular': ['in_stock:desc', 'popularity:desc'], 'name': ['name_sort:asc']}


def listing(db: Session, engine: SearchEngine, *, path: str, filters: dict[str, list[str]],
            preset: dict[str, list[str]], sort: str, page: int, page_size: int, facet_keys: list[str],
            lang: str) -> dict[str, Any]:
    base = _and(f'categories = {quote(path)}' if path else None, _filters(preset))
    page_size = max(1, min(page_size, 96))
    page = max(1, min(page, settings.search_max_page))
    selected_keys = [k for k in facet_keys if filters.get(k)]
    other_keys = [k for k in facet_keys if not filters.get(k)]
    queries = [Query(filter=_and(base, _filters(filters)), sort=SORTS.get(sort, SORTS['popular']),
                     offset=(page - 1) * page_size, limit=page_size,
                     facets=[*(FACET_FIELDS[k] for k in other_keys if k in FACET_FIELDS), 'all'])]
    # Counts of a selected filter ignore its own selection, so the alternatives stay visible (disjunctive).
    for key in selected_keys:
        queries.append(Query(filter=_and(base, _filters(filters, skip=key)), limit=0, facets=[FACET_FIELDS[key]]))
    results = engine.search(settings.meili_index, queries)
    main = results[0]
    total = sum(main.facets.get('all', {}).values()) or main.total
    facet_counts: dict[str, dict[str, int]] = {}
    for key in other_keys:
        facet_counts[key] = main.facets.get(FACET_FIELDS.get(key, ''), {})
    for key, result in zip(selected_keys, results[1:], strict=True):
        facet_counts[key] = result.facets.get(FACET_FIELDS[key], {})
    page_count = max(1, min(math.ceil(total / page_size), settings.search_max_page))
    return {
        'items': [preview(hit, lang) for hit in main.hits],
        'total': total,
        'page': page,
        'pageSize': page_size,
        'pageCount': page_count,
        'facets': [{'key': key, 'values': _facet_values(db, key, facet_counts.get(key, {}), filters.get(key) or [],
                                                         lang)} for key in facet_keys],
    }


def count(engine: SearchEngine, path: str, preset: dict[str, list[str]]) -> int:
    base = _and(f'categories = {quote(path)}' if path else None, _filters(preset))
    result = engine.search(settings.meili_index, [Query(filter=base, limit=0, facets=['all'])])[0]
    return sum(result.facets.get('all', {}).values()) or result.total


def brands_in(db: Session, engine: SearchEngine, path: str, preset: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Manufacturers of a category with their product counts (the «Производители» block)."""
    base = _and(f'categories = {quote(path)}' if path else None, _filters(preset))
    result = engine.search(settings.meili_index, [Query(filter=base, limit=0, facets=['brand_slug'])])[0]
    counts = result.facets.get('brand_slug', {})
    rows = {b.slug: b for b in db.scalars(select(Brand).where(Brand.slug.in_(list(counts))))}
    out = [{'slug': slug, 'name': rows[slug].name, 'logo': rows[slug].logo, 'count': n}
           for slug, n in counts.items() if slug in rows]
    return sorted(out, key=lambda b: -b['count'])


# ── the search page /search/ (SRCH-07) ──

def search_page(db: Session, engine: SearchEngine, *, query: str, brand: str | None, category: str | None,
                page: int, lang: str) -> dict[str, Any]:
    q = normalize_query(query)
    empty = {'query': query, 'items': [], 'total': 0, 'page': 1, 'pageCount': 1,
             'facets': {'brand': [], 'category': []}}
    if len(q) < SUGGEST_MIN:
        return empty
    page = max(1, min(page, settings.search_max_page))
    filters = {'brand': [brand] if brand else [], 'category_top': [category] if category else []}

    def expr(skip: str | None = None) -> str | None:
        parts = []
        if filters['brand'] and skip != 'brand':
            parts.append(any_of('brand_slug', filters['brand']))
        if filters['category_top'] and skip != 'category':
            parts.append(any_of('category_top', filters['category_top']))
        return ' AND '.join(parts) if parts else None

    found = find(engine, q, base=expr(), offset=(page - 1) * SEARCH_PAGE_SIZE, limit=SEARCH_PAGE_SIZE)
    effective = found.corrected or q
    # Facet counts: each facet with the other facet's filter only.
    by_brand = find(engine, effective, base=expr('brand'), limit=0, facets=['brand_slug']) if found.total or brand \
        else Found(hits=[], total=0)
    by_category = find(engine, effective, base=expr('category'), limit=0, facets=['category_top']) \
        if found.total or category else Found(hits=[], total=0)
    if not found.total:
        record_miss(db, q, lang)
    names = {c.path: (c.name_en or c.name_ru) if lang == 'en' else c.name_ru
             for c in db.scalars(select(Category).where(Category.parent_id.is_(None)))}
    category_values: list[dict[str, Any]] = [
        {'value': value, 'label': names.get(value, value), 'count': n, 'selected': value == category}
        for value, n in by_category.facets.get('category_top', {}).items()]
    if category and category not in by_category.facets.get('category_top', {}):
        category_values.append({'value': category, 'label': names.get(category, category), 'count': 0,
                                'selected': True})
    category_values.sort(key=lambda v: (-int(v['count']), str(v['label'])))
    return {
        'query': query,
        'corrected': found.corrected,
        'items': [preview(hit, lang) for hit in found.hits],
        'total': found.total,
        'page': page,
        'pageCount': max(1, min(math.ceil(found.total / SEARCH_PAGE_SIZE), settings.search_max_page)),
        'facets': {'brand': _facet_values(db, 'brand', by_brand.facets.get('brand_slug', {}),
                                          [brand] if brand else [], lang),
                   'category': category_values},
    }


def record_miss(db: Session, query: str, lang: str) -> None:
    """Demand without a product (SRCH-06): the journal behind «топ запросов без результатов» (SRCH-12)."""
    q = normalize_query(query)[:200]
    if len(q) < SUGGEST_MIN:
        return
    row = db.scalar(select(SearchMiss).where(SearchMiss.query == q, SearchMiss.lang == lang).with_for_update())
    if row is None:
        db.add(SearchMiss(query=q, lang=lang))
    else:
        row.count += 1
        row.last_at = utcnow()
    db.flush()


# ── list search (SRCH-09, SC-02) ──

def parse_line(line: str) -> tuple[str, int]:
    """«Y0001897 2», «28721-07-5;3», «Paracetamol CRS» → query and quantity."""
    cols = [c.strip() for c in re.split(r'\t|;', line) if c.strip()]
    if len(cols) >= 2 and re.fullmatch(r'\d{1,3}', cols[-1]):
        return ' '.join(cols[:-1]), int(cols[-1])
    words = line.strip().split()
    if len(words) == 2 and re.fullmatch(r'\d{1,3}', words[1]) and re.search(r'\d', words[0]):
        return words[0], int(words[1])
    return line.strip(), 1


def batch(engine: SearchEngine, lines: list[str], lang: str) -> list[dict[str, Any]]:
    parsed = [(line, *parse_line(line)) for line in (raw.strip() for raw in lines) if line][:BATCH_LIMIT]
    if not parsed:
        return []
    exact_queries = [Query(filter=f'numbers = {quote(compact(q))} OR cas_numbers = {quote(compact(q))}', limit=5,
                           sort=['in_stock:desc', 'completeness:desc', 'popularity:desc'])
                     for _line, q, _n in parsed]
    exact = engine.search(settings.meili_index, exact_queries)
    pending = [i for i, result in enumerate(exact) if not result.hits and len(parsed[i][1]) >= 3]
    fuzzy: dict[int, Result] = {}
    if pending:
        answers = engine.search(settings.meili_index, [
            Query(q=normalize_query(parsed[i][1]), limit=5, matching_strategy='all') for i in pending])
        fuzzy = dict(zip(pending, answers, strict=True))
    out = []
    for i, (line, q, quantity) in enumerate(parsed):
        hits = exact[i].hits or (fuzzy[i].hits if i in fuzzy else [])
        status = 'none' if not hits else 'exact' if len(hits) == 1 else 'multiple'
        out.append({'line': line, 'query': q, 'quantity': max(1, min(999, quantity)), 'status': status,
                    'candidates': [candidate(hit, lang) for hit in hits[:5]]})
    return out
