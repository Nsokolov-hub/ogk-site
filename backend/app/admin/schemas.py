"""Shapes of the editable contents (ADM-02): the same as the storefront renders (web src/types/content.ts).

A draft is checked against them before it is saved, so a page the storefront cannot render never gets published.
Unknown keys are kept: the storefront may learn a field before the admin panel shows it.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.core.errors import DomainError


class Shape(BaseModel):
    model_config = ConfigDict(extra='allow')


class Seo(Shape):
    h1: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=500)
    updatedAt: str | None = None
    hasEn: bool | None = None


class Faq(Shape):
    q: str = Field(min_length=1)
    a: str = Field(min_length=1)


class Link(Shape):
    label: str = Field(min_length=1)
    href: str = Field(min_length=1)


class Image(Shape):
    src: str = Field(min_length=1)
    alt: str = ''
    width: int = Field(default=1200, ge=1)
    height: int = Field(default=800, ge=1)


class Cta(Shape):
    label: str
    href: str
    variant: Literal['primary', 'secondary'] = 'primary'
    icon: Literal['plus', 'dot', 'arrow'] | None = None


class IconText(Shape):
    id: str
    title: str
    text: str = ''
    icon: str = ''


class Accent(Shape):
    title: str
    accent: str = ''
    subtitle: str = ''


class HeroSlide(Shape):
    id: str
    title: str
    subtitle: str = ''
    ctas: list[Cta] = []
    imageMode: Literal['cover', 'object'] = 'cover'
    image: Image


class Home(Shape):
    hero: dict[str, Any]
    products: Accent
    brands: dict[str, Any]
    promo: dict[str, Any]
    quality: dict[str, Any]
    services: dict[str, Any]
    whyUs: dict[str, Any]
    capabilities: dict[str, Any]
    request: dict[str, Any]
    subscribe: dict[str, Any]

    @model_validator(mode='after')
    def slides_valid(self) -> 'Home':
        for slide in self.hero.get('slides') or []:
            HeroSlide.model_validate(slide)
        return self


class Step(Shape):
    title: str
    text: str = ''


class Table(Shape):
    caption: str = ''
    head: list[str]
    rows: list[list[str]]


class ServiceForm(Shape):
    title: str
    text: str = ''
    fields: list[Literal['route', 'temperature', 'cargo', 'date', 'goods', 'permit', 'regulator']] = []


class Service(Seo):
    slug: str
    name: str
    summary: str = ''
    intro: str = ''
    includes: list[str] = []
    steps: list[Step] = []
    needs: list[str] | None = None
    text: list[str] | None = None
    table: Table | None = None
    countries: list[str] | None = None
    faq: list[Faq] | None = None
    related: list[Link] = []
    form: ServiceForm
    image: Image | None = None


class SolutionGroup(Shape):
    title: str
    text: str = ''
    links: list[Link] = []
    scope: list[str] = []


class Solution(Seo):
    slug: str
    name: str
    summary: str = ''
    intro: str = ''
    tasks: list[str] = []
    groups: list[SolutionGroup] = []
    featured: list[str] = []
    services: list[str] = []
    articles: list[str] = []
    faq: list[Faq] | None = None


class Block(Shape):
    type: Literal['h2', 'p', 'ul', 'table', 'note']
    id: str | None = None
    text: str | None = None
    items: list[str] | None = None
    caption: str | None = None
    head: list[str] | None = None
    rows: list[list[str]] | None = None

    @model_validator(mode='after')
    def filled(self) -> 'Block':
        need = {'h2': ('id', 'text'), 'p': ('text',), 'note': ('text',), 'ul': ('items',), 'table': ('head', 'rows')}
        missing = [name for name in need[self.type] if not getattr(self, name)]
        if missing:
            raise ValueError(f'блок «{self.type}»: заполните {", ".join(missing)}')
        return self


class ArticleCta(Shape):
    title: str
    text: str = ''
    href: str
    label: str


class Article(Seo):
    slug: str
    lead: str = ''
    publishedAt: str
    authorSlug: str
    reviewed: bool = False
    readingMinutes: int = Field(default=5, ge=1)
    body: list[Block] = Field(min_length=1)
    links: list[Link] = []
    cta: ArticleCta


class Author(Shape):
    slug: str
    name: str
    role: str = ''
    bio: list[str] | None = None
    photo: Image | None = None


class Trust(Seo):
    slug: Literal['about', 'delivery', 'documents', 'contacts']
    intro: str = ''


class CategoryText(Seo):
    intro: str = ''
    seoText: list[str] | None = None
    delivery: list[str] | None = None
    faq: list[Faq] | None = None
    documents: list[dict[str, str]] | None = None
    related: list[Link] | None = None


class BrandText(Seo):
    summary: str = ''
    intro: str = ''
    text: list[str] = []
    groups: list[Link] = []
    faq: list[Faq] | None = None


class SubstanceText(Shape):
    description: list[str] | str | None = None
    synonyms: list[str] | None = None


PAGE_SHAPES: dict[str, type[Shape]] = {'home': Home, 'service': Service, 'solution': Solution, 'article': Article,
                                       'author': Author, 'trust': Trust}


def check(shape: type[Shape], value: Any, where: str) -> dict[str, Any]:
    """Validate one language version; a readable error names the field."""
    try:
        return shape.model_validate(value).model_dump(mode='json', exclude_none=True)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = '.'.join(str(p) for p in first['loc'])
        raise DomainError('CONTENT_INVALID', f'{where}: {field} — {first["msg"]}', 422, field) from None


def check_localized(shape: type[Shape], value: Any) -> dict[str, Any]:
    """{"ru": …, "en": …}: Russian is required, English only when translated (EN-05)."""
    if not isinstance(value, dict) or not isinstance(value.get('ru'), dict):
        raise DomainError('CONTENT_INVALID', 'Нужна русская версия', 422, 'ru')
    out = {'ru': check(shape, value['ru'], 'RU')}
    if isinstance(value.get('en'), dict) and value['en']:
        out['en'] = check(shape, value['en'], 'EN')
    return out
