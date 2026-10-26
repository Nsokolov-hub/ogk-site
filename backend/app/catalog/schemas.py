"""Answers of the public catalog API in the storefront's shapes (src/types/catalog.ts); camelCase on the wire.

The storefront generates its TypeScript types from the OpenAPI schema of these models (openapi-typescript).
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CardType = Literal['standard', 'equipment', 'other']
Match = Literal['catalogNumber', 'cas', 'formula', 'name', 'brand']


class Out(BaseModel):
    model_config = ConfigDict(extra='ignore')


class BrandRef(Out):
    slug: str
    name: str
    logo: str | None = None


class PackagingOut(Out):
    id: str
    label: str
    catalogNumber: str | None = None


class ImageOut(Out):
    src: str
    alt: str
    kind: Literal['photo', 'structure']


class SubstanceLink(Out):
    slug: str
    role: Literal['api', 'impurity', 'metabolite', 'labeled']


class ProductPreview(Out):
    id: str
    slug: str
    cardType: CardType
    name: str
    brand: BrandRef
    catalogNumber: str
    cas: str | None = None
    categorySlug: str
    packagings: list[PackagingOut]
    customPackaging: bool
    image: ImageOut | None = None
    discontinued: bool = False
    substance: SubstanceLink | None = None
    attributes: dict[str, list[str]] = Field(default_factory=dict)
    popularity: int = 0


class FacetValue(Out):
    value: str
    label: str
    count: int
    selected: bool


class Facet(Out):
    key: str
    values: list[FacetValue]


class CatalogListing(Out):
    items: list[ProductPreview]
    total: int
    page: int
    pageSize: int
    pageCount: int
    facets: list[Facet]


class CountOut(Out):
    count: int


class CategoryBrand(BrandRef):
    count: int


class CategoryNode(Out):
    slug: str
    path: str
    nameRu: str
    nameEn: str | None = None
    shortRu: str | None = None
    shortEn: str | None = None
    # A translated category gets hreflang and the English Sitemap (EN-05).
    hasEn: bool = False
    updatedAt: str = ''
    children: list['CategoryNode'] = Field(default_factory=list)


class CategoryOut(Out):
    path: str
    nameRu: str
    nameEn: str | None = None
    cardType: CardType
    facets: list[str]
    isIndexed: bool
    # CategoryContent of the storefront, per language; «en» is absent until translated (EN-05).
    content: dict[str, Any]
    updatedAt: str


class SuggestItem(Out):
    id: str
    slug: str
    name: str
    brand: str
    catalogNumber: str
    cas: str | None = None
    formula: str | None = None
    cardType: CardType
    match: Match


class SuggestSubstance(Out):
    slug: str
    name: str
    nameEn: str


class LinkOut(Out):
    name: str
    href: str


class SuggestBrand(Out):
    slug: str
    name: str


class SuggestResult(Out):
    query: str
    corrected: str | None = None
    items: list[SuggestItem]
    total: int
    substances: list[SuggestSubstance]
    categories: list[LinkOut]
    brands: list[SuggestBrand]


class SearchFacets(Out):
    brand: list[FacetValue]
    category: list[FacetValue]


class SearchPageResult(Out):
    query: str
    corrected: str | None = None
    items: list[ProductPreview]
    total: int
    page: int
    pageCount: int
    facets: SearchFacets


class BatchCandidate(Out):
    id: str
    slug: str
    name: str
    brand: BrandRef
    catalogNumber: str
    cas: str | None = None
    categorySlug: str
    packagings: list[PackagingOut]
    customPackaging: bool
    cardType: CardType


class BatchLine(Out):
    line: str
    query: str
    quantity: int
    status: Literal['exact', 'multiple', 'none']
    candidates: list[BatchCandidate]


class BatchIn(BaseModel):
    lines: list[str] = Field(max_length=1000)
    lang: Literal['ru', 'en'] = 'ru'


class BatchOut(Out):
    lines: list[BatchLine]
    # Lines beyond the limit of 200 (SRCH-09) are not matched.
    truncated: bool = False


class DocumentOut(Out):
    type: str
    lang: str
    titleRu: str | None = None
    titleEn: str | None = None
    href: str | None = None


class ProductDetailOut(ProductPreview):
    nameRu: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    altCas: list[str] = Field(default_factory=list)
    formula: str | None = None
    molecularWeight: str | None = None
    iupacName: str | None = None
    purity: str | None = None
    storage: str | None = None
    shipping: str | None = None
    dangerousGoods: bool | None = None
    # {"ru": {"description": [...], "specs": [...], "faq": [...], "monograph": ...}, "en": {...}}
    texts: dict[str, Any]
    uniqueDescription: bool
    documents: list[DocumentOut]
    completeness: int
    indexable: bool
    availability: str
    # Title and Description written by hand in the admin panel (SEO-02): {"ru": {"title", "description"}, "en": …}.
    seo: dict[str, Any] = Field(default_factory=dict)
    updatedAt: str


class BreadcrumbCategory(Out):
    slug: str
    name: str
    href: str


class SubstanceOut(Out):
    slug: str
    nameRu: str
    nameEn: str
    cas: str | None = None
    formula: str | None = None
    molecularWeight: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    # {"ru": {"description": [...]}, "en": {"description": [...], "synonyms": [...]}}
    content: dict[str, Any] = Field(default_factory=dict)


class ProductPage(Out):
    # Set instead of the page when the address changed (URL-03): the storefront answers 301.
    moved: str | None = None
    product: ProductDetailOut | None = None
    categories: list[BreadcrumbCategory] = Field(default_factory=list)
    substance: SubstanceOut | None = None
    sameSubstance: list[ProductPreview] = Field(default_factory=list)
    sameSubstanceTotal: int = 0
    analogues: list[ProductPreview] = Field(default_factory=list)
    accessories: list[ProductPreview] = Field(default_factory=list)


class SubstanceListItem(SubstanceOut):
    count: int


class SubstancePage(Out):
    moved: str | None = None
    substance: SubstanceOut | None = None
    items: list[ProductPreview] = Field(default_factory=list)


class BrandOut(Out):
    slug: str
    name: str
    logo: str | None = None
    country: str | None = None
    customPackaging: bool
    wave: int | None = None
    # BrandContent of the storefront, per language.
    content: dict[str, Any]
    count: int
    updatedAt: str


class CountedPath(Out):
    slug: str
    count: int


class BrandPage(Out):
    moved: str | None = None
    brand: BrandOut | None = None
    products: list[ProductPreview] = Field(default_factory=list)
    categories: list[CountedPath] = Field(default_factory=list)


class ProductsPage(Out):
    items: list[ProductPreview]
    total: int


class SitemapEntry(Out):
    slug: str
    updatedAt: str
    hasEn: bool


class SitemapPage(Out):
    items: list[SitemapEntry]
    total: int
    page: int
    pageCount: int


class FeedItem(Out):
    id: str
    slug: str
    name: str
    brand: str
    catalogNumber: str
    cas: str | None = None
    categorySlug: str
    image: str | None = None
    description: str | None = None
    packagings: list[str] = Field(default_factory=list)
    customPackaging: bool = False


class FeedOut(Out):
    items: list[FeedItem]
    categories: list[CategoryNode]


class CartIn(BaseModel):
    items: list[dict[str, Any]] = Field(max_length=200)


class CartOut(Out):
    items: list[dict[str, Any]]
    updatedAt: str | None = None


CategoryNode.model_rebuild()
