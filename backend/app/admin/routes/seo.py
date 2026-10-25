"""SEO of the site (ADM-07): redirects, meta templates, robots.txt and the report on duplicates and indexing."""

import csv
import io
import re
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.admin.audit import record
from app.admin.editables import queue_revalidate
from app.admin.models import ContentPage, Redirect, SeoLanding
from app.admin.security import StaffDep, requires
from app.catalog.models import Brand, Category, Product
from app.catalog.settings import get_setting, set_setting
from app.core.db import DB
from app.core.errors import DomainError

router = APIRouter()
PATH_RE = re.compile(r'^/[^\s?#]*$')


def clean_path(value: str, field: str) -> str:
    """A path of the site: from /, without the domain and the query; full URLs are cut to their path."""
    text = value.strip()
    text = re.sub(r'^https?://[^/]+', '', text)
    text = text.split('?')[0].split('#')[0]
    if not PATH_RE.match(text):
        raise DomainError('PATH_INVALID', 'Адрес начинается с / и без пробелов, например /old-page/', 422, field)
    return text


def final_target(db: DB, target: str, source: str) -> str:
    """Follow existing redirects from the target: no chains (one 301) and no loops."""
    seen = {source}
    current = target
    for _ in range(20):
        if current in seen:
            raise DomainError('REDIRECT_LOOP', f'Получится петля через {current}', 422, 'target')
        seen.add(current)
        nxt = db.scalar(select(Redirect.target).where(Redirect.source == current))
        if nxt is None:
            return current
        current = nxt
    raise DomainError('REDIRECT_LOOP', 'Слишком длинная цепочка редиректов', 422, 'target')


def redirect_out(row: Redirect) -> dict[str, Any]:
    return {'id': row.id, 'source': row.source, 'target': row.target, 'code': row.code, 'note': row.note,
            'updatedAt': row.updated_at.isoformat() if row.updated_at else None}


@router.get('/redirects', dependencies=[requires('seo.read')])
def redirects(db: DB, q: str = '', page: int = 1) -> dict[str, Any]:
    statement = select(Redirect)
    if q.strip():
        like = f'%{q.strip()}%'
        statement = statement.where(or_(Redirect.source.ilike(like), Redirect.target.ilike(like)))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(Redirect.source).offset((max(page, 1) - 1) * 100).limit(100))
    return {'total': total, 'items': [redirect_out(r) for r in rows]}


class RedirectIn(BaseModel):
    source: str = Field(max_length=400)
    target: str = Field(max_length=500)
    code: int = 301
    note: str | None = Field(default=None, max_length=300)


def save_redirect(db: DB, row: Redirect | None, body: RedirectIn) -> Redirect:
    source = clean_path(body.source, 'source')
    target = body.target.strip() if body.target.strip().startswith('http') else clean_path(body.target, 'target')
    if body.code not in (301, 302):
        raise DomainError('CODE_INVALID', 'Код: 301 или 302', 422, 'code')
    if source == target:
        raise DomainError('REDIRECT_LOOP', 'Адрес перенаправляет сам на себя', 422, 'target')
    if not target.startswith('http'):
        target = final_target(db, target, source)
    other = db.scalar(select(Redirect).where(Redirect.source == source))
    if other is not None and (row is None or other.id != row.id):
        raise DomainError('REDIRECT_EXISTS', 'С этого адреса редирект уже есть', 409, 'source')
    if row is None:
        row = Redirect(source=source, target=target, code=body.code, note=body.note)
        db.add(row)
    else:
        row.source, row.target, row.code, row.note = source, target, body.code, body.note
    # Redirects that pointed at the source now point straight at the new target (no chains, URL-11).
    for chained in db.scalars(select(Redirect).where(Redirect.target == source)):
        chained.target = target
    db.flush()
    return row


@router.post('/redirects', dependencies=[requires('seo.write')])
def create_redirect(body: RedirectIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    row = save_redirect(db, None, body)
    record(db, staff, 'redirect', row.id, 'create', f'{row.source} → {row.target} ({row.code})', None,
           redirect_out(row))
    queue_revalidate(db, ['redirects'])
    return redirect_out(row)


@router.put('/redirects/{redirect_id}', dependencies=[requires('seo.write')])
def update_redirect(redirect_id: str, body: RedirectIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    row = db.get(Redirect, redirect_id)
    if row is None:
        raise DomainError('NOT_FOUND', 'Редирект не найден', 404)
    before = redirect_out(row)
    save_redirect(db, row, body)
    record(db, staff, 'redirect', row.id, 'update', f'{row.source} → {row.target}', before, redirect_out(row))
    queue_revalidate(db, ['redirects'])
    return redirect_out(row)


@router.delete('/redirects/{redirect_id}', dependencies=[requires('seo.write')])
def delete_redirect(redirect_id: str, staff: StaffDep, db: DB) -> dict[str, bool]:
    row = db.get(Redirect, redirect_id)
    if row is not None:
        record(db, staff, 'redirect', row.id, 'delete', f'{row.source} → {row.target}', redirect_out(row), None)
        db.delete(row)
        queue_revalidate(db, ['redirects'])
    return {'ok': True}


class ImportIn(BaseModel):
    csv: str = Field(max_length=2_000_000)


@router.post('/redirects/import', dependencies=[requires('seo.write')])
def import_redirects(body: ImportIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    """CSV «откуда;куда;код» (код необязателен, 301): строки с ошибками пропускаются и перечисляются."""
    sample = body.csv[:2000]
    delimiter = ';' if sample.count(';') >= sample.count(',') else ','
    created = updated = 0
    errors: list[str] = []
    for number, cells in enumerate(csv.reader(io.StringIO(body.csv), delimiter=delimiter), start=1):
        if not cells or not cells[0].strip() or cells[0].strip().lower() in ('source', 'откуда'):
            continue
        try:
            code = int(cells[2]) if len(cells) > 2 and cells[2].strip() else 301
            existing = db.scalar(select(Redirect).where(Redirect.source == clean_path(cells[0], 'source')))
            with db.begin_nested():
                save_redirect(db, existing, RedirectIn(source=cells[0], target=cells[1] if len(cells) > 1 else '',
                                                       code=code))
            created, updated = (created, updated + 1) if existing else (created + 1, updated)
        except (DomainError, ValueError, IndexError) as exc:
            errors.append(f'строка {number}: {getattr(exc, "message", str(exc))}')
    record(db, staff, 'redirect', 'import', 'import', f'добавлено {created}, изменено {updated}, ошибок {len(errors)}')
    queue_revalidate(db, ['redirects'])
    return {'created': created, 'updated': updated, 'errors': errors[:100]}


@router.get('/redirects/export', dependencies=[requires('seo.read')])
def export_redirects(db: DB) -> Response:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=';')
    writer.writerow(['source', 'target', 'code', 'note'])
    for row in db.scalars(select(Redirect).order_by(Redirect.source)):
        writer.writerow([row.source, row.target, row.code, row.note or ''])
    return Response('﻿' + out.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename="redirects.csv"'})


@router.get('/redirects/check', dependencies=[requires('seo.read')])
def check_redirects(db: DB) -> dict[str, Any]:
    """Цепочки и петли: каждая проблема с адресом, чтобы её исправить."""
    rows = {r.source: r.target for r in db.scalars(select(Redirect))}
    problems: list[dict[str, str]] = []
    for source, target in rows.items():
        if target in rows:
            seen, current = {source}, target
            while current in rows and current not in seen:
                seen.add(current)
                current = rows[current]
            kind = 'петля' if current in seen else 'цепочка'
            problems.append({'source': source, 'target': target, 'problem': f'{kind}: {target} тоже перенаправляет'})
    return {'total': len(rows), 'problems': problems}


# ── meta templates (SEO-02) and robots.txt (SEO-03) ──

@router.get('/seo/templates', dependencies=[requires('seo.read')])
def templates(db: DB) -> dict[str, Any]:
    return {'value': get_setting(db, 'meta_templates'),
            'placeholders': {'product': ['{name}', '{brand}', '{number}', '{cas}', '{ids}', '{logistics}'],
                             'substance': ['{name}', '{count}', '{brands}']}}


class TemplatesIn(BaseModel):
    value: dict[str, dict[str, dict[str, str]]]


@router.put('/seo/templates', dependencies=[requires('seo.write')])
def save_templates(body: TemplatesIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    allowed = {'product': {'title', 'titleNoCas', 'description'}, 'substance': {'title', 'description'}}
    clean: dict[str, Any] = {}
    for kind, fields in allowed.items():
        clean[kind] = {}
        for lang in ('ru', 'en'):
            values = (body.value.get(kind) or {}).get(lang) or {}
            clean[kind][lang] = {k: v.strip() for k, v in values.items() if k in fields and v.strip()}
            title = clean[kind][lang].get('title', '')
            if title and '{name}' not in title:
                raise DomainError('TEMPLATE_INVALID', f'В шаблоне Title ({kind}, {lang}) нужен {{name}}', 422,
                                  f'{kind}.{lang}.title')
    before = get_setting(db, 'meta_templates')
    set_setting(db, 'meta_templates', clean)
    record(db, staff, 'setting', 'meta_templates', 'update', 'шаблоны метатегов', before, clean)
    queue_revalidate(db, ['content', 'catalog'])
    return templates(db)


ROBOTS_LINE = re.compile(r'^(user-agent|disallow|allow|clean-param|crawl-delay|host|sitemap):\s*\S.*$', re.I)


@router.get('/seo/robots', dependencies=[requires('seo.read')])
def robots(db: DB) -> dict[str, str]:
    return {'extra': get_setting(db, 'robots_extra') or ''}


class RobotsIn(BaseModel):
    extra: str = Field(max_length=10_000)


@router.put('/seo/robots', dependencies=[requires('seo.write')])
def save_robots(body: RobotsIn, staff: StaffDep, db: DB) -> dict[str, str]:
    """Строки добавляются к обязательным правилам SEO-03; проверяется синтаксис и что каталог не закрыт."""
    lines = [line.strip() for line in body.extra.splitlines()]
    for number, line in enumerate(lines, start=1):
        if line and not line.startswith('#') and not ROBOTS_LINE.match(line):
            raise DomainError('ROBOTS_INVALID', f'Строка {number}: «{line}» — не директива robots.txt', 422, 'extra')
        if re.match(r'^disallow:\s*/(catalog|brands|services|articles|product)?/?$', line, re.I):
            raise DomainError('ROBOTS_INVALID', f'Строка {number} закрывает от индексации основные разделы (SEO-03)',
                              422, 'extra')
    value = '\n'.join(lines).strip()
    before = get_setting(db, 'robots_extra')
    set_setting(db, 'robots_extra', value)
    record(db, staff, 'setting', 'robots_extra', 'update', 'robots.txt', before, value)
    queue_revalidate(db, ['content'])
    return {'extra': value}


@router.get('/seo/report', dependencies=[requires('seo.read')])
def report(db: DB) -> dict[str, Any]:
    """Дубли Title и H1 среди индексируемых страниц и сводка индексируемости (ADM-07, SEO-02)."""
    seen: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    def add(lang: str, h1: Any, title: Any, where: str) -> None:
        for field, value in (('Title', title), ('H1', h1)):
            if isinstance(value, str) and value.strip():
                seen[(field, lang, value.strip().casefold())].append(where)

    for page in db.scalars(select(ContentPage).where(ContentPage.status == 'published')):
        for lang, value in (page.content or {}).items():
            if isinstance(value, dict):
                add(lang, value.get('h1'), value.get('title'), f'{page.kind}: {page.slug}')
    for category in db.scalars(select(Category).where(Category.is_indexed.is_(True))):
        for lang, value in (category.content or {}).items():
            if isinstance(value, dict):
                add(lang, value.get('h1'), value.get('title'), f'раздел: {category.path}')
    for brand in db.scalars(select(Brand).where(Brand.page_published.is_(True))):
        for lang, value in (brand.content or {}).items():
            if isinstance(value, dict):
                add(lang, value.get('h1'), value.get('title'), f'бренд: {brand.slug}')
    for landing in db.scalars(select(SeoLanding).where(SeoLanding.status == 'published')):
        for lang, value in (landing.content or {}).items():
            if isinstance(value, dict):
                add(lang, value.get('h1'), value.get('title'), f'посадочная: {landing.category_path}/{landing.slug}')
    for slug, seo in db.execute(select(Product.slug, Product.seo).where(Product.indexable.is_(True),
                                                                         Product.seo.is_not(None))):
        for lang, value in (seo or {}).items():
            if isinstance(value, dict):
                add(lang, value.get('h1'), value.get('title'), f'товар: {slug}')
    duplicates = [{'field': field, 'lang': lang, 'value': value, 'pages': pages}
                  for (field, lang, value), pages in seen.items() if len(pages) > 1]
    counts = dict(db.execute(select(Product.status, func.count()).group_by(Product.status)).all())
    indexable = db.scalar(select(func.count()).select_from(Product).where(Product.indexable.is_(True))) or 0
    return {'duplicates': sorted(duplicates, key=lambda d: (d['field'], d['value'])),
            'indexing': {'products': counts, 'indexable': indexable,
                         'pagesHidden': db.scalar(select(func.count()).select_from(ContentPage)
                                                  .where(ContentPage.status == 'hidden')) or 0,
                         'categoriesNoindex': db.scalar(select(func.count()).select_from(Category)
                                                        .where(Category.is_indexed.is_(False))) or 0,
                         'brandPages': db.scalar(select(func.count()).select_from(Brand)
                                                 .where(Brand.page_published.is_(True))) or 0,
                         'landings': db.scalar(select(func.count()).select_from(SeoLanding)
                                               .where(SeoLanding.status == 'published')) or 0}}
