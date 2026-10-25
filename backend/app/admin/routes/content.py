"""Pages of the site and their drafts (ADM-02): the editor of any page, category, brand, substance or landing.

Saving keeps a draft; «Опубликовать» applies it now or at the chosen time; the preview link shows the draft on the
storefront to whoever has it for 24 hours; every publication goes to the journal and can be restored.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.admin import editables
from app.admin.audit import history, record
from app.admin.models import PAGE_KINDS, AuditEntry, ContentPage, Draft, SeoLanding
from app.admin.security import Staff, StaffDep, requires
from app.catalog.normalize import slugify
from app.core.config import settings
from app.core.db import DB, as_utc, utcnow
from app.core.errors import DomainError

router = APIRouter()
RIGHTS = {'page': ('pages.read', 'pages.write'), 'category': ('taxonomy.read', 'taxonomy.write'),
          'brand': ('taxonomy.read', 'taxonomy.write'), 'substance': ('taxonomy.read', 'taxonomy.write'),
          'landing': ('seo.read', 'seo.write')}
KIND_NAMES = {'home': 'Главная', 'service': 'Услуги', 'solution': 'Решения', 'article': 'Статьи',
              'author': 'Авторы', 'trust': 'Страницы доверия'}


def allow(staff: Staff, entity: str, write: bool) -> None:
    if entity not in RIGHTS:
        raise DomainError('NOT_FOUND', 'Нет такого вида страниц', 404)
    staff.require(RIGHTS[entity][1 if write else 0])


def preview_url(kind: editables.Editable, row: Any, lang: str = 'ru') -> str:
    token = editables.preview_token(kind.entity, row.id)
    prefix = '/en' if lang == 'en' else ''
    return f'{settings.site_url.rstrip("/")}{prefix}{kind.path(row)}?preview={token}'


def editor_view(db: DB, entity: str, entity_id: str) -> dict[str, Any]:
    kind, row = editables.get_row(db, entity, entity_id)
    draft = editables.draft_of(db, entity, entity_id)
    published = kind.payload(db, row)
    return {'entity': entity, 'id': row.id, 'title': kind.title, 'label': kind.label(row), 'path': kind.path(row),
            'kind': getattr(row, 'kind', None), 'published': published,
            'draft': draft.data if draft else None,
            'publishAt': draft.publish_at.isoformat() if draft and draft.publish_at else None,
            'draftAuthor': draft.author_name if draft else None,
            'draftUpdatedAt': draft.updated_at.isoformat() if draft else None,
            'previewUrl': preview_url(kind, row), 'previewUrlEn': preview_url(kind, row, 'en'),
            'history': history(db, entity, row.id, limit=30)}


@router.get('/edit/{entity}/{entity_id}')
def editor(entity: str, entity_id: str, staff: StaffDep, db: DB) -> dict[str, Any]:
    allow(staff, entity, False)
    return editor_view(db, entity, entity_id)


class DraftIn(BaseModel):
    data: dict[str, Any]


@router.put('/edit/{entity}/{entity_id}/draft')
def save_draft(entity: str, entity_id: str, body: DraftIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    allow(staff, entity, True)
    editables.save_draft(db, staff, entity, entity_id, body.data)
    return editor_view(db, entity, entity_id)


class PublishIn(BaseModel):
    at: datetime | None = Field(default=None, description='Отложенная публикация; пусто — сейчас')


@router.post('/edit/{entity}/{entity_id}/publish')
def publish(entity: str, entity_id: str, body: PublishIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    allow(staff, entity, True)
    if body.at is not None and as_utc(body.at) > utcnow():
        draft = editables.draft_of(db, entity, entity_id)
        if draft is None:
            raise DomainError('NO_DRAFT', 'Сначала сохраните черновик', 409)
        draft.publish_at = as_utc(body.at)
        record(db, staff, entity, entity_id, 'schedule', f'публикация {as_utc(body.at):%d.%m.%Y %H:%M} UTC')
    else:
        editables.publish(db, staff, entity, entity_id)
    return editor_view(db, entity, entity_id)


@router.delete('/edit/{entity}/{entity_id}/draft')
def discard(entity: str, entity_id: str, staff: StaffDep, db: DB) -> dict[str, Any]:
    allow(staff, entity, True)
    draft = editables.draft_of(db, entity, entity_id)
    if draft is not None:
        db.delete(draft)
        db.flush()
    return editor_view(db, entity, entity_id)


@router.post('/edit/{entity}/{entity_id}/restore/{entry_id}')
def restore(entity: str, entity_id: str, entry_id: int, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Версия из журнала становится черновиком: её можно проверить и опубликовать (ADM-01)."""
    allow(staff, entity, True)
    entry = db.get(AuditEntry, entry_id)
    if entry is None or entry.entity != entity or entry.entity_id != entity_id or entry.after is None:
        raise DomainError('NOT_FOUND', 'Версия не найдена', 404)
    editables.save_draft(db, staff, entity, entity_id, entry.after)
    return editor_view(db, entity, entity_id)


# ── pages ──

def page_row(db: DB, row: ContentPage, drafts: dict[str, Draft]) -> dict[str, Any]:
    ru = (row.content or {}).get('ru') or {}
    draft = drafts.get(row.id)
    return {'id': row.id, 'kind': row.kind, 'slug': row.slug, 'title': ru.get('h1') or ru.get('name') or row.slug,
            'status': row.status, 'position': row.position, 'hasEn': bool((row.content or {}).get('en')),
            'hasDraft': draft is not None, 'publishAt': draft.publish_at.isoformat() if draft and draft.publish_at
            else None, 'updatedAt': row.updated_at.isoformat() if row.updated_at else None,
            'path': editables.PageEditable.PATHS[row.kind].format(slug=row.slug)}


@router.get('/pages', dependencies=[requires('pages.read')])
def pages(db: DB, kind: str | None = None) -> dict[str, Any]:
    statement = select(ContentPage).order_by(ContentPage.kind, ContentPage.position, ContentPage.slug)
    if kind:
        statement = statement.where(ContentPage.kind == kind)
    rows = list(db.scalars(statement))
    drafts = {d.entity_id: d for d in db.scalars(select(Draft).where(Draft.entity == 'page'))}
    return {'items': [page_row(db, row, drafts) for row in rows],
            'kinds': [{'key': k, 'name': KIND_NAMES[k]} for k in PAGE_KINDS]}


def blank(value: Any) -> Any:
    """The skeleton of a page of the same kind: the shape stays, the texts go."""
    if isinstance(value, dict):
        return {k: blank(v) for k, v in value.items()}
    if isinstance(value, list):
        return [blank(value[0])] if value and isinstance(value[0], (dict, list)) else []
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value
    return ''


class NewPageIn(BaseModel):
    kind: str
    slug: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)


@router.post('/pages', dependencies=[requires('pages.write')])
def create_page(body: NewPageIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    """Новая страница скрыта, пока её не опубликуют; поля — как у страниц того же вида."""
    if body.kind not in PAGE_KINDS or body.kind in ('home',):
        raise DomainError('KIND_INVALID', 'Такую страницу создать нельзя', 422, 'kind')
    slug = slugify(body.slug)
    if db.scalar(select(ContentPage.id).where(ContentPage.kind == body.kind, ContentPage.slug == slug)):
        raise DomainError('SLUG_TAKEN', 'Такой адрес уже занят', 409, 'slug')
    sample = db.scalar(select(ContentPage).where(ContentPage.kind == body.kind).order_by(ContentPage.position))
    skeleton = blank((sample.content or {}).get('ru') or {}) if sample else {}
    skeleton.update({'slug': slug, 'h1': body.title, 'title': body.title, 'description': ''})
    if 'name' in skeleton:
        skeleton['name'] = body.title
    last = db.scalar(select(ContentPage.position).where(ContentPage.kind == body.kind)
                     .order_by(ContentPage.position.desc())) or 0
    row = ContentPage(kind=body.kind, slug=slug, position=last + 1, content={'ru': skeleton}, status='hidden')
    db.add(row)
    db.flush()
    record(db, staff, 'page', row.id, 'create', f'{KIND_NAMES[body.kind]}: {body.title}')
    db.add(Draft(entity='page', entity_id=row.id, data={'slug': slug, 'position': row.position, 'status': 'published',
                                                        'content': {'ru': skeleton}},
                 author_id=staff.id, author_name=staff.name))
    db.flush()
    return editor_view(db, 'page', row.id)


# ── SEO landings (URL-07) ──

@router.get('/landings', dependencies=[requires('seo.read')])
def landings(db: DB) -> dict[str, Any]:
    drafts = {d.entity_id for d in db.scalars(select(Draft).where(Draft.entity == 'landing'))}
    rows = db.scalars(select(SeoLanding).order_by(SeoLanding.category_path, SeoLanding.position))
    return {'items': [{'id': r.id, 'categoryPath': r.category_path, 'slug': r.slug, 'filters': r.filters,
                       'name': ((r.content or {}).get('ru') or {}).get('name') or r.slug, 'status': r.status,
                       'hasEn': bool((r.content or {}).get('en')), 'hasDraft': r.id in drafts,
                       'path': f'/catalog/{r.category_path}/{r.slug}/'} for r in rows]}


class NewLandingIn(BaseModel):
    categoryPath: str
    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    filters: dict[str, list[str]] = {}


@router.post('/landings', dependencies=[requires('seo.write')])
def create_landing(body: NewLandingIn, staff: StaffDep, db: DB) -> dict[str, Any]:
    row = SeoLanding(category_path=body.categoryPath.strip('/'), slug=slugify(body.slug), filters=body.filters,
                     content={'ru': {'name': body.name, 'h1': body.name, 'title': body.name, 'description': '',
                                     'intro': '', 'facets': []}}, status='hidden')
    if db.scalar(select(SeoLanding.id).where(SeoLanding.category_path == row.category_path,
                                             SeoLanding.slug == row.slug)):
        raise DomainError('SLUG_TAKEN', 'Такая посадочная уже есть', 409, 'slug')
    db.add(row)
    db.flush()
    record(db, staff, 'landing', row.id, 'create', body.name)
    return editor_view(db, 'landing', row.id)
