"""Controlled substances (TZ 5.2.1): lists of Government Decrees No. 681 and No. 964.

A product is checked by CAS and by names on import and on edit. A CAS match marks it at once; a match by name
only (salts, a missing CAS) goes to the chemist for review. Marked products are hidden from the storefront,
search, Sitemap and the feed while the setting ``hide_controlled`` is on.

Business remark of 31 October 2026 (precursors of List IV): a name matches when the product's name *is* the
substance — after its grade, purity, concentration, solvent, salt and stereo prefix are taken off («Acetone HPLC
grade ≥99.9%», «Ephedrine hydrochloride», «Кислота соляная хч»). A name that merely contains the substance as a
word («Piperidine-4-carboxylic acid», «Toluene-2,4-diisocyanate», «3,4-Dimethoxybenzaldehyde») is another
substance, so a catalog of building blocks is not hidden by «piperidine» or «toluene».
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.catalog.models import ControlledEntry
from app.catalog.normalize import cas_or_none, clean_spaces

# Words after the substance that do not change it: grades, purity, form, use; Russian grades too.
DESCRIPTORS = frozenset("""
    hplc uhplc lc ms lc-ms lc/ms gc gc-ms gc/ms acs reagent reagentplus anhydrous puriss puriss. p.a. pa analytical
    analysis standard reference crs rs usp ep bp jp nf ph.eur. ph. eur. eur grade gradient extra pure dry solution
    solvent technical tech certified secondary pharmaceutical pharma for synthesis spectroscopy spectrophotometric
    absolute glacial fuming concentrated conc conc. redistilled distilled ultrapure uv ir nmr hplc-grade lichrosolv
    suprasolv emsure chromasolv chromanorm normapur analar emparta bioreagent biochemistry molecular biology plus
    purum purified purity min. min max. approx. approx assay stabilized stabilised unstabilized inhibitor-free free
    traceselect tracepur ultra optima high very low water residue residues pesticide pestanal amd vetec sigma-aldrich
    reagent-grade lab laboratory bulk sample -
    хч х.ч. чда ч.д.а. осч о.с.ч. ч ч. имп имп. импорт безводный безводная безводное ледяная ледяной
    концентрированная конц конц. раствор р-р стандарт титр стандарт-титр фиксанал для вэжх гх спектроскопии анализа
    особо чистый чистая чистое химически марки марка сорт высший технический техн техн. фармакопейный фарм эталон
    гсо со медицинский медицинская
""".split())
SALTS = frozenset("""
    hydrochloride hcl dihydrochloride sulfate sulphate hemisulfate bisulfate tartrate bitartrate maleate hydrobromide
    hbr citrate phosphate salt monohydrate dihydrate trihydrate hemihydrate sesquihydrate hydrate base
    гидрохлорид сульфат тартрат битартрат малеат гидробромид цитрат фосфат соль моногидрат дигидрат гидрат основание
""".split())
QUANTITY = re.compile(r'[≥≤<>~±]?\d+(?:[.,]\d+)?\+?(?:-\d+(?:[.,]\d+)?)?(?:%|‰|ppm|mm|m|n|mol/l|g/l|mg/ml|µg/ml'
                      r'|ug/ml|ml|l|g|kg|mg|мл|л|г|кг|мг|м|н|моль/л|w/w|v/v)?|%|m|n|mol/l|моль/л|w/w|v/v|wt\.?')
STEREO = re.compile(r'^(?:\((?:[+±-]|[rs]|\d+[rs](?:,\d+[rs])*|rs|r/s)\)-|(?:dl|d|l|rac|cis|trans)-|[±+-]-)+')
# After a comma these words make another substance: «Benzaldehyde, 4-methyl-», «Ether, butyl ethyl»,
# «Уксусная кислота, аммонийная соль» (ammonium acetate), labelled forms.
MODIFIERS = frozenset("""
    bis tris tetrakis butyl ethyl methyl propyl isopropyl phenyl benzyl hexyl octyl dimethyl diethyl dibutyl
    sodium potassium ammonium lithium calcium magnesium zinc copper silver barium cesium caesium rubidium aluminium
    aluminum iron nickel cobalt manganese ester oxime hydrazone semicarbazone acetal amide nitrile compd compound
    polymer resin derivative labeled labelled deuterated homopolymer copolymer
    dimethanesulfonate methanesulfonate diacetate monoacetate dibenzoate diacrylate dimethacrylate diglycidyl
    dinitrate ditosylate tosylate triflate glucuronide metabolite impurity
    натриевая калиевая аммонийная литиевая кальциевая магниевая цинковая медная серебряная бариевая цезиевая
    натрия калия аммония лития кальция магния цинка меди серебра бария эфир этиловый метиловый бутиловый
    ангидрид амид нитрил оксим гидразон дейтерированный меченый полимер
""".split())
CHEMICAL_PART = re.compile(r'\d[\d,]*-|-$|[()\[\]]|^(?:[nosp]|alpha|beta|gamma|delta|tert|sec|iso)-|^[αβγδ]-|^d\d+$|^\d+c$')


def _descriptive(segment: str) -> bool:
    """A part after a comma that only names a grade, purity or form, not a substituent or another compound."""
    for token in segment.split():
        if QUANTITY.fullmatch(token) or token in DESCRIPTORS or token in SALTS:
            continue
        if token in MODIFIERS or CHEMICAL_PART.search(token):
            return False
    return True


def core_name(text: str) -> str:
    """The substance a product name names: grade, purity, concentration, solvent, salt and stereo prefix taken off.

    A name whose part after a comma changes the compound («Benzaldehyde, 2,4-dibromo-») stays whole, so it names
    another substance than its head word.
    """
    value = re.sub(r'[®™©*]', '', text.casefold().replace('ё', 'е'))
    value = re.sub(r'[‐‑‒–—−]', '-', value).strip()
    value = re.split(r'\s-\s|\s/\s', value, maxsplit=1)[0]
    head, *rest = re.split(r'[,;]\s+', value)
    if not all(_descriptive(segment) for segment in rest):
        return re.sub(r'\s+', ' ', value)
    while (bracket := re.search(r'\s*[(\[][^()\[\]]*[)\]]\s*$', head)) and bracket.start() > 0:
        head = head[:bracket.start()]
    head = re.sub(r'\s+(?=[(\[])', '', head)
    head = STEREO.sub('', head.strip())
    tokens = head.split()
    for index, token in enumerate(tokens[1:], start=1):
        if token in ('in', 'в', 'with', 'с', 'for', 'для', 'according', 'согласно', 'meets', 'соответствует'):
            tokens = tokens[:index]
            break
    while len(tokens) > 1 and (tokens[-1] in DESCRIPTORS or tokens[-1] in SALTS or QUANTITY.fullmatch(tokens[-1])):
        tokens.pop()
    return ' '.join(tokens)


@dataclass
class Register:
    by_cas: dict[str, str] = field(default_factory=dict)
    # The core name of a substance or synonym → list; a product matches when its core name is the same.
    names: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, db: Session) -> 'Register':
        return cls.build((entry.list_name, entry.cas, entry.names) for entry in db.scalars(select(ControlledEntry)))

    @classmethod
    def build(cls, entries: Any) -> 'Register':
        """From (list, CAS numbers, names) of each entry."""
        register = cls()
        for listed, cas_numbers, names in entries:
            for cas in cas_numbers:
                register.by_cas[cas] = listed
            for name in names:
                if key := core_name(name):
                    register.names.setdefault(key, listed)
        return register

    def match(self, name: str, cas: str | None, synonyms: list[str] | tuple[str, ...] = ()) -> tuple[str, str] | None:
        """(list, state): state «auto» for a CAS match, «review» for a match by name only."""
        if cas and cas in self.by_cas:
            return self.by_cas[cas], 'auto'
        for text in (name, *synonyms):
            if text and (listed := self.names.get(core_name(text))):
                return listed, 'review'
        return None


def apply(register: Register, *, name: str, cas: str | None, synonyms: list[str], current: str | None,
          state: str | None) -> tuple[str | None, str | None]:
    """The new (controlled, controlled_state) of a product; the chemist's decision is never overwritten."""
    if state in ('confirmed', 'cleared'):
        return current, state
    hit = register.match(name, cas, synonyms)
    return (hit[0], hit[1]) if hit else (None, None)


def load_register(db: Session, entries: list[dict[str, Any]]) -> int:
    """Replace the register: [{"list": "pp681", "name": ..., "cas": [...], "names": [...]}]."""
    db.execute(delete(ControlledEntry))
    count = 0
    for raw in entries:
        listed = str(raw.get('list') or '')
        if listed not in ('pp681', 'pp964'):
            raise ValueError(f'Неизвестный перечень: {listed!r}')
        names = [clean_spaces(str(n)).casefold() for n in raw.get('names') or [] if clean_spaces(str(n))]
        cas = [c for c in (cas_or_none(str(v)) for v in raw.get('cas') or []) if c]
        db.add(ControlledEntry(list_name=listed, name=str(raw.get('name') or (names[0] if names else cas[0])),
                               cas=cas, names=names))
        count += 1
    db.flush()
    return count


def read_register(path: Path) -> list[dict[str, Any]]:
    """Entries of a register file: our JSON (seed/controlled-register.json) or an xlsx of the chemist."""
    if path.suffix.lower() == '.json':
        import json

        data = json.loads(path.read_text(encoding='utf-8'))
        return list(data['entries'] if isinstance(data, dict) else data)
    return read_register_xlsx(path)


def read_register_xlsx(path: Path) -> list[dict[str, Any]]:
    """Rows of a register file: columns «Перечень» (681/964), «Название», «CAS», «Синонимы» (через «;»)."""
    from app.catalog.importer.reader import read_rows

    entries = []
    rows = read_rows(path)
    header = [clean_spaces(str(cell)).casefold() for cell in next(rows)]

    def column(*names: str) -> int:
        for i, title in enumerate(header):
            if any(title.startswith(name) for name in names):
                return i
        raise ValueError(f'В файле нет колонки «{names[0]}»')

    listed, title, cas, synonyms = column('перечень', 'list'), column('назван', 'name'), column('cas'), \
        column('синоним', 'synonym')
    def value(row: list[str | None], i: int) -> str:
        return clean_spaces(str(row[i])) if i < len(row) and row[i] is not None else ''

    for row in rows:
        code = 'pp964' if '964' in value(row, listed) else 'pp681'
        name = value(row, title)
        if not name:
            continue
        entries.append({'list': code, 'name': name, 'cas': re.split(r'[;,\s]+', value(row, cas)),
                        'names': [name, *[s for s in value(row, synonyms).split(';') if s.strip()]]})
    return entries
