"""Yandex Metrica and Webmaster in the admin panel: the token stays secret, goals are created once, the reports of
each period come from one snapshot, a refused service leaves the other one working."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.admin.models import AuditEntry
from app.analytics import yandex
from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.crm.conversions import METRIKA_TARGETS

TOKEN = 'y0_AgAAAAB-test-token_0123456789abcdefXYZ'
TODAY = date(2026, 11, 2)
HOST = 'https:www.ogk-chem.ru:443'


class FakeYandex:
    """Metrica and Webmaster with the answers of their documentation; ``refuse`` — a service answers this status."""

    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.refuse: dict[str, int] = {}
        self.goals = [{'id': 1, 'name': 'Отправка формы', 'type': 'action',
                       'conditions': [{'type': 'exact', 'url': 'form_submit'}]},
                      {'id': 2, 'name': 'Страница контактов', 'type': 'url',
                       'conditions': [{'type': 'contain', 'url': '/contacts/'}]}]
        self.sitemaps: list[str] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        assert request.headers['Authorization'] == f'OAuth {TOKEN}'
        host, path, params = request.url.host, request.url.path, request.url.params
        if host in self.refuse:
            return httpx.Response(self.refuse[host], json={'message': 'Access denied', 'error_message': 'denied'})
        if host == 'api-metrika.yandex.net':
            return self.metrika(request, path, params)
        if host == 'api.webmaster.yandex.net':
            return self.webmaster(request, path, params)
        return httpx.Response(404)

    def metrika(self, request: httpx.Request, path: str, params: httpx.QueryParams) -> httpx.Response:
        if path == '/management/v1/counter/98765':
            return httpx.Response(200, json={'counter': {'id': 98765, 'name': 'Сайт ОГК-ХИМ', 'owner_login': 'ogkteam',
                                                         'permission': 'own'}})
        if path == '/management/v1/counter/98765/goals':
            if request.method == 'POST':
                goal = json.loads(request.content)['goal']
                goal['id'] = len(self.goals) + 1
                self.goals.append(goal)
                return httpx.Response(200, json={'goal': goal})
            return httpx.Response(200, json={'goals': self.goals})
        assert path == '/stat/v1/data' and params['ids'] == '98765' and params['accuracy'] == 'full'
        days = (date.fromisoformat(params['date2']) - date.fromisoformat(params['date1'])).days + 1
        dimension = params.get('dimensions')
        if dimension == 'ym:s:date':
            return httpx.Response(200, json={'data': [
                {'dimensions': [{'name': '2026-11-01'}], 'metrics': [12, 10, 40, 25.0, 95]},
                {'dimensions': [{'name': '2026-11-02'}], 'metrics': [8, 7, 20, 37.5, 60]},
            ], 'totals': [20 * days / 7, 15, 60, 30.04, 80]})
        if dimension == 'ym:s:lastsignTrafficSource':
            return httpx.Response(200, json={'data': [
                {'dimensions': [{'id': 'organic', 'name': 'Переходы из поисковых систем'}], 'metrics': [14, 11]},
                {'dimensions': [{'id': 'direct', 'name': 'Прямые заходы'}], 'metrics': [6, 5]}]})
        if dimension == 'ym:s:lastsignSearchEngineRoot':
            assert params['filters'] == "ym:s:lastsignTrafficSource=='organic'"
            return httpx.Response(200, json={'data': [{'dimensions': [{'name': 'Яндекс'}], 'metrics': [10]},
                                                      {'dimensions': [{'name': 'Google'}], 'metrics': [4]}]})
        if dimension == 'ym:s:startURLPath':
            return httpx.Response(200, json={'data': [{'dimensions': [{'name': '/cas/69-65-8/'}], 'metrics': [5, 20.0]}]})
        assert dimension is None
        metrics = params['metrics'].split(',')
        assert len(metrics) <= 20
        return httpx.Response(200, json={'data': [], 'totals': [3 if 'reaches' in m else 1.5 for m in metrics]})

    def webmaster(self, request: httpx.Request, path: str, params: httpx.QueryParams) -> httpx.Response:
        base = f'/v4/user/42/hosts/{HOST}'
        if path == '/v4/user':
            return httpx.Response(200, json={'user_id': 42})
        if path == '/v4/user/42/hosts':
            return httpx.Response(200, json={'hosts': [
                {'host_id': 'https:ogk-chem.ru:443', 'ascii_host_url': 'https://ogk-chem.ru/', 'verified': True},
                {'host_id': HOST, 'ascii_host_url': 'https://www.ogk-chem.ru/', 'verified': True}]})
        if path == f'{base}/summary':
            return httpx.Response(200, json={'sqi': 0, 'excluded_pages_count': 31, 'searchable_pages_count': 9,
                                             'site_problems': {'FATAL': 0, 'CRITICAL': 1, 'RECOMMENDATION': 2}})
        if path == f'{base}/diagnostics':
            return httpx.Response(200, json={'problems': {
                'NO_REGIONS': {'severity': 'RECOMMENDATION', 'state': 'PRESENT'},
                'DOCUMENTS_MISSING_TITLE': {'severity': 'CRITICAL', 'state': 'PRESENT'},
                'NO_SITEMAPS': {'severity': 'POSSIBLE_PROBLEM', 'state': 'ABSENT'},
                'SOMETHING_NEW': {'severity': 'RECOMMENDATION', 'state': 'PRESENT'}}})
        if path == f'{base}/sitemaps':
            return httpx.Response(200, json={'sitemaps': [
                {'sitemap_url': 'https://www.ogk-chem.ru/sitemap.xml', 'urls_count': 0, 'errors_count': 0,
                 'children_count': 26, 'last_access_date': '2026-11-01T10:00:00.000+03:00'}]})
        if path == f'{base}/user-added-sitemaps':
            if request.method == 'POST':
                self.sitemaps.append(json.loads(request.content)['url'])
                return httpx.Response(201, json={'sitemap_id': 'x'})
            return httpx.Response(200, json={'sitemaps': [{'sitemap_url': u} for u in self.sitemaps]})
        if path == f'{base}/search-urls/events/samples':
            return httpx.Response(200, json={'samples': [
                {'url': 'https://www.ogk-chem.ru/a/', 'event': 'REMOVED_FROM_SEARCH', 'excluded_url_status': 'LOW_DEMAND'},
                {'url': 'https://www.ogk-chem.ru/b/', 'event': 'REMOVED_FROM_SEARCH', 'excluded_url_status': 'LOW_DEMAND'},
                {'url': 'https://www.ogk-chem.ru/c/', 'event': 'REMOVED_FROM_SEARCH', 'excluded_url_status': 'NOT_CANONICAL'},
                {'url': 'https://www.ogk-chem.ru/d/', 'event': 'APPEARED_IN_SEARCH'}]})
        if path == f'{base}/search-queries/popular':
            assert params.get_list('query_indicator') == ['TOTAL_SHOWS', 'TOTAL_CLICKS', 'AVG_SHOW_POSITION']
            return httpx.Response(200, json={'queries': [{'query_text': 'маннит стандарт', 'indicators': {
                'TOTAL_SHOWS': 120.0, 'TOTAL_CLICKS': 7.0, 'AVG_SHOW_POSITION': 8.26}}]})
        if path == f'{base}/search-queries/all/history':
            return httpx.Response(200, json={'indicators': {
                'TOTAL_SHOWS': [{'date': '2026-11-01T00:00:00.000+03:00', 'value': 70.0},
                                {'date': '2026-11-02T00:00:00.000+03:00', 'value': 50.0}],
                'TOTAL_CLICKS': [{'date': '2026-11-02T00:00:00.000+03:00', 'value': 7.0}]}})
        if path == f'{base}/search-urls/in-search/history':
            return httpx.Response(200, json={'history': [{'date': '2026-10-30T00:00:00.000+03:00', 'value': 4},
                                                         {'date': '2026-11-01T00:00:00.000+03:00', 'value': 9}]})
        if path == f'{base}/indexing/history':
            return httpx.Response(200, json={'indicators': {
                'HTTP_2XX': [{'date': '2026-11-01T00:00:00.000+03:00', 'value': 300}],
                'HTTP_3XX': [{'date': '2026-11-01T00:00:00.000+03:00', 'value': 20}],
                'HTTP_4XX': [{'date': '2026-11-01T00:00:00.000+03:00', 'value': 3}],
                'OTHER': [{'date': '2026-11-01T00:00:00.000+03:00', 'value': 1}]}})
        return httpx.Response(404, json={'error_message': f'unknown {path}'})


@pytest.fixture
def fake(monkeypatch) -> FakeYandex:
    fake = FakeYandex()
    monkeypatch.setattr(yandex, 'http_client', lambda: httpx.Client(transport=httpx.MockTransport(fake.handle)))
    monkeypatch.setattr(yandex, 'today', lambda: TODAY)
    monkeypatch.setattr(settings, 'ym_counter_id', '98765')
    monkeypatch.setattr(settings, 'metrika_oauth_token', '')
    monkeypatch.setattr(settings, 'site_url', 'https://www.ogk-chem.ru')
    return fake


def test_the_goals_cover_the_site_events_and_the_crm_stages():
    identifiers = [i for i, _ in yandex.GOALS]
    assert len(identifiers) == len(set(identifiers))
    assert set(METRIKA_TARGETS.values()) <= set(identifiers)
    source = Path(__file__).resolve().parents[3] / 'src' / 'lib' / 'analytics.ts'
    if not source.exists():
        pytest.skip('нет исходников витрины рядом (тесты внутри образа API)')
    events = source.read_text(encoding='utf-8')
    for identifier in identifiers:
        assert identifier.startswith('crm_') or f"'{identifier}'" in events, identifier


def test_the_token_is_checked_kept_encrypted_and_never_shown(fake, signed_in, sessions):
    admin, viewer = signed_in('admin'), signed_in('viewer')
    assert viewer.put('/analytics/token', {'token': TOKEN}).status_code == 403
    assert admin.put('/analytics/token', {'token': 'не токен'}).json()['code'] == 'TOKEN_INVALID'
    assert not fake.calls

    answer = admin.ok(admin.put('/analytics/token', {'token': f'  OAuth {TOKEN} '}))
    assert answer['access']['metrika'] == {'ok': True, 'name': 'Сайт ОГК-ХИМ', 'login': 'ogkteam', 'permission': 'own'}
    assert answer['access']['webmaster'] == {'ok': True, 'host': 'https://www.ogk-chem.ru/'}
    status = answer['status']
    assert status['connected'] and status['source'] == 'admin' and status['tail'] == TOKEN[-4:]
    assert status['login'] == 'ogkteam' and status['savedBy'] == 'Сотрудник admin'
    # Goals: form_submit was there, the other 13 are created once as «JavaScript-событие».
    states = {g['identifier']: g['state'] for g in answer['goals']}
    assert states['form_submit'] == 'exists' and list(states.values()).count('created') == len(yandex.GOALS) - 1
    created = [g for g in fake.goals if g['id'] > 2]
    assert all(g['type'] == 'action' and g['conditions'][0]['type'] == 'exact' for g in created)
    again = admin.ok(admin.post('/analytics/goals'))['goals']
    assert {g['state'] for g in again} == {'exists'} and len(fake.goals) == len(yandex.GOALS) + 1

    with sessions() as db:
        stored = get_setting(db, 'yandex_token')
        assert TOKEN not in json.dumps(stored) and stored['cipher']
        assert yandex.token(db) == TOKEN
        journal = ' '.join(f'{e.summary} {json.dumps(e.before)} {json.dumps(e.after)}'
                           for e in db.scalars(select(AuditEntry)))
        assert TOKEN not in journal and f'…{TOKEN[-4:]}' in journal and 'form_start' in journal
    for path in ('/analytics', '/settings'):
        assert TOKEN not in admin.get(path).text
    assert viewer.ok(viewer.get('/analytics'))['status']['tail'] == TOKEN[-4:]

    assert admin.ok(admin.delete('/analytics/token'))['status']['connected'] is False
    with sessions() as db:
        assert yandex.token(db) == ''


def test_a_token_neither_service_accepts_is_not_kept(fake, signed_in, sessions):
    fake.refuse = {'api-metrika.yandex.net': 401, 'api.webmaster.yandex.net': 403}
    answer = signed_in('admin').put('/analytics/token', {'token': TOKEN})
    assert answer.status_code == 422 and answer.json()['code'] == 'TOKEN_REFUSED'
    assert 'отозван или истёк' in answer.json()['message'] and 'Нет доступа' in answer.json()['message']
    with sessions() as db:
        assert get_setting(db, 'yandex_token') is None


def test_the_reports_of_each_period_come_from_one_snapshot(fake, signed_in, sessions):
    admin = signed_in('admin')
    admin.ok(admin.put('/analytics/token', {'token': TOKEN}))
    fake.calls.clear()
    week = admin.ok(admin.post('/analytics/refresh', params={'period': 7}))
    assert week['status']['refreshedAt'] and week['fetchedAt'] and not week['status']['tokenInvalid']

    metrika = week['metrika']
    assert metrika['errors'] == [] and metrika['missingGoals'] == []
    assert metrika['totals'] == {'visits': 20, 'users': 15, 'pageviews': 60, 'bounceRate': 30.0, 'duration': 80}
    assert [d['date'] for d in metrika['days']] == [(TODAY - timedelta(days=6 - i)).isoformat() for i in range(7)]
    assert metrika['days'][-2:] == [{'date': '2026-11-01', 'visits': 12, 'users': 10},
                                    {'date': '2026-11-02', 'visits': 8, 'users': 7}]
    assert metrika['days'][0]['visits'] == 0
    assert metrika['sources'][0] == {'key': 'organic', 'name': 'Переходы из поисковых систем', 'visits': 14, 'users': 11}
    assert [e['name'] for e in metrika['engines']] == ['Яндекс', 'Google']
    assert metrika['pages'] == [{'path': '/cas/69-65-8/', 'visits': 5, 'bounceRate': 20.0}]
    goals = {g['identifier']: g for g in metrika['goals']}
    assert len(metrika['goals']) == len(yandex.GOALS) + 1 and goals['form_submit']['reaches'] == 3
    assert goals[None]['name'] == 'Страница контактов' and goals['crm_sale']['conversion'] == 1.5

    webmaster = week['webmaster']
    assert webmaster['errors'] == [] and webmaster['host'] == 'https://www.ogk-chem.ru/'
    assert webmaster['summary'] == {'inSearch': 9, 'excluded': 31, 'sqi': 0,
                                    'problems': {'FATAL': 0, 'CRITICAL': 1, 'RECOMMENDATION': 2}}
    assert [p['title'] for p in webmaster['problems']] == ['Страницы без title', 'Не указан регион сайта',
                                                            'SOMETHING_NEW']
    assert webmaster['removed'] == [
        {'title': 'Маловостребованная', 'count': 2,
         'examples': ['https://www.ogk-chem.ru/a/', 'https://www.ogk-chem.ru/b/']},
        {'title': 'Неканоническая: указан другой canonical', 'count': 1, 'examples': ['https://www.ogk-chem.ru/c/']}]
    assert webmaster['sitemaps'][0]['children'] == 26 and webmaster['sitemaps'][0]['added'] is False
    assert webmaster['queries'] == [{'text': 'маннит стандарт', 'shows': 120, 'clicks': 7, 'position': 8.3}]
    assert webmaster['queryTotals']['shows'] == 120 and webmaster['queryTotals']['clicks'] == 7
    # Pages in search are counted every few days: the gaps carry the last value.
    assert [p['value'] for p in webmaster['inSearch']] == [None, None, None, 4, 4, 9, 9]
    assert webmaster['crawled'] == {'ok': 300, 'redirect': 20, 'notFound': 3, 'error': 1}

    calls = len(fake.calls)
    quarter = admin.ok(admin.get('/analytics', params={'period': 90}))
    assert len(fake.calls) == calls and len(quarter['metrika']['days']) == 90
    assert quarter['metrika']['totals']['visits'] == round(20 * 90 / 7)
    assert admin.get('/analytics', params={'period': 14}).json()['code'] == 'PERIOD_INVALID'


def test_a_refused_service_leaves_the_other_and_an_expired_token_is_reported(fake, signed_in, sessions):
    admin = signed_in('admin')
    admin.ok(admin.put('/analytics/token', {'token': TOKEN}))
    fake.refuse = {'api.webmaster.yandex.net': 403}
    report = admin.ok(admin.post('/analytics/refresh'))
    assert report['metrika']['errors'] == [] and report['metrika']['totals']['visits'] > 0
    assert report['webmaster']['host'] is None
    assert report['webmaster']['errors'][0].startswith('Нет доступа к Вебмастеру: в приложении Яндекса')
    assert report['status']['tokenInvalid'] is False

    fake.refuse = {'api-metrika.yandex.net': 401, 'api.webmaster.yandex.net': 401}
    report = admin.ok(admin.post('/analytics/refresh'))
    assert report['status']['tokenInvalid'] is True
    assert 'отозван или истёк' in report['metrika']['errors'][0]


def test_the_sitemap_is_added_to_webmaster_once(fake, signed_in, sessions):
    admin = signed_in('admin')
    assert admin.post('/analytics/sitemap').json()['code'] == 'YANDEX_NOT_CONNECTED'
    admin.ok(admin.put('/analytics/token', {'token': TOKEN}))
    assert signed_in('content').post('/analytics/sitemap').status_code == 403
    assert admin.ok(admin.post('/analytics/sitemap')) == {'url': 'https://www.ogk-chem.ru/sitemap.xml', 'state': 'added'}
    assert admin.ok(admin.post('/analytics/sitemap'))['state'] == 'exists'
    assert fake.sitemaps == ['https://www.ogk-chem.ru/sitemap.xml']
    fake.refuse = {'api.webmaster.yandex.net': 403}
    refused = admin.post('/analytics/sitemap')
    assert refused.status_code == 422 and refused.json()['code'] == 'YANDEX_NO_ACCESS'


def test_the_worker_fetches_once_an_hour_and_conversions_use_the_admin_token(fake, signed_in, sessions):
    with sessions.begin() as db:
        assert not yandex.due(db)
    signed_in('admin').ok(signed_in('admin').put('/analytics/token', {'token': TOKEN}))
    with sessions.begin() as db:
        assert yandex.due(db)
        yandex.refresh(db)
        assert not yandex.due(db)
        later = datetime.fromisoformat(get_setting(db, 'yandex_reports_at')) + timedelta(hours=1)
        assert yandex.due(db, later) and not yandex.due(db, later - timedelta(minutes=1))
    # The server's token is the fallback; the admin panel's one wins.
    with sessions.begin() as db:
        settings.metrika_oauth_token = 'server-token-from-env'
        assert yandex.token(db) == TOKEN
        set_setting(db, 'yandex_token', None)
        assert yandex.token(db) == 'server-token-from-env' and yandex.status(db)['source'] == 'server'
        assert yandex.status(db)['tail'] is None


def test_a_token_without_metrica_and_a_site_webmaster_has_not_loaded_yet(fake, signed_in):
    """02.11.2026 in production: the app had no metrika:* rights; the site was added to Webmaster the day before."""
    real = fake.handle

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.host == 'api-metrika.yandex.net':
            fake.calls.append(request)
            return httpx.Response(403, json={'errors': [{'error_type': 'access_denied', 'message': 'Access Denied'}],
                                             'code': 403, 'message': 'Access Denied'})
        if request.url.path.startswith(f'/v4/user/42/hosts/{HOST}/'):
            fake.calls.append(request)
            return httpx.Response(404, json={'error_code': 'HOST_NOT_LOADED',
                                             'error_message': f'Host "{HOST}" is not loaded in Ya.Webmaster yet'})
        return real(request)

    fake.handle = handle  # type: ignore[method-assign]
    admin = signed_in('admin')
    answer = admin.ok(admin.put('/analytics/token', {'token': TOKEN}))
    assert answer['access']['metrika']['error'].startswith('Нет доступа к Метрике: в приложении Яндекса не отмечены')
    assert answer['access']['webmaster']['ok'] and answer['goals'] == 'нет доступа к Метрике'
    report = admin.ok(admin.post('/analytics/refresh'))
    assert report['webmaster']['errors'] == ['Вебмастер ещё собирает данные о сайте: после добавления это занимает '
                                             'несколько дней. Отчёт появится сам']
    assert report['metrika']['errors'][0].startswith('Нет доступа к Метрике')


def test_metrica_gets_at_most_two_requests_at_a_time_and_a_429_is_retried(fake, signed_in, monkeypatch):
    """02.11.2026 in production: six requests at once got «429 too many requests» for some blocks."""
    import threading
    import time

    real, lock = fake.handle, threading.Lock()
    state = {'now': 0, 'most': 0, 'refused': set()}

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.host != 'api-metrika.yandex.net' or request.url.path != '/stat/v1/data':
            return real(request)
        with lock:
            state['now'] += 1
            state['most'] = max(state['most'], state['now'])
        try:
            time.sleep(0.01)
            key = str(request.url)
            if key not in state['refused']:  # every report is refused once, then answered
                state['refused'].add(key)
                return httpx.Response(429, json={'message': 'Too many requests'})
            return real(request)
        finally:
            with lock:
                state['now'] -= 1

    fake.handle = handle  # type: ignore[method-assign]
    waits: list[float] = []
    monkeypatch.setattr(yandex, 'pause', waits.append)
    admin = signed_in('admin')
    admin.ok(admin.put('/analytics/token', {'token': TOKEN}))
    report = admin.ok(admin.post('/analytics/refresh', params={'period': 7}))
    assert report['metrika']['errors'] == [] and report['metrika']['sources'] and report['metrika']['engines']
    assert state['most'] <= yandex.METRIKA_PARALLEL and waits and set(waits) == {1.0}
