"""Normalization rules shared by imports, search and the admin panel (TZ 6 SRCH-03, 9.5 IMP-03, 4.3 URL-05).

- Catalog numbers and CAS are compared without case, spaces, dashes, dots and slashes: «1.00030» = «100030».
- CAS numbers are checked by their check digit; «28721075» becomes 28721-07-5.
- Packagings «100 мг | 1 г», «4x2.5 l», «25.0 g» become rows with an amount, a unit and RU/EN labels.
- Gross formulas are compared in Hill order: «C15 H12 N2 O2» and «c15h12n2o2» give C15H12N2O2.
"""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_COMPACT = re.compile(r'[\s.\-–—/_\\,]+')


def compact(value: str | None) -> str:
    """Catalog numbers, P/N and CAS for comparison: lower case without separators."""
    return _COMPACT.sub('', (value or '').casefold().replace('µ', 'u'))


def clean_spaces(value: str | None) -> str:
    return ' '.join((value or '').split())


def normalize_query(value: str | None) -> str:
    return clean_spaces(value).casefold()


# ── CAS ──

_CAS_EMPTY = {'', '-', '—', 'na', 'n/a', 'нет', 'none', 'null', '0'}


def cas_check_ok(cas: str) -> bool:
    match = re.fullmatch(r'(\d{2,7})-(\d{2})-(\d)', cas)
    if not match:
        return False
    digits = (match.group(1) + match.group(2))[::-1]
    return sum((i + 1) * int(d) for i, d in enumerate(digits)) % 10 == int(match.group(3))


def parse_cas(raw: str | None) -> tuple[str | None, bool]:
    """(CAS in the canonical form or None, whether the source had a value that is not a valid CAS)."""
    value = clean_spaces(raw).casefold()
    if value in _CAS_EMPTY:
        return None, False
    digits = re.sub(r'[\s\-–—.]', '', value)
    if not digits.isdigit() or not 5 <= len(digits) <= 10:
        return None, True
    cas = f'{digits[:-3]}-{digits[-3:-1]}-{digits[-1]}'
    return (cas, False) if cas_check_ok(cas) else (None, True)


def cas_or_none(raw: str | None) -> str | None:
    return parse_cas(raw)[0]


# ── gross formula (SRCH-10) ──

_TWO_LETTER = {'Cl', 'Br', 'Na', 'Ca', 'Mg', 'Li', 'Si', 'Se', 'Zn', 'Fe', 'Al', 'Pt', 'Ag', 'Au', 'Mn', 'Cu',
               'Co', 'Ni', 'Sn', 'Hg', 'Pb', 'Ba', 'Sr', 'Bi', 'Gd', 'Tc'}
_SUBSCRIPTS = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')


def hill_key(value: str | None) -> str | None:
    """«C15H12N2O2», «c15h12n2o2», «C₁₅H₁₂N₂O₂» → the formula in Hill order; not a formula → None."""
    raw = re.sub(r'\s+', '', (value or '').translate(_SUBSCRIPTS))
    if not raw or not re.fullmatch(r'[A-Za-z0-9]+', raw) or not re.search(r'\d', raw) or not re.search('[cC]', raw):
        return None
    mixed_case = bool(re.search('[a-z]', raw)) and bool(re.search('[A-Z]', raw))
    counts: dict[str, int] = {}
    i = 0
    while i < len(raw):
        up = raw[i].upper()
        if not up.isalpha():
            return None
        element = up
        nxt = raw[i + 1] if i + 1 < len(raw) else ''
        if nxt.isalpha():
            pair = up + nxt.lower()
            # Written with case, a lower-case letter always continues the symbol; without case only known pairs.
            if (nxt.islower() if mixed_case else pair in _TWO_LETTER):
                element = pair
        i += len(element)
        number = ''
        while i < len(raw) and raw[i].isdigit():
            number += raw[i]
            i += 1
        counts[element] = counts.get(element, 0) + (int(number) if number else 1)
    if 'C' not in counts:
        return None
    order = ['C', 'H', *sorted(e for e in counts if e not in ('C', 'H'))]
    return ''.join(f'{e}{"" if counts[e] == 1 else counts[e]}' for e in order if e in counts)


# ── keyboard layout (SRCH-05) ──

_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`"
_RU = 'йцукенгшщзхъфывапролджэячсмитьбюё'


def switch_layout(query: str) -> str:
    """«jrcrfh,fptgby» → «окскарбазепин» and back."""
    lowered = query.casefold()
    latin = bool(re.search('[a-z]', lowered)) and not re.search('[а-яё]', lowered)
    source, target = (_EN, _RU) if latin else (_RU, _EN)
    return ''.join(target[source.index(ch)] if ch in source else ch for ch in lowered)


def looks_like_number(query: str) -> bool:
    """A catalog number, P/N or CAS: every word has a digit («Y0001897», «58 08 2», «1.00030»), or the number is
    typed with spaces and is mostly digits («Y 000 1897»)."""
    words = normalize_query(query).split()
    packed = compact(query)
    if not words or len(packed) < 3:
        return False
    digits = sum(ch.isdigit() for ch in packed)
    return all(re.search(r'\d', w) for w in words) or (len(packed) >= 5 and digits / len(packed) >= 0.6)


# ── names, slugs ──

_TRANSLIT = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                     ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's',
                      't', 'u', 'f', 'kh', 'ts', 'ch', 'sh', 'shch', '', 'y', '', 'e', 'yu', 'ya'], strict=True))


def ascii_fold(value: str) -> str:
    lowered = value.casefold().replace('µ', 'u').replace('&', ' and ')
    lowered = ''.join(_TRANSLIT.get(ch, ch) for ch in lowered)
    return unicodedata.normalize('NFKD', lowered).encode('ascii', 'ignore').decode()


def slugify(value: str, limit: int = 80) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_fold(value)).strip('-')
    return slug[:limit].rstrip('-')


def product_slug(brand_slug: str, catalog_number: str, name: str) -> str:
    """URL-05: brand + catalog number + English name, up to 80 characters."""
    return slugify(f'{brand_slug} {catalog_number} {name}')


# Words that do not tell manufacturers apart (as in the CRM registry).
_LEGAL_WORDS = {'pvt', 'ltd', 'limited', 'private', 'inc', 'llc', 'gmbh', 'co', 'corp', 'corporation', 'company',
                'sa', 'ag', 'srl', 'spa', 'bv', 'oy', 'kg', 'ooo', 'ооо', 'ао', 'зао', 'пао', 'оао'}


def brand_key(value: str | None) -> str:
    """A brand spelling for lookup: «Riedel-de Haën» = «riedel de haen», «Merck KGaA» ≠ «Merck»."""
    folded = unicodedata.normalize('NFKD', (value or '').casefold()).encode('ascii', 'ignore').decode() \
        if not re.search('[а-яё]', (value or '').casefold()) else (value or '').casefold()
    words = re.findall(r'[0-9a-zа-яё]+', folded.replace('&', ' and '))
    return ''.join(word for word in words if word not in _LEGAL_WORDS)


# ── packagings ──

@dataclass(frozen=True)
class Pack:
    key: str
    label_ru: str
    label_en: str
    amount: Decimal | None = None
    unit: str | None = None


# unit → (RU label, EN label); keys are the canonical units the storefront and the CRM understand.
UNITS: dict[str, tuple[str, str]] = {
    'ug': ('мкг', 'µg'), 'mg': ('мг', 'mg'), 'g': ('г', 'g'), 'kg': ('кг', 'kg'),
    'ul': ('мкл', 'µl'), 'ml': ('мл', 'ml'), 'l': ('л', 'l'),
    'umol': ('мкмоль', 'µmol'), 'mmol': ('ммоль', 'mmol'),
    'pcs': ('шт.', 'pcs'), 'test': ('тест.', 'tests'), 'kit': ('набор', 'kit'), 'pack': ('упак.', 'pack'),
    'vial': ('фл.', 'vial'), 'mm': ('мм', 'mm'), 'cm': ('см', 'cm'), 'm': ('м', 'm'), 'iu': ('ЕД', 'IU'),
}
_UNIT_WORDS = {
    'ug': ('мкг', 'ug', 'µg', 'μg', 'mcg', '?g'),
    'mg': ('мг', 'mg'),
    'g': ('г', 'гр', 'g', 'gr', 'gm'),
    'kg': ('кг', 'kg'),
    'ul': ('мкл', 'ul', 'µl', 'μl', '?l'),
    'ml': ('мл', 'ml'),
    'l': ('л', 'l', 'lt', 'ltr'),
    'umol': ('мкмоль', 'umol', 'µmol'),
    'mmol': ('ммоль', 'mmol'),
    'pcs': ('шт', 'шт.', 'pc', 'pcs', 'each', 'ea', 'штук', 'штука', 'штуки'),
    'test': ('тест', 'тест.', 'тестов', 't', 'tst', 'test', 'tests', 'определений', 'реакций', 'rxn'),
    'kit': ('набор', 'наборов', 'kit', 'компл', 'компл.', 'комплект'),
    'pack': ('упак', 'упак.', 'упаковка', 'уп', 'уп.', 'pak', 'pk', 'pack'),
    'vial': ('vl', 'флакон', 'флакона', 'флаконов', 'фл', 'фл.', 'амп', 'ампула', 'ампулы', 'vial', 'vials'),
    'mm': ('мм', 'mm'), 'cm': ('см', 'cm'), 'm': ('м', 'm'),
    'iu': ('ед', 'iu', 'ме'),
}
_UNIT_OF = {word: unit for unit, words in _UNIT_WORDS.items() for word in words}
_NUMBER = r'\d+(?:[.,]\d+)?'
_PACK = re.compile(rf'^(?:(?P<count>\d+)\s*[xх×*]\s*)?(?P<amount>{_NUMBER})?\s*(?P<unit>[^\d\s][^\d]*)?$', re.I)


def _decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(',', '.'))
    except InvalidOperation:
        return None


def _number(value: Decimal, comma: bool) -> str:
    text = format(value.normalize(), 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text.replace('.', ',') if comma else text


def parse_pack(raw: str | None) -> Pack | None:
    """One packaging: «250 мг», «0,1 мл», «25.0 g», «1г», «4x2.5 l», «96 t», «шт»; empty → None."""
    value = clean_spaces(raw)
    if not value:
        return None
    match = _PACK.match(value)
    unit_word = (match.group('unit') or '').strip().casefold().rstrip('.') if match else ''
    unit = _UNIT_OF.get(unit_word) or _UNIT_OF.get(unit_word + '.') if match else None
    amount = _decimal(match.group('amount')) if match and match.group('amount') else None
    if match and unit and (amount is not None or not match.group('count')):
        amount = amount if amount is not None else Decimal(1)
        count = int(match.group('count')) if match.group('count') else None
        ru, en = UNITS[unit]
        label_ru = f'{_number(amount, True)} {ru}'
        label_en = f'{_number(amount, False)} {en}'
        key = f'{_number(amount, False)}-{unit}'
        if count and count > 1:
            label_ru, label_en, key = f'{count} × {label_ru}', f'{count} × {label_en}', f'{count}x{key}'
        return Pack(key=slugify(key, 60) or 'pack', label_ru=label_ru, label_en=label_en, amount=amount, unit=unit)
    # Anything else stays as the source wrote it: «59 пластин 20мм ?», «10 колб по 5 мл».
    return Pack(key=slugify(value, 60) or 'pack', label_ru=value, label_en=value)


def parse_packs(raw: str | None) -> list[Pack]:
    """«100 мг | 1 г» → two packagings (TZ 5.1); duplicates are dropped, the order is kept."""
    seen: set[str] = set()
    packs: list[Pack] = []
    for part in re.split(r'\s*[|;]\s*', raw or ''):
        pack = parse_pack(part)
        if pack and pack.key not in seen:
            seen.add(pack.key)
            packs.append(pack)
    return packs


# ── catalog numbers of packagings: «CS-T-60514-5MG», «AB477228-1мг», «SIN-10039-MM09-A-25Tests» ──

_SUFFIX_UNITS = r'mg|g|gm|gr|kg|ug|µg|mcg|ml|l|ul|µl|мг|г|кг|мкг|мл|л|мкл|tests?|tst|t|pcs|pc|ea|vl|kit|pk|mmol|umol'
_PACK_SUFFIX = re.compile(rf'^(?P<base>.+?)[-_/.](?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>{_SUFFIX_UNITS})$', re.I)
_NUMBER_SUFFIX = re.compile(r'^(?P<base>.+?)[-_/](?P<amount>\d+(?:[.,]\d+)?)$')


def split_pack_suffix(catalog_number: str, pack: Pack | None) -> tuple[str, Pack | None]:
    """(catalog number of the product, packaging) when the number ends with its packaging.

    «CS-T-60514-5MG» → «CS-T-60514» with 5 mg; «AG005JV6-100» with «100 мг» → «AG005JV6». A number that does not
    end with a packaging stays as it is. The full number stays on the packaging and is still searchable.
    """
    value = clean_spaces(catalog_number)
    match = _PACK_SUFFIX.match(value)
    if match and len(compact(match.group('base'))) >= 3:
        suffix_pack = parse_pack(f'{match.group("amount")} {match.group("unit")}')
        if suffix_pack and suffix_pack.unit and (pack is None or pack.key == suffix_pack.key or pack.unit is None):
            return match.group('base'), pack if pack and pack.unit else suffix_pack
    match = _NUMBER_SUFFIX.match(value)
    if match and pack and pack.amount is not None and len(compact(match.group('base'))) >= 3:
        amount = _decimal(match.group('amount'))
        if amount is not None and amount == pack.amount:
            return match.group('base'), pack
    return value, pack
