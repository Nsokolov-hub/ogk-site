"""Pages of substances by CAS number (/cas/<cas>/): the nightly build from the products.

A CAS number gets a page when at least MIN_BRANDS brands sell at least MIN_OFFERS visible products with it: such a
page gathers what one card cannot — every manufacturer's grade and packaging of the substance. The page is named as
most brands name the substance, without grade and purity; the other names are its synonyms. Precursors (any product
with the CAS on the lists) and substances with their own written page (Substance) get none.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.controlled import DESCRIPTORS, QUANTITY, _descriptive, _untruncated, core_name
from app.catalog.models import Brand, CasPage, Category, Product, ProductCategory, Substance
from app.catalog.normalize import compact
from app.catalog.settings import get_setting, set_setting
from app.core.db import utcnow
from app.core.logs import event

logger = logging.getLogger(__name__)

MIN_OFFERS = 3
MIN_BRANDS = 2
SYNONYMS = 6
# The nightly build runs in these UTC hours (after the backups), once a day.
NIGHT = range(1, 4)
STOP = frozenset(('in', 'with', 'for', 'according', 'meets', 'contains', 'containing', 'suitable', 'plant', 'cell'))
# Brands' own grade names, on top of the grades the precursor check knows (app.catalog.controlled.DESCRIPTORS).
GRADES = DESCRIPTORS | frozenset('bioxtra bioultra sigmaultra certipur vetranal tracecert pharmpur '
                                  'bioperformance selectophore supelco fluka tested reo'.split())
# A catalogue or registry code is not a name: «UNII-U2Y5OFN795», «R320072».
CODE = re.compile(r'^unii-|^[a-z]{1,4}\d{3,}\b|(?:^|\s)[a-z]*\d{5,}', re.I)
# A big page names its synonyms only after names two brands share: one brand's odd name is noise there.
STRICT_OFFERS = 20


def tidy(name: str) -> str:
    """A name written in capitals in sentence case: «ACETAMINOPHEN» → «Acetaminophen», «(C11:0)» and roman numerals
    stay, a name that starts with a locant stays lower case («5-tert-butyl-o-anisidine»)."""
    if any(c.islower() for c in name):
        return name
    value = name.lower()
    value = re.sub(r'(?<![a-z])([a-z])(?=\d)', lambda m: m.group(1).upper(), value)
    value = re.sub(r'(?<=[\s(])([ivx]{1,4})(?=[\s)]|$)', lambda m: m.group(1).upper(), value)
    return value[:1].upper() + value[1:] if value[:1].isalpha() else value


def grade(token: str) -> bool:
    bare = token.strip(' ()[],;').casefold()
    return bare in GRADES or bool(QUANTITY.fullmatch(bare))


def display_name(name: str, *, keep_case: bool = False) -> str | None:
    """The substance a product name names: grade, purity and amounts taken off, the salt kept; in sentence case
    unless keep_case (the build compares the brands' own spellings first). None for a solution or a mix (another
    product than the substance itself)."""
    value = re.sub(r'[®™©*]', '', name)
    value = re.sub(r'(?<=[A-Za-z])\((?:R|TM|r|tm)\)', '', value)
    value = re.sub(r'[‐‑‒–—−]', '-', value).strip()
    low = value.casefold()
    if 'solution' in low or ' in ' in f' {low} ' or 'mixture' in low or 'kit' in low.split():
        return None
    if len(low) == len(value):
        value = value[:len(_untruncated(low))]
    value = re.split(r'\s-\s|\s/\s', value, maxsplit=1)[0]
    head, *rest = re.split(r'[,;]\s+', value)
    # Brackets after a comma only qualify the grade: «99.98% (REO)»; a lone «.» is the source's leftover.
    rest = [re.sub(r'\([^()]*\)', '', segment).casefold() for segment in rest if re.search(r'\w', segment)]
    if all(_descriptive(segment) for segment in rest):
        value = head
    tokens = value.split()
    for index, token in enumerate(tokens[1:], start=1):
        if token.casefold() in STOP:
            tokens = tokens[:index]
            break
    while len(tokens) > 1 and grade(tokens[-1]):
        tokens.pop()
    value = ' '.join(tokens).strip(' ,;.')
    # A name the source cut inside the chemical name («…CYCLIC MONOPHOSPHATE&») is not whole.
    if not re.search(r'[A-Za-z]{2}', value) or CODE.search(value) or value.endswith('&'):
        return None
    return value if keep_case else tidy(value)


def stand_in(name: str, brand: str, number_norm: str) -> bool:
    """The importer's stand-in for a card without a Latin name: «<brand> <catalog number>»."""
    if not name.casefold().startswith(brand.casefold()):
        return False
    rest = compact(name[len(brand):])
    return not rest or rest == number_norm or number_norm.startswith(rest) or rest.startswith(number_norm)


@dataclass
class Group:
    """The rows of one CAS number while it is read."""
    names: list[tuple[str, str]] = field(default_factory=list)  # (display name, brand)
    brands: Counter[str] = field(default_factory=Counter)
    sections: Counter[str] = field(default_factory=Counter)
    formulas: Counter[str] = field(default_factory=Counter)
    weights: Counter[str] = field(default_factory=Counter)
    offers: int = 0
    listed: bool = False


def choose(names: list[tuple[str, str]], *, strict: bool = False) -> tuple[str, list[str]] | None:
    """The name most brands use and the other names as synonyms, one per substance core name; strict — only names
    two brands share become synonyms."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for name, brand in names:
        key = core_name(name) or name.casefold()
        groups.setdefault(key, []).append((name, brand))
    if not groups:
        return None

    def weight(rows: list[tuple[str, str]]) -> tuple[int, int, bool, int]:
        # More brands, more cards, a name some brand writes in normal case, a shorter name.
        return (len({b for _, b in rows}), len(rows), any(not n.isupper() for n, _ in rows),
                -min(len(n) for n, _ in rows))

    def representative(rows: list[tuple[str, str]]) -> str:
        spelled = Counter(n for n, _ in rows)
        return tidy(min(spelled, key=lambda n: (n.isupper(), -spelled[n], len(n), n)))

    ordered = sorted(groups.values(), key=weight, reverse=True)
    name = representative(ordered[0])
    synonyms: list[str] = []
    for rows in ordered[1:]:
        if strict and len({b for _, b in rows}) < 2:
            continue
        other = representative(rows)
        if other.casefold() != name.casefold() and other.casefold() not in {s.casefold() for s in synonyms}:
            synonyms.append(other)
        if len(synonyms) == SYNONYMS:
            break
    return name, synonyms


def page_of(cas: str, group: Group) -> dict[str, object] | None:
    if group.listed or group.offers < MIN_OFFERS or len(group.brands) < MIN_BRANDS:
        return None
    chosen = choose(group.names, strict=group.offers >= STRICT_OFFERS)
    if chosen is None:
        return None
    name, synonyms = chosen
    return {
        'cas': cas, 'name': name[:300], 'synonyms': synonyms, 'offers': group.offers,
        'formula': group.formulas.most_common(1)[0][0] if group.formulas else None,
        'molecular_weight': group.weights.most_common(1)[0][0] if group.weights else None,
        'brands': [b for b, _ in group.brands.most_common()],
        'sections': [s for s, _ in group.sections.most_common()],
    }


def pages(db: Session) -> dict[str, dict[str, object]]:
    """Every page the catalog gives now, read in one pass over the products with a CAS number."""
    hidden = get_setting(db, 'hidden_categories')
    own = {cas for cas in db.scalars(select(Substance.cas).where(Substance.cas.is_not(None)))}
    statement = (select(Product.cas, Product.name_en, Product.catalog_number_norm, Product.status, Product.controlled,
                        Product.formula, Product.molecular_weight, Brand.name, Category.path)
                 .join(Brand, Brand.id == Product.brand_id)
                 .outerjoin(ProductCategory, and_(ProductCategory.product_id == Product.id,
                                                  ProductCategory.is_primary.is_(True)))
                 .outerjoin(Category, Category.id == ProductCategory.category_id)
                 .where(Product.cas.is_not(None))
                 .order_by(Product.cas)
                 .execution_options(yield_per=5000))
    out: dict[str, dict[str, object]] = {}
    current, group = None, Group()
    for cas, name, number, status, controlled, formula, weight, brand, path in db.execute(statement):
        if cas != current:
            if current is not None and current not in own and (page := page_of(current, group)):
                out[current] = page
            current, group = cas, Group()
        if controlled:
            group.listed = True
            continue
        if status != 'published' or (path and any(path == h or path.startswith(f'{h}/') for h in hidden)):
            continue
        group.offers += 1
        group.brands[brand] += 1
        if path:
            group.sections[path.split('/')[0]] += 1
        if formula:
            group.formulas[formula] += 1
        if weight:
            group.weights[weight] += 1
        if name and not stand_in(name, brand, number) and (display := display_name(name, keep_case=True)):
            group.names.append((display, brand))
    if current is not None and current not in own and (page := page_of(current, group)):
        out[current] = page
    return out


def build(session_factory: sessionmaker[Session]) -> dict[str, int]:
    """Write the pages: new ones added, changed ones updated (with a new lastmod), gone ones deleted."""
    with session_factory() as db:
        fresh = pages(db)
    counts = {'pages': len(fresh), 'added': 0, 'changed': 0, 'removed': 0}
    fields = ('name', 'synonyms', 'formula', 'molecular_weight', 'offers', 'brands', 'sections')
    with session_factory.begin() as db:
        now = utcnow()
        existing = {row.cas: row for row in db.scalars(select(CasPage))}
        for cas, data in fresh.items():
            row = existing.get(cas)
            if row is None:
                db.add(CasPage(**data, updated_at=now))
                counts['added'] += 1
            elif any(getattr(row, f) != data[f] for f in fields):
                for f in fields:
                    setattr(row, f, data[f])
                row.updated_at = now
                counts['changed'] += 1
        gone = [cas for cas in existing if cas not in fresh]
        for start in range(0, len(gone), 1000):
            db.execute(delete(CasPage).where(CasPage.cas.in_(gone[start:start + 1000])))
        counts['removed'] = len(gone)
        set_setting(db, 'cas_pages_built_at', now.isoformat())
    event(logger, 'cas_pages_built', **counts)
    return counts


def due(db: Session, now: datetime | None = None) -> bool:
    """Once a night, in the hours after the backups."""
    now = now or utcnow()
    if now.hour not in NIGHT:
        return False
    last = get_setting(db, 'cas_pages_built_at')
    return not last or now - datetime.fromisoformat(last) >= timedelta(hours=20)
