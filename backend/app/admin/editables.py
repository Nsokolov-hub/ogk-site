"""Pages, categories, brands, substances and SEO landings edited through drafts (ADM-02).

Each kind knows its editable state (``payload``), how to check and write it (``apply``), where it lives on the
storefront (``path``) and which cached storefront data it touches (``tags``). A draft is the payload not yet
published; publishing applies it, writes the journal and drops the storefront's cache.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import date
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin import schemas
from app.admin.audit import changed_fields, record
from app.admin.models import ContentPage, Draft, Redirect, SeoLanding
from app.catalog.models import Brand, Category, Product, Substance
from app.catalog.normalize import cas_or_none, slugify
from app.catalog.service import queue_products
from app.catalog.settings import set_setting
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import DomainError
from app.outbox.models import OutboxEvent

PREVIEW_SECONDS = 24 * 3600


class Editable:
    entity: ClassVar[str]
    model: ClassVar[Any]
    title: ClassVar[str]

    def payload(self, db: Session, row: Any) -> dict[str, Any]:
        raise NotImplementedError

    def check(self, db: Session, row: Any, data: dict[str, Any]) -> dict[str, Any]:
        """Validated payload; raises DomainError with the field."""
        raise NotImplementedError

    def write(self, db: Session, row: Any, data: dict[str, Any]) -> None:
        raise NotImplementedError

    def path(self, row: Any) -> str:
        raise NotImplementedError

    def tags(self, row: Any) -> list[str]:
        return ['catalog']

    def label(self, row: Any) -> str:
        return str(getattr(row, 'slug', row.id))


def stamp(content: dict[str, Any]) -> dict[str, Any]:
    """The date of the change in every language version (sitemap lastmod, «Обновлено»)."""
    today = date.today().isoformat()
    return {lang: {**value, 'updatedAt': today} if isinstance(value, dict) and value else value
            for lang, value in content.items()}


def redirect_moved(db: Session, old: str, new: str) -> None:
    """A published address that changes answers 301 to the new one (URL-03); chains are collapsed."""
    if old == new:
        return
    for row in db.scalars(select(Redirect).where(Redirect.target == old)):
        row.target = new
    existing = db.scalar(select(Redirect).where(Redirect.source == old))
    if existing is None:
        db.add(Redirect(source=old, target=new, code=301, note='смена адреса в админке'))
    else:
        existing.target, existing.code = new, 301
    stale = db.scalar(select(Redirect).where(Redirect.source == new))
    if stale is not None:
        db.delete(stale)
    db.flush()


class PageEditable(Editable):
    entity, model, title = 'page', ContentPage, 'Страница'
    PATHS: ClassVar[dict[str, str]] = {'home': '/', 'service': '/services/{slug}/', 'solution': '/solutions/{slug}/',
                                       'article': '/articles/{slug}/', 'author': '/authors/{slug}/', 'trust': '/{slug}/'}

    def payload(self, db: Session, row: ContentPage) -> dict[str, Any]:
        return {'slug': row.slug, 'position': row.position, 'status': row.status, 'content': row.content}

    def check(self, db: Session, row: ContentPage, data: dict[str, Any]) -> dict[str, Any]:
        slug = str(data.get('slug') or row.slug)
        if row.kind not in ('home',) and slug != slugify(slug):
            raise DomainError('SLUG_INVALID', 'Адрес — латиница в нижнем регистре и дефисы', 422, 'slug')
        if slug != row.slug and db.scalar(select(ContentPage.id).where(
                ContentPage.kind == row.kind, ContentPage.slug == slug, ContentPage.id != row.id)):
            raise DomainError('SLUG_TAKEN', 'Такой адрес уже занят', 409, 'slug')
        content = schemas.check_localized(schemas.PAGE_SHAPES[row.kind], data.get('content'))
        for value in content.values():
            if 'slug' in value:
                value['slug'] = slug
        status = data.get('status', row.status)
        if status not in ('published', 'hidden'):
            raise DomainError('STATUS_INVALID', 'Статус: published или hidden', 422, 'status')
        return {'slug': slug, 'position': int(data.get('position', row.position) or 0), 'status': status,
                'content': content}

    def write(self, db: Session, row: ContentPage, data: dict[str, Any]) -> None:
        old_path = self.path(row) if row.status == 'published' else None
        row.slug, row.position, row.status = data['slug'], data['position'], data['status']
        row.content = stamp(data['content'])
        if row.status == 'published' and row.published_at is None:
            row.published_at = utcnow()
        if old_path:
            redirect_moved(db, old_path, self.path(row))

    def path(self, row: ContentPage) -> str:
        return self.PATHS[row.kind].format(slug=row.slug)

    def tags(self, row: ContentPage) -> list[str]:
        return ['content', f'page:{row.kind}:{row.slug}']

    def label(self, row: ContentPage) -> str:
        content = (row.content or {}).get('ru') or {}
        return str(content.get('h1') or content.get('name') or row.slug)


class CategoryEditable(Editable):
    entity, model, title = 'category', Category, 'Раздел каталога'

    def payload(self, db: Session, row: Category) -> dict[str, Any]:
        return {'nameRu': row.name_ru, 'nameEn': row.name_en, 'shortRu': row.short_ru, 'shortEn': row.short_en,
                'position': row.position, 'cardType': row.card_type, 'facets': row.facets,
                'isIndexed': row.is_indexed, 'content': row.content}

    def check(self, db: Session, row: Category, data: dict[str, Any]) -> dict[str, Any]:
        if not str(data.get('nameRu') or '').strip():
            raise DomainError('CONTENT_INVALID', 'Название раздела обязательно', 422, 'nameRu')
        if data.get('cardType', row.card_type) not in ('standard', 'equipment', 'other'):
            raise DomainError('CONTENT_INVALID', 'Тип карточки: standard, equipment или other', 422, 'cardType')
        facets = [str(f) for f in data.get('facets') or []]
        return {'nameRu': str(data['nameRu']).strip(), 'nameEn': (data.get('nameEn') or None),
                'shortRu': data.get('shortRu') or None, 'shortEn': data.get('shortEn') or None,
                'position': int(data.get('position') or 0), 'cardType': data.get('cardType', row.card_type),
                'facets': facets, 'isIndexed': bool(data.get('isIndexed', True)),
                'content': schemas.check_localized(schemas.CategoryText, data.get('content'))}

    def write(self, db: Session, row: Category, data: dict[str, Any]) -> None:
        row.name_ru, row.name_en, row.short_ru, row.short_en = (data['nameRu'], data['nameEn'], data['shortRu'],
                                                                data['shortEn'])
        row.position, row.card_type, row.facets, row.is_indexed = (data['position'], data['cardType'],
                                                                   data['facets'], data['isIndexed'])
        row.content = stamp({lang: {**value, 'facets': data['facets']} for lang, value in data['content'].items()})

    def path(self, row: Category) -> str:
        return f'/catalog/{row.path}/'

    def label(self, row: Category) -> str:
        return row.name_ru


class BrandEditable(Editable):
    entity, model, title = 'brand', Brand, 'Бренд'

    def payload(self, db: Session, row: Brand) -> dict[str, Any]:
        return {'name': row.name, 'country': row.country, 'logo': row.logo, 'isPartner': row.is_partner,
                'customPackaging': row.custom_packaging, 'pagePublished': row.page_published,
                'position': row.position, 'wave': row.wave, 'content': row.content}

    def check(self, db: Session, row: Brand, data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get('name') or '').strip()
        if not name:
            raise DomainError('CONTENT_INVALID', 'Название бренда обязательно', 422, 'name')
        published = bool(data.get('pagePublished'))
        content = data.get('content') or {}
        if published or (isinstance(content, dict) and content.get('ru')):
            content = schemas.check_localized(schemas.BrandText, content)
        wave = data.get('wave')
        return {'name': name, 'country': data.get('country') or None, 'logo': data.get('logo') or None,
                'isPartner': bool(data.get('isPartner')), 'customPackaging': bool(data.get('customPackaging')),
                'pagePublished': published, 'position': int(data.get('position') or 1000),
                'wave': int(wave) if wave in (1, 2, '1', '2') else None, 'content': content or {}}

    def write(self, db: Session, row: Brand, data: dict[str, Any]) -> None:
        reindex = (row.name != data['name'] or row.custom_packaging != data['customPackaging'])
        row.name, row.country, row.logo, row.is_partner = (data['name'], data['country'], data['logo'],
                                                           data['isPartner'])
        row.custom_packaging, row.page_published = data['customPackaging'], data['pagePublished']
        row.position, row.wave = data['position'], data['wave']
        content = data['content']
        row.content = stamp({lang: {**value, 'slug': row.slug, 'name': row.name} for lang, value in content.items()}) \
            if content else {}
        if reindex:
            queue_products(db, brand_ids=[row.id])

    def path(self, row: Brand) -> str:
        return f'/brands/{row.slug}/'

    def tags(self, row: Brand) -> list[str]:
        return ['catalog', f'brand:{row.slug}']

    def label(self, row: Brand) -> str:
        return row.name


class SubstanceEditable(Editable):
    entity, model, title = 'substance', Substance, 'Субстанция'

    def payload(self, db: Session, row: Substance) -> dict[str, Any]:
        return {'nameRu': row.name_ru, 'nameEn': row.name_en, 'cas': row.cas, 'formula': row.formula,
                'molecularWeight': row.molecular_weight, 'synonyms': row.synonyms, 'content': row.content}

    def check(self, db: Session, row: Substance, data: dict[str, Any]) -> dict[str, Any]:
        name_ru, name_en = str(data.get('nameRu') or '').strip(), str(data.get('nameEn') or '').strip()
        if not name_ru or not name_en:
            raise DomainError('CONTENT_INVALID', 'Нужны МНН на русском и на английском', 422, 'nameRu')
        cas = (data.get('cas') or '').strip() or None
        if cas and cas_or_none(cas) is None:
            raise DomainError('CAS_INVALID', 'CAS не прошёл проверку контрольной цифры', 422, 'cas')
        content = data.get('content') or {}
        out_content = {lang: schemas.check(schemas.SubstanceText, value, lang.upper())
                       for lang, value in content.items() if isinstance(value, dict)}
        synonyms = [s.strip() for s in data.get('synonyms') or [] if str(s).strip()]
        return {'nameRu': name_ru, 'nameEn': name_en, 'cas': cas_or_none(cas) if cas else None,
                'formula': data.get('formula') or None, 'molecularWeight': data.get('molecularWeight') or None,
                'synonyms': synonyms, 'content': out_content}

    def write(self, db: Session, row: Substance, data: dict[str, Any]) -> None:
        names_changed = (row.name_ru, row.name_en, row.synonyms) != (data['nameRu'], data['nameEn'], data['synonyms'])
        row.name_ru, row.name_en, row.cas = data['nameRu'], data['nameEn'], data['cas']
        row.formula, row.molecular_weight, row.synonyms = data['formula'], data['molecularWeight'], data['synonyms']
        row.content = data['content']
        queue_products(db, substance_ids=[row.id])
        if names_changed:
            # RU ↔ EN synonyms of the search come from substances (SRCH-05): the worker updates the index settings.
            set_setting(db, 'search_settings_dirty', True)

    def path(self, row: Substance) -> str:
        return f'/substances/{row.slug}/'

    def label(self, row: Substance) -> str:
        return row.name_ru


class LandingEditable(Editable):
    entity, model, title = 'landing', SeoLanding, 'SEO-посадочная'

    def payload(self, db: Session, row: SeoLanding) -> dict[str, Any]:
        return {'categoryPath': row.category_path, 'slug': row.slug, 'filters': row.filters, 'status': row.status,
                'position': row.position, 'content': row.content}

    def check(self, db: Session, row: SeoLanding, data: dict[str, Any]) -> dict[str, Any]:
        path = str(data.get('categoryPath') or row.category_path).strip('/')
        if db.scalar(select(Category.id).where(Category.path == path)) is None:
            raise DomainError('CATEGORY_NOT_FOUND', 'Нет такого раздела каталога', 422, 'categoryPath')
        slug = str(data.get('slug') or row.slug)
        if slug != slugify(slug):
            raise DomainError('SLUG_INVALID', 'Адрес — латиница в нижнем регистре и дефисы', 422, 'slug')
        if db.scalar(select(Category.id).where(Category.path == f'{path}/{slug}')):
            raise DomainError('SLUG_TAKEN', 'Этот адрес занят подразделом каталога', 409, 'slug')
        if db.scalar(select(SeoLanding.id).where(SeoLanding.category_path == path, SeoLanding.slug == slug,
                                                 SeoLanding.id != row.id)):
            raise DomainError('SLUG_TAKEN', 'Такая посадочная уже есть', 409, 'slug')
        filters = {str(k): [str(v) for v in values] for k, values in (data.get('filters') or {}).items() if values}
        if not filters:
            raise DomainError('CONTENT_INVALID', 'Посадочной нужен хотя бы один фиксированный фильтр', 422, 'filters')
        content = schemas.check_localized(schemas.CategoryText, data.get('content'))
        if not str(content['ru'].get('name') or '').strip():
            raise DomainError('CONTENT_INVALID', 'Нужна короткая подпись для чипов «Подборки»', 422, 'ru.name')
        status = data.get('status', row.status)
        if status not in ('published', 'hidden'):
            raise DomainError('STATUS_INVALID', 'Статус: published или hidden', 422, 'status')
        return {'categoryPath': path, 'slug': slug, 'filters': filters, 'status': status,
                'position': int(data.get('position') or 0), 'content': content}

    def write(self, db: Session, row: SeoLanding, data: dict[str, Any]) -> None:
        old_path = self.path(row) if row.status == 'published' and row.slug else None
        row.category_path, row.slug, row.filters = data['categoryPath'], data['slug'], data['filters']
        row.status, row.position, row.content = data['status'], data['position'], stamp(data['content'])
        if old_path:
            redirect_moved(db, old_path, self.path(row))

    def path(self, row: SeoLanding) -> str:
        return f'/catalog/{row.category_path}/{row.slug}/'

    def tags(self, row: SeoLanding) -> list[str]:
        return ['catalog', 'landings']

    def label(self, row: SeoLanding) -> str:
        return str(((row.content or {}).get('ru') or {}).get('name') or row.slug)


EDITABLES: dict[str, Editable] = {e.entity: e for e in (PageEditable(), CategoryEditable(), BrandEditable(),
                                                         SubstanceEditable(), LandingEditable())}


def editable(entity: str) -> Editable:
    if entity not in EDITABLES:
        raise DomainError('NOT_FOUND', 'Нет такого вида страниц', 404)
    return EDITABLES[entity]


def get_row(db: Session, entity: str, entity_id: str, *, lock: bool = False) -> tuple[Editable, Any]:
    kind = editable(entity)
    statement = select(kind.model).where(kind.model.id == entity_id)
    row = db.scalar(statement.with_for_update() if lock else statement)
    if row is None:
        raise DomainError('NOT_FOUND', f'{kind.title} не найдена', 404)
    return kind, row


def draft_of(db: Session, entity: str, entity_id: str) -> Draft | None:
    return db.scalar(select(Draft).where(Draft.entity == entity, Draft.entity_id == entity_id))


def queue_revalidate(db: Session, tags: list[str]) -> None:
    """Drop the storefront's cache after the commit: the worker posts the tags (app.core.storefront)."""
    db.add(OutboxEvent(event_key=f'revalidate:{utcnow().timestamp()}:{"|".join(tags)[:120]}',
                       kind='storefront.revalidate', payload={'tags': tags}))


def save_draft(db: Session, actor: Any, entity: str, entity_id: str, data: dict[str, Any]) -> Draft:
    kind, row = get_row(db, entity, entity_id)
    checked = kind.check(db, row, data)
    draft = draft_of(db, entity, entity_id)
    if draft is None:
        draft = Draft(entity=entity, entity_id=entity_id)
        db.add(draft)
    draft.data, draft.author_id, draft.author_name = checked, getattr(actor, 'id', None), getattr(actor, 'name', '')
    db.flush()
    return draft


def publish(db: Session, actor: Any, entity: str, entity_id: str, data: dict[str, Any] | None = None,
            *, action: str = 'publish') -> dict[str, Any]:
    """Apply the given payload or the saved draft now; the journal keeps both states."""
    kind, row = get_row(db, entity, entity_id, lock=True)
    draft = draft_of(db, entity, entity_id)
    if data is None:
        if draft is None:
            raise DomainError('NO_DRAFT', 'Нет черновика для публикации', 409)
        data = draft.data
    checked = kind.check(db, row, data)
    before = kind.payload(db, row)
    kind.write(db, row, checked)
    row.version = (row.version or 0) + 1
    db.flush()
    after = kind.payload(db, row)
    fields = changed_fields(before, after)
    record(db, actor, entity, row.id, action, f'{kind.label(row)}: {", ".join(fields) or "без изменений"}',
           before, after)
    if draft is not None:
        db.delete(draft)
    queue_revalidate(db, kind.tags(row))
    db.flush()
    return after


def publish_due(db: Session) -> int:
    """Scheduled drafts whose time has come (the worker, every minute)."""
    due = db.scalars(select(Draft).where(Draft.publish_at.is_not(None), Draft.publish_at <= utcnow())
                     .with_for_update(skip_locked=True)).all()
    done = 0
    for draft in due:
        try:
            with db.begin_nested():
                publish(db, None, draft.entity, draft.entity_id, action='publish_scheduled')
            done += 1
        except DomainError as exc:
            draft.publish_at = None
            record(db, None, draft.entity, draft.entity_id, 'publish_failed', exc.message[:300])
    return done


# ── preview links: the storefront shows a draft to whoever has the signed link (24 hours) ──

def _sign(body: str) -> str:
    return hmac.new(f'preview:{settings.secret_key}'.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]


def preview_token(entity: str, entity_id: str, seconds: int = PREVIEW_SECONDS) -> str:
    body = json.dumps([entity, entity_id, int(time.time()) + seconds], separators=(',', ':'))
    raw = base64.urlsafe_b64encode(body.encode()).decode().rstrip('=')
    return f'{raw}.{_sign(body)}'


def read_preview(token: str | None) -> tuple[str, str] | None:
    if not token or '.' not in token:
        return None
    raw, signature = token.rsplit('.', 1)
    try:
        body = base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)).decode()
        entity, entity_id, expires = json.loads(body)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(signature, _sign(body)) or int(expires) < time.time():
        return None
    return str(entity), str(entity_id)


def preview_data(db: Session, token: str | None, entity: str, entity_id: str) -> dict[str, Any] | None:
    """The draft of this very page when the link is valid for it; None — show the published version."""
    found = read_preview(token)
    if found != (entity, entity_id):
        return None
    draft = draft_of(db, entity, entity_id)
    return draft.data if draft else None


def products_count(db: Session, brand_id: str) -> int:
    from sqlalchemy import func

    return db.scalar(select(func.count()).select_from(Product).where(Product.brand_id == brand_id)) or 0
