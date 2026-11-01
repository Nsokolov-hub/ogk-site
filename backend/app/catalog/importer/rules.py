"""Category of an imported row (IMP-03): by brand, refined by words of the name; the rest waits for a person.

Rows the rules do not place get no category: they are on the site and in search at once, and the admin panel
shows them in the queue «без категории». The rules are a starting point and are meant to be edited.
"""

import re

from app.catalog.normalize import brand_key

RS = 'reference-standards'
CH = 'chromatography'
BIO = 'biochemistry'

# Brand → category path; «chromatography» and «Merck» are refined by name below.
BRAND_CATEGORY: dict[str, str] = {
    **{brand_key(b): f'{RS}/usp' for b in ('USP', 'United States Pharmacopeia')},
    **{brand_key(b): f'{RS}/edqm' for b in ('EDQM', 'European Pharmacopoeia')},
    **{brand_key(b): f'{RS}/british-pharmacopoeia' for b in ('British Pharmacopoeia', 'BP')},
    **{brand_key(b): f'{RS}/lgc' for b in ('LGC', 'LGC Dr. Ehrenstorfer', 'LGC Standards', 'Dr. Ehrenstorfer')},
    **{brand_key(b): f'{RS}/impurity-standards' for b in (
        'Clearsynth', 'TLC Pharmaceutical Standards', 'Pharmaffiliates', 'Molcan', 'SynZeal', 'Aozeal', 'TRC',
        'Toronto Research Chemicals', 'BioOrganics')},
    **{brand_key(b): 'reagents' for b in (
        'Sigma-Aldrich', 'ABCR', 'Acros Organics', 'Alfa Aesar', 'Thermo Fisher Scientific', 'Honeywell',
        'Riedel-de Haën (Honeywell)', 'Central Drug House', 'Sisco Research Laboratories', 'neoFroxx',
        'ITW Reagents (PanReac AppliChem)', 'Avantor', 'Scharlab', 'Angene International', 'Macklin',
        'HiMedia Laboratories', 'Larodan', 'TOKU-e', 'Duchefa Biochemie', 'Nacalai', 'Hopax', 'Quanta BioDesign',
        'AkzoNobel', 'Oleon', 'TCI', 'Chemtrade Chemicals US', 'Macco Organiques', 'Guangzhou Jiahua Chemical',
        'SEPPIC', 'ABITEC', 'Ueno Fine Chemical Industrial', 'ICL', 'Hispanagar', 'Merck')},
    # Antibodies, recombinant proteins, peptides, enzymes, immunoassay and molecular biology kits.
    **{brand_key(b): BIO for b in (
        'Sino Biological', 'Novus Biologicals', 'ABclonal', 'R&D Systems', 'Enzo Life Sciences', 'Immundiagnostik',
        'Agdia', 'New England Biolabs', 'Servicebio', 'BioLegend', 'Santa Cruz Biotechnology', 'Abcam', 'Qiagen',
        'Jackson ImmunoResearch', 'Vector Laboratories', 'Bio-Rad', 'Cytiva', 'ДНК-Технология')},
    **{brand_key(b): CH for b in (
        'Waters', 'Agilent Technologies', 'Agilent', 'Phenomenex', 'GL Sciences', 'Imtakt', 'Macherey-Nagel', 'Shodex',
        'Welch Materials', 'Welch', 'Hawach Scientific', 'Bischoff', 'MZ-Analysentechnik', 'Nomura', 'Sciencix',
        'Regis Technologies', 'ALWSCI Technologies', 'Biocomma', 'Jet Bio-Filtration', 'Membrane Solutions',
        'La-Pha-Pack', 'LC Tech', 'IDEX', 'HiChrome', 'Владипор', 'Pickering Laboratories')},
    # Business remark of 31 October 2026: equipment and glassware are not sold; their brands get no category and
    # their rows are skipped by the list of seed/excluded-assortment.csv.gz.
    **{brand_key(b): 'biological-standards' for b in ('ATCC',)},
}

# A reagent brand's or an unknown brand's antibodies, proteins and immunoassay kits go to biochemistry.
_BIO_WORDS = re.compile(r'antibod|антител|recombinant|рекомбинант|\bproteins?\b|\bбел(ок|ка|ки)\b|elisa|\bифа\b|'
                        r'monoclonal|polyclonal|моноклон|поликлон|isotype|\bsirna\b|plasmid|плазмид|\bcdna\b|'
                        r'\bpeptides?\b|пептид', re.I)
_MERCK_STANDARD = re.compile(r'\b(crs|crm|reference|standard|certified|pharmaceutical secondary|phr\d)', re.I)
_GUARD = re.compile(r'guard|precolumn|pre-column|предколон|sentry|cartridge holder|vanguard', re.I)
_COLUMN = re.compile(r'\bcolumns?\b|колонк', re.I)
_FILTER = re.compile(r'filter|фильтр|membrane|мембран', re.I)
_FITTING = re.compile(r'fitting|ferrule|фитинг|\bnut\b|tubing|union|капилляр', re.I)


def category_for(brand: str, name: str) -> str | None:
    path = BRAND_CATEGORY.get(brand_key(brand))
    if path in (None, 'reagents') and _BIO_WORDS.search(name):
        return BIO
    if path is None:
        return None
    if brand_key(brand) == brand_key('Merck'):
        return f'{RS}/merck' if _MERCK_STANDARD.search(name) else 'reagents'
    if path == CH:
        if _GUARD.search(name):
            return f'{CH}/precolumns'
        if _COLUMN.search(name):
            return f'{CH}/hplc-columns'
        if _FILTER.search(name):
            return f'{CH}/filters'
        if _FITTING.search(name):
            return f'{CH}/fittings'
    return path


# «Каталог продукции по категориям» (31.10.2026): direction / category / subgroup → the site's category. The longest
# match wins; SKIP — the business does not sell it (business remarks of 31.10.2026: equipment, glassware except
# filters; «Прочие товары» are mostly the same kind of goods and wait for a person to sort them).
SKIP = 'skip'
_CHEM, _STD, _CHROM = 'Химические реактивы', 'Стандарты и эталонные материалы', 'Хроматография'
_COLUMNS, _CHROM_SUPPLIES = 'Колонки хроматографические', 'Расходники и принадлежности для хроматографии'
FILE_CATEGORIES: dict[tuple[str, ...], str] = {
    (_CHEM, 'Неорганические соединения, кислоты и соли'): 'reagents/inorganic',
    (_CHEM, 'Растворители'): 'reagents/solvents',
    (_CHEM, 'Органические соединения и строительные блоки'): 'reagents/organic',
    (_CHEM, 'Металлоорганические соединения, катализаторы и лиганды'): 'reagents/organometallics',
    (_CHEM, 'Аминокислоты и реагенты пептидного синтеза'): 'reagents/amino-acids',
    (_CHEM, 'Биохимические реагенты'): 'reagents/biochemical',
    (_CHEM, 'Биоактивные соединения, ингибиторы и природные вещества'): 'reagents/bioactive',
    (_CHEM, 'Антибиотики и противомикробные вещества'): 'reagents/antibiotics',
    (_CHEM, 'Красители, индикаторы, зонды и субстраты'): 'reagents/dyes',
    (_CHEM, 'Полимеры, ПЭГ-линкеры, смолы, микро- и наноматериалы'): 'reagents/polymers',
    (_CHEM, 'Металлы, сплавы и конструкционные материалы'): 'reagents/metals',
    (_CHEM,): 'reagents',
    (_STD, 'Фармакопейные стандарты и примеси (EP/USP/BP)'): f'{RS}/impurity-standards',
    (_STD, 'Фармстандарты, метаболиты и субстанции'): f'{RS}/impurity-standards',
    (_STD, 'Аналитические стандарты и CRM'): f'{RS}/analytical',
    (_STD, 'Изотопно-меченые соединения'): f'{RS}/isotope-labelled',
    (_STD, 'Буферы, титранты и стандартные растворы'): f'{RS}/solutions',
    (_STD,): RS,
    (_CHROM, _COLUMNS, 'Колонки для ВЭЖХ/УВЭЖХ'): f'{CH}/hplc-columns',
    (_CHROM, _COLUMNS, 'Колонки эксклюзионные (SEC/GPC)'): f'{CH}/hplc-columns',
    (_CHROM, _COLUMNS, 'Колонки для ГХ'): f'{CH}/gc-columns',
    (_CHROM, _COLUMNS, 'Предколонки и защитные картриджи'): f'{CH}/precolumns',
    (_CHROM, _CHROM_SUPPLIES, 'Виалы, септы и крышки'): f'{CH}/vials',
    (_CHROM, _CHROM_SUPPLIES, 'Сорбенты и ТФЭ (SPE)'): f'{CH}/spe',
    (_CHROM, _CHROM_SUPPLIES, 'ТСХ-пластины'): f'{CH}/tlc',
    (_CHROM, _CHROM_SUPPLIES, 'Фитинги, капилляры, запчасти'): f'{CH}/fittings',
    (_CHROM,): CH,
    ('Антитела и иммуноанализ',): f'{BIO}/antibodies',
    ('Белки, ферменты и пептиды',): f'{BIO}/proteins',
    ('Молекулярная биология и генетика',): f'{BIO}/molecular-biology',
    ('Клеточная биология и микробиология', 'Штаммы, клеточные линии и контрольные культуры'): 'biological-standards',
    ('Клеточная биология и микробиология',): f'{BIO}/cell-biology',
    ('Лабораторная посуда и расходные материалы', 'Фильтры, мембраны и фильтровальная бумага'): f'{CH}/filters',
    ('Лабораторная посуда и расходные материалы',): SKIP,
    ('Лабораторное оборудование и мебель',): SKIP,
    ('Прочие товары',): SKIP,
}
_FILE_KEYS = {tuple(' '.join(part.split()).casefold() for part in key): path for key, path in FILE_CATEGORIES.items()}
# Publishers whose every item is a reference standard: their own subcategory, whatever the file's words say.
_PUBLISHERS = (f'{RS}/usp', f'{RS}/edqm', f'{RS}/british-pharmacopoeia', f'{RS}/lgc', 'biological-standards')


def file_category(direction: str, section: str, subgroup: str, brand: str, name: str) -> str | None:
    """The category of a row of the business's catalog; SKIP when it is not sold, None for an unknown direction
    (the brand rules decide then)."""
    parts = [' '.join(p.split()).casefold() for p in (direction, section, subgroup)]
    path = next((_FILE_KEYS[key] for key in (tuple(parts), tuple(parts[:2]), tuple(parts[:1])) if key in _FILE_KEYS),
                None)
    if path is None or path == SKIP:
        return path
    by_brand = category_for(brand, name)
    if by_brand in _PUBLISHERS:
        return by_brand
    # Merck's own reference materials keep their subcategory among the standards.
    if path.startswith(RS) and by_brand == f'{RS}/merck':
        return by_brand
    return path


def card_type_for(path: str | None) -> str:
    if not path:
        return 'standard'
    top = path.split('/')[0]
    if top == 'chromatography':
        return 'equipment'
    if top in ('biological-standards', 'pharmacopeias'):
        return 'other'
    return 'standard'
