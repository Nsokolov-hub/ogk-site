"""Dated warehouse news and the warehouse column of the supplier's PDF, without guessed manufacturer identity."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.catalog.stock_sources.additional import algimed_parse, csdb_parse, csdb_text
from app.catalog.stock_sources.base import ParseChanged


def algimed(rows: str) -> str:
    return '<h1>Складские остатки</h1><p>Актуализация: 29 октября 2026 г.</p>' \
        '<table><tr><th>Номенклатура</th><th>Количество</th></tr>' + rows + '</table>'


def test_news_keeps_declared_stock_date_and_brand_specific_offer_identity():
    result = algimed_parse(algimed('<tr><td colspan="2">EDQM</td></tr>'
        '<tr><td>Стандарт, 100 мг, EDQM, DEMO-1</td><td>2</td></tr>'
        '<tr><td colspan="2">USP</td></tr>'
        '<tr><td>Стандарт, 100 мг, USP, DEMO-1</td><td>3</td></tr>'
        '<tr><td>Стандарт, 100 мг, USP, DEMO-2</td><td>0</td></tr>'))
    assert len(result.offers) == 2
    first, second = result.offers
    assert first.external_id != second.external_id
    assert first.catalog_number == second.catalog_number == 'DEMO-1'
    assert first.brand_name == 'EDQM' and second.brand_name == 'USP'
    assert first.pack == '100 мг' and first.quantity == 2
    assert first.stock_updated_at == datetime(2026, 10, 29, tzinfo=UTC)


def test_news_layout_and_quantity_changes_never_become_verified_empty_stock():
    with pytest.raises(ParseChanged):
        algimed_parse('<h1>Каталог</h1>Нет совпадений')
    result = algimed_parse(algimed('<tr><td colspan="2">USP</td></tr>'
        '<tr><td>Стандарт, 100 мг, USP, DEMO-1</td><td>Уточнить</td></tr>'))
    assert not result.offers and result.incomplete


def layout(values):
    widths = [35, 20, 18, 12, 14, 22, 12, 12, 12, 20]
    return ''.join(str(value).ljust(width) for value, width in zip(values, widths, strict=True))


def pdf_text():
    return '\n'.join([
        layout(['Наименование', 'ГОСТ', 'CAS', 'Перейти', '500 кг', 'Базовая уп.', '1 кг', '0,5 кг', '0,1 кг', 'Наличие на']),
        layout(['Реагент А', '', '90-15-3', 'перейти', '100', '10 (1 кг)', '10', '5', '1', 'СПБ']),
        layout(['Реагент Б', '', '57-48-7', 'перейти', '100', '10 (25 кг)', '10', '5', '1', 'с 25.12.26']),
        layout(['Реагент В', '', '58-86-6', 'перейти', '100', '10 (1 кг)', '10', '5', '1', 'СПБ']),
        'Цены указаны за упаковку без учета НДС 22% на 20.11.26',
    ])


def test_pdf_stock_column_distinguishes_warehouse_and_future_delivery(monkeypatch):
    import pypdf

    class Page:
        def extract_text(self, **_kwargs):
            return pdf_text()

        def get(self, _key, _default):
            return [SimpleNamespace(get_object=lambda i=i: {'/A': {'/URI': f'https://www.csdb.ru/shop/demo-{i}'}})
                    for i in range(3)]

    monkeypatch.setattr(pypdf, 'PdfReader', lambda _stream: SimpleNamespace(pages=[Page()]))
    result = csdb_parse(b'%PDF-test')
    assert len(result.offers) == 2 and result.incomplete
    assert [offer.name for offer in result.offers] == ['Реагент А', 'Реагент В']
    assert all(offer.review_only and offer.brand_name == '' and offer.catalog_number == '' for offer in result.offers)
    assert all(offer.quantity is None and offer.price is None for offer in result.offers)
    assert result.offers[0].pack == '1 кг'
    assert result.offers[0].stock_updated_at == datetime(2026, 11, 20, tzinfo=UTC)


def test_pdf_unknown_layout_and_malformed_pdf_are_source_errors():
    with pytest.raises(ParseChanged, match='columns_changed'):
        csdb_text('Каталог, цены, купить')
    with pytest.raises(ParseChanged):
        csdb_parse(b'%PDF-not-a-real-document')
