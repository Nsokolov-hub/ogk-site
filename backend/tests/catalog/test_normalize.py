"""Normalization rules (SRCH-03, IMP-03, URL-05) on tables of real examples from the assortment export."""

from decimal import Decimal

import pytest

from app.catalog.normalize import (
    brand_key,
    compact,
    hill_key,
    looks_like_number,
    parse_cas,
    parse_pack,
    parse_packs,
    product_slug,
    split_pack_suffix,
    switch_layout,
)


@pytest.mark.parametrize(('raw', 'expected'), [
    ('Y0001897', 'y0001897'), ('1.00030', '100030'), ('58 08 2', '58082'), ('C/3400/08', 'c340008'),
    ('DRE-C20670000', 'drec20670000'), ('  ab_12 ', 'ab12'),
])
def test_compact_numbers(raw, expected):
    assert compact(raw) == expected


@pytest.mark.parametrize(('raw', 'expected'), [
    ('28721-07-5', ('28721-07-5', False)), ('28721075', ('28721-07-5', False)), ('58-08-2', ('58-08-2', False)),
    ('58082', ('58-08-2', False)), ('2139718', (None, True)), ('28721-07-4', (None, True)), ('N/A', (None, False)), ('', (None, False)),
    ('NA', (None, False)), ('abc', (None, True)),
])
def test_cas_check_digit(raw, expected):
    assert parse_cas(raw) == expected


@pytest.mark.parametrize(('raw', 'expected'), [
    ('C15H12N2O2', 'C15H12N2O2'), ('c15h12n2o2', 'C15H12N2O2'), ('C15 H12 N2 O2', 'C15H12N2O2'),
    ('H12C15O2N2', 'C15H12N2O2'), ('C₁₅H₁₂N₂O₂', 'C15H12N2O2'), ('C8H9NO2', 'C8H9NO2'),
    ('CH3Cl', 'CH3Cl'), ('ch3cl', 'CH3Cl'), ('Paracetamol', None), ('Y0001897', None), ('1234', None),
])
def test_hill_order(raw, expected):
    assert hill_key(raw) == expected


@pytest.mark.parametrize(('raw', 'key', 'ru', 'en'), [
    ('250 мг', '250-mg', '250 мг', '250 mg'), ('0,1 мл', '0-1-ml', '0,1 мл', '0.1 ml'),
    ('25.0 g', '25-g', '25 г', '25 g'), ('1г', '1-g', '1 г', '1 g'), ('2.5 l', '2-5-l', '2,5 л', '2.5 l'),
    ('4x2.5 l', '4x2-5-l', '4 × 2,5 л', '4 × 2.5 l'), ('96 t', '96-test', '96 тест.', '96 tests'),
    ('100 ?G', '100-ug', '100 мкг', '100 µg'), ('400 ?L', '400-ul', '400 мкл', '400 µl'),
    ('1 шт', '1-pcs', '1 шт.', '1 pcs'), ('шт', '1-pcs', '1 шт.', '1 pcs'), ('1.0 kg', '1-kg', '1 кг', '1 kg'),
    ('5 флаконов', '5-vial', '5 фл.', '5 vial'), ('1000 мг', '1000-mg', '1000 мг', '1000 mg'),
])
def test_packagings(raw, key, ru, en):
    pack = parse_pack(raw)
    assert pack is not None and (pack.key, pack.label_ru, pack.label_en) == (key, ru, en)


def test_unknown_packaging_stays_as_written_and_lists_split():
    pack = parse_pack('10 колб по 5 мл')
    assert pack is not None and pack.label_ru == '10 колб по 5 мл' and pack.unit is None
    assert [p.key for p in parse_packs('100 мг | 1 г | 100 мг')] == ['100-mg', '1-g']
    assert parse_packs('') == [] and parse_pack(None) is None
    small = parse_pack('2,5 мг')
    assert small is not None and small.amount == Decimal('2.5')


@pytest.mark.parametrize(('number', 'pack', 'base', 'label'), [
    ('CS-T-60514-5MG', '5 мг', 'CS-T-60514', '5 мг'), ('CS-T-60514-100MG', None, 'CS-T-60514', '100 мг'),
    ('AB477228-1мг', None, 'AB477228', '1 мг'), ('SIN-10039-MM09-A-25Tests', '25 тест', 'SIN-10039-MM09-A', '25 тест.'),
    ('AG005JV6-100', '100 мг', 'AG005JV6', '100 мг'), ('CS-CD-00140-500GM', '500 г', 'CS-CD-00140', '500 г'),
    ('SRP0562-100UG', None, 'SRP0562', '100 мкг'),
    # Numbers that do not end with their packaging stay whole.
    ('Y0001897', '100 мг', 'Y0001897', '100 мг'), ('46142-0050', '5 г', '46142-0050', '5 г'),
    ('160-2655-1', None, '160-2655-1', None), ('NBP2-47725F', '0,1 мл', 'NBP2-47725F', '0,1 мл'),
])
def test_packaging_suffix_of_catalog_numbers(number, pack, base, label):
    found, packaging = split_pack_suffix(number, parse_pack(pack))
    assert found == base
    assert (packaging.label_ru if packaging else None) == label


def test_layout_numbers_slugs_and_brand_spellings():
    assert switch_layout('jrcrfh,fptgby') == 'окскарбазепин'
    assert switch_layout('щчсфкифяузшт') == 'oxcarbazepin'
    assert looks_like_number('Y0001897') and looks_like_number('58 08 2') and looks_like_number('1.00030')
    assert looks_like_number('Y 000 1897') and not looks_like_number('100 mg caffeine')
    assert not looks_like_number('C18 column') and not looks_like_number('oxcarbazepine') and not looks_like_number('12')
    assert product_slug('edqm', 'Y0001897', 'Oxcarbazepine CRS') == 'edqm-y0001897-oxcarbazepine-crs'
    assert len(product_slug('edqm', 'Y0001897', 'x' * 200)) == 80
    assert product_slug('himlaborpribor', 'ХЛП-1', 'Шкаф вытяжной') == 'himlaborpribor-khlp-1-shkaf-vytyazhnoy'
    assert brand_key('Riedel-de Haën (Honeywell)') == brand_key('riedel de haen honeywell')
    assert brand_key('Merck KGaA') != brand_key('Merck') and brand_key('ABCR GmbH') == brand_key('ABCR')
    assert brand_key('R&D Systems') == brand_key('R and D Systems')


def test_only_formula_and_molecular_weight_are_taken_from_characteristics():
    from app.catalog.normalize import chemical_facts

    assert chemical_facts('Молекулярный вес: 322.70 g/mol; Формула: C9H10N2O; Плотность: 1.2; Точка кипения: 1') == {
        'formula': 'C9H10N2O', 'formula_hill': 'C9H10N2O', 'molecular_weight': '322,70'}
    assert chemical_facts('Formula: C22H36FeP2; Molecular Weight: 220.26 g/mol')['formula_hill'] == 'C22H36FeP2'
    assert chemical_facts('Формула: C6H12O6·H2O') == {'formula': 'C6H12O6·H2O'}
    assert chemical_facts('Формула: None; Молекулярный вес: None; Вес: 200 г') == {}
    assert chemical_facts('Альтернативное название: ГАМК; Хост: Мышь') == {}
