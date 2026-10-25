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
    **{brand_key(b): 'laboratory-equipment' for b in (
        'Mettler Toledo', 'Heidolph', 'IKA', 'Julabo', 'DLAB', 'Biobase', 'Memmert', 'Binder', 'Liebherr',
        'Martin Christ', 'Tuttnauer', 'Milestone', 'Haier Biomedical', 'NuAire', 'Arctiko', 'SNOL', 'Panasonic',
        'Huber', 'Elma', 'Erweka', 'Gilson', 'Biosan', 'Kinematica', 'Gerhardt', 'BEING TECHNOLOGY', 'Boxun',
        'Labonce', 'AND', 'Вибротехник', 'Ламинарные системы', 'ЛОиП', 'Химлаборприбор', 'Beckman Coulter',
        'Sigma Laborzentrifugen', 'Shimadzu', 'SCIEX', 'Changsha Samy Instruments', 'Vacuubrand', 'Yamato',
        'Kruss Optronic', 'Buchi Labortechnik', 'Vilber', 'Pharma Test', 'RWD', 'Adrona', 'GFL (LAUDA)', 'GFL',
        'Elmi', 'Позис', 'Retsch', 'Aquila Biolabs', 'Hettich', 'Foss', 'Biohit', 'Labconco', 'Wenk LabTec',
        'Fiocchetti', 'Testo', 'Metash', 'Miele', 'Fungilab', 'Hermle', 'Esco', 'Atlas Copco', 'CAMAG', 'VirTis',
        'Bioer', 'Hanna Instruments', 'ЛОМО', 'Qsonica', 'Watson-Marlow', 'Hitachi', 'Avestin', 'Porkka', 'ZEISS',
        'Stuart', 'Analytik Jena', 'Люмэкс', 'Томьаналит', 'ЭКАН', 'Эконикс-Эксперт', 'ЛТО', 'Duperthal',
        'Смоленское СКТБ СПУ', 'Schuett', 'BioCision', 'Awel')},
    **{brand_key(b): 'laboratory-glassware' for b in (
        'Kavalier', 'Marienfeld', 'Hirschmann', 'Vitlab', 'ROBU', 'Isolab', 'Brand', 'DWK Life Sciences', 'Hellma',
        'Экрос', 'Kavalierglass')},
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


def card_type_for(path: str | None) -> str:
    if not path:
        return 'standard'
    top = path.split('/')[0]
    if top in ('chromatography', 'laboratory-equipment'):
        return 'equipment'
    if top in ('laboratory-glassware', 'biological-standards', 'pharmacopeias'):
        return 'other'
    return 'standard'
