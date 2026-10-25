"""Completeness of a product card (TZ 5.6) and whether search engines may index it (SEO-07)."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CardFacts:
    has_identity: bool
    has_image: bool
    description_length: int
    has_document: bool
    has_link: bool
    has_storage: bool


def facts(*, name: str | None, brand_id: str | None, catalog_number: str | None, primary_category: str | None,
          packagings: int, custom_packaging: bool, images: list[Any], texts: dict[str, Any], documents: int,
          substance_id: str | None, storage: str | None) -> CardFacts:
    description = ' '.join((texts.get('ru') or {}).get('description') or [])
    return CardFacts(
        has_identity=bool(name and brand_id and catalog_number and primary_category and (packagings or custom_packaging)),
        has_image=bool(images),
        description_length=len(description),
        has_document=documents > 0,
        has_link=bool(substance_id or primary_category),
        # Storage conditions do not apply to pharmacopoeias and subscriptions.
        has_storage=bool(storage) or (primary_category or '').startswith('pharmacopeias'),
    )


def score(card: CardFacts, weights: dict[str, int]) -> int:
    total = 0
    total += weights.get('identity', 0) if card.has_identity else 0
    total += weights.get('image', 0) if card.has_image else 0
    total += weights.get('description', 0) if card.description_length >= 300 else 0
    total += weights.get('document', 0) if card.has_document else 0
    total += weights.get('link', 0) if card.has_link else 0
    total += weights.get('storage', 0) if card.has_storage else 0
    return min(100, total)


def indexable(*, status: str, completeness: int, threshold: int, override: bool | None, controlled: bool,
              discontinued: bool = False) -> bool:
    """Index only published cards above the threshold; a manual override wins; controlled and discontinued never.

    A discontinued product keeps its page with analogues (URL-11) but leaves search engines' index.
    """
    if status != 'published' or controlled or discontinued:
        return False
    if override is not None:
        return override
    return completeness >= threshold
