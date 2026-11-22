"""Public source adapters; additions use the same Offer/Page contract as the existing suppliers."""

import importlib
import importlib.util

from app.catalog.stock_sources import dia_m, labteh, laverna, vilax

SOURCES = {'diam': dia_m.page, 'labteh': labteh.page, 'laverna': laverna.page, 'vilax': vilax.page}
FIRST = {source: {'s': source, 'url': module.START, 'page': 1}
         for source, module in [('diam', dia_m), ('labteh', labteh), ('laverna', laverna), ('vilax', vilax)]}
NAMES = {'diam': 'Диаэм', 'labteh': 'Лабтех', 'laverna': 'Лаверна XXI век', 'vilax': 'Вилакс'}
META = {
    'diam': {'name': NAMES['diam'], 'url': dia_m.START, 'origin': dia_m.ORIGIN,
             'paths': list(dia_m.PREFIXES), 'status': 'supported',
             'reason': 'Наличие только в строке таблицы конкретной фасовки'},
    'labteh': {'name': NAMES['labteh'], 'url': labteh.START, 'origin': labteh.ORIGIN,
               'paths': list(labteh.PREFIXES), 'status': 'supported',
               'reason': 'Наличие только при явном подтверждении в сроке поставки'},
    'laverna': {'name': NAMES['laverna'], 'url': 'https://laverna-xxi.ru/', 'origin': laverna.ORIGIN,
                'paths': ['/catalog/'], 'status': 'needs_verification',
                'reason': 'Проверяются открытые каталоги и карточки; запрос стоимости не подтверждает остаток'},
    'vilax': {'name': NAMES['vilax'], 'url': vilax.START, 'origin': vilax.ORIGIN,
              'paths': list(vilax.PREFIXES), 'status': 'supported',
              'reason': 'Количество и фасовки из открытых разделов Welch и химических реактивов'},
}

if importlib.util.find_spec('app.catalog.stock_sources.additional') is not None:
    additional = importlib.import_module('app.catalog.stock_sources.additional')
    SOURCES.update(additional.SOURCES)
    FIRST.update(additional.FIRST)
    NAMES.update(additional.NAMES)
    META.update(additional.META)
