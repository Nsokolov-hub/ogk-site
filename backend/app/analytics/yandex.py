"""Yandex Metrica and Webmaster in the admin panel: one OAuth token of the account that owns the counter and the site.

An administrator pastes the token in «Настройки»; it is kept encrypted with SECRET_KEY (like the TOTP secrets) and
the API never sends it back, only its last four characters. Without it the server's METRIKA_OAUTH_TOKEN is used.
The same token uploads the offline conversions of the CRM (app.crm.conversions).

The worker fetches the reports once an hour for 7, 30 and 90 days (refresh_if_due); the admin panel reads that
snapshot. Each block is fetched on its own: a refused permission or a timeout leaves that block empty with a note,
the rest of the page still shows.
"""

import base64
import hashlib
import logging
import re
import threading
import time
from collections.abc import Callable, Hashable
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.catalog.settings import get_setting, set_setting
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import DomainError
from app.core.logs import event

logger = logging.getLogger(__name__)

METRIKA = 'https://api-metrika.yandex.net'
WEBMASTER = 'https://api.webmaster.yandex.net/v4'
PERIODS = (7, 30, 90)
EVERY = timedelta(hours=1)
TOP = 20
QUERIES = 50
# Metrica serves at most three requests of one user at a time and answers 429 to the rest.
METRIKA_PARALLEL = 2
RETRIES = 3
TOKEN_SHAPE = re.compile(r'[A-Za-z0-9_.\-]{20,300}')

# Events the site sends (src/lib/analytics.ts) and the stages of the CRM (app.crm.conversions.METRIKA_TARGETS):
# goals «JavaScript-событие» with these identifiers.
GOALS: list[tuple[str, str]] = [
    ('form_submit', 'Заявка: отправлена любая форма'),
    ('quote_request', 'Заявка: запрос КП из корзины'),
    ('product_request', 'Заявка: заказ в один клик'),
    ('add_to_rfq', 'Добавление позиции в запрос'),
    ('bulk_upload', 'Загрузка списка позиций'),
    ('click_phone', 'Клик по телефону'),
    ('click_email', 'Клик по почте'),
    ('download_document', 'Скачивание документа'),
    ('site_search', 'Поиск по сайту'),
    ('subscribe', 'Подписка на рассылку'),
    ('form_start', 'Начало заполнения формы'),
    ('crm_qualified', 'CRM: заявка взята в работу'),
    ('crm_proposal', 'CRM: отправлено КП'),
    ('crm_sale', 'CRM: продажа'),
]

SEVERITY = {'FATAL': 'Фатальная', 'CRITICAL': 'Критичная', 'POSSIBLE_PROBLEM': 'Возможная проблема',
            'RECOMMENDATION': 'Рекомендация'}
# Webmaster's diagnostics; an unknown code is shown as is.
PROBLEMS = {
    'CONNECTION_FAILED': 'Сайт недоступен для робота', 'DNS_ERROR': 'Ошибка DNS',
    'DISALLOWED_IN_ROBOTS': 'Сайт закрыт в robots.txt', 'ERROR_IN_ROBOTS_TXT': 'Ошибки в robots.txt',
    'NO_ROBOTS_TXT': 'Нет robots.txt', 'NO_SITEMAPS': 'Нет файлов Sitemap', 'ERRORS_IN_SITEMAPS': 'Ошибки в Sitemap',
    'NO_SITEMAP_MODIFICATIONS': 'Sitemap давно не обновлялся', 'SSL_CERTIFICATE_ERROR': 'Ошибка SSL-сертификата',
    'DOCUMENTS_MISSING_TITLE': 'Страницы без title', 'DOCUMENTS_MISSING_DESCRIPTION': 'Страницы без description',
    'NO_METRIKA_COUNTER_BINDING': 'Счётчик Метрики не привязан к сайту в Вебмастере',
    'NO_METRIKA_COUNTER_CRAWL_ENABLED': 'Обход по счётчику Метрики выключен',
    'SLOW_AVG_RESPONSE_TIME': 'Сайт медленно отвечает', 'MAIN_PAGE_ERROR': 'Главная страница отвечает ошибкой',
    'MAIN_PAGE_REDIRECTS': 'Главная страница перенаправляет', 'NO_REGIONS': 'Не указан регион сайта',
    'NOT_MOBILE_FRIENDLY': 'Сайт не оптимизирован для мобильных', 'BIG_FAVICON_ABSENT': 'Нет большого фавикона',
    'FAVICON_ERROR': 'Фавикон недоступен', 'INSIGNIFICANT_CGI_PARAMETER': 'Дубли из-за незначащих GET-параметров',
    'DUPLICATE_PAGES': 'Много дублей страниц', 'DUPLICATE_CONTENT_ATTRS': 'Одинаковые title и description',
    'URL_ALERT_4XX': 'Важные страницы отвечают 4xx', 'URL_ALERT_5XX': 'Важные страницы отвечают 5xx',
    'SOFT_404': 'Пустые страницы отвечают 200', 'DOMAIN_EXPIRES': 'Скоро истекает домен', 'THREATS': 'Угрозы безопасности',
    'HOST_COMPANY_PROFILE_NOT_FILLED': 'Не заполнен профиль организации', 'TOO_MANY_DOMAINS_ON_SEARCH': 'Много поддоменов в поиске',
}
# Why a page left the search (Webmaster «Исключённые страницы»).
EXCLUDED = {
    'HTTP_ERROR': 'Ответ с ошибкой HTTP', 'NOT_CANONICAL': 'Неканоническая: указан другой canonical',
    'DUPLICATE': 'Дубль другой страницы', 'LOW_QUALITY': 'Недостаточно качественная',
    'LOW_DEMAND': 'Маловостребованная', 'REDIRECT_NOTSEARCHABLE': 'Перенаправление',
    'REDIRECT_SEARCHABLE': 'Перенаправление', 'NO_INDEX': 'Запрещена noindex',
    'CONTAINS_NOINDEX_META_TAG': 'Запрещена noindex', 'CONTAINS_NOINDEX_X_ROBOTS_TAG_HEADER': 'Запрещена noindex',
    'FORBIDDEN_BY_ROBOTS_TXT': 'Запрещена в robots.txt', 'ROBOTS_URL_ERROR': 'Запрещена в robots.txt',
    'ROBOTS_HOST_ERROR': 'robots.txt был недоступен', 'HOST_ERROR': 'Сайт был недоступен',
    'CLEAN_PARAMS': 'Отброшены параметры', 'NOT_MAIN_MIRROR': 'Не главное зеркало',
    'PARSER_ERROR': 'Ошибка обработки страницы', 'NOTHING_FOUND': 'Страница не найдена',
    'SITEMAP_FORBIDDEN': 'Запрещена в Sitemap', 'SITEMAP_NOT_ALLOWED': 'Запрещена в Sitemap',
    'URL_NOT_ALLOWED': 'Адрес не разрешён', 'OTHER': 'Другая причина', 'UNKNOWN': 'Другая причина',
}


# ── the token ──

def _cipher() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(f'yandex:{settings.secret_key}'.encode()).digest()))


def token(db: Session) -> str:
    """The token of the admin panel, else the server's METRIKA_OAUTH_TOKEN; empty — not connected."""
    stored = get_setting(db, 'yandex_token') or {}
    if stored.get('cipher'):
        try:
            return _cipher().decrypt(str(stored['cipher']).encode()).decode()
        except InvalidToken:
            # SECRET_KEY changed: the token has to be pasted again.
            event(logger, 'yandex_token_unreadable', logging.WARNING)
    return settings.metrika_oauth_token


def counter(db: Session) -> str:
    from app.crm.conversions import counters

    return counters(db)[0]


def status(db: Session) -> dict[str, Any]:
    """What the admin panel shows about the connection; never the token itself."""
    stored = get_setting(db, 'yandex_token') or {}
    source = 'admin' if stored.get('cipher') else 'server' if settings.metrika_oauth_token else None
    reports = get_setting(db, 'yandex_reports') or {}
    return {'connected': source is not None, 'source': source, 'tail': stored.get('tail') if source == 'admin' else None,
            'login': stored.get('login'), 'savedAt': stored.get('savedAt'), 'savedBy': stored.get('savedBy'),
            'access': stored.get('access') or {}, 'counter': counter(db) or None,
            'refreshedAt': get_setting(db, 'yandex_reports_at'), 'tokenInvalid': bool(reports.get('tokenInvalid'))}


# ── calls to Yandex ──

class Refused(Exception):
    """Yandex said no: the message is for people, the code for the logs."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message

    def domain(self) -> DomainError:
        temporary = self.code in ('UNAVAILABLE', 'UNREACHABLE', 'RATE_LIMIT')
        return DomainError(f'YANDEX_{self.code}', self.message, 503 if temporary else 422)


def http_client() -> httpx.Client:
    """Replaced in tests with a client on a mock transport."""
    return httpx.Client(timeout=20)


def _refusal(response: httpx.Response) -> Refused:
    status_code = response.status_code
    try:
        data = response.json()
    except ValueError:
        data = {}
    detail = str((data.get('message') or data.get('error_message') or '') if isinstance(data, dict) else '')[:200]
    code = str(data.get('error_code') or '') if isinstance(data, dict) else ''
    host = response.request.url.host if response.request else ''
    if status_code == 401:
        return Refused('TOKEN_INVALID', 'Яндекс не принял токен: он отозван или истёк. Получите новый и вставьте '
                                        'в настройках')
    if status_code == 403 and host == urlsplit(METRIKA).hostname:
        return Refused('NO_ACCESS', 'Нет доступа к Метрике: в приложении Яндекса не отмечены права metrika:read и '
                                    'metrika:write или токен получен не под владельцем счётчика')
    if status_code == 403 and host == urlsplit(WEBMASTER).hostname:
        return Refused('NO_ACCESS', 'Нет доступа к Вебмастеру: в приложении Яндекса не отмечены права '
                                    'webmaster:hostinfo и webmaster:verify или токен получен не под владельцем сайта')
    if status_code == 403:
        return Refused('NO_ACCESS', 'Нет доступа: у приложения не отмечены нужные права или токен получен не под '
                                    'тем аккаунтом' + (f' ({detail})' if detail else ''))
    if status_code == 404 and (code == 'HOST_NOT_LOADED' or 'not loaded' in detail):
        # A site added to Webmaster a day or two ago: Yandex has not collected its data yet.
        return Refused('NOT_LOADED', 'Вебмастер ещё собирает данные о сайте: после добавления это занимает '
                                     'несколько дней. Отчёт появится сам')
    if status_code == 429:
        return Refused('RATE_LIMIT', 'Яндекс просит подождать: слишком много запросов. Попробуйте через час')
    if status_code >= 500:
        return Refused('UNAVAILABLE', 'Сервис Яндекса временно не отвечает')
    return Refused(f'HTTP_{status_code}', f'Яндекс ответил ошибкой {status_code}' + (f': {detail}' if detail else ''))


def pause(seconds: float) -> None:
    """Replaced in tests: a 429 is retried without waiting."""
    time.sleep(seconds)


class Api:
    def __init__(self, oauth: str, client: httpx.Client):
        self.client = client
        self.headers = {'Authorization': f'OAuth {oauth}'}
        self.metrika_slots = threading.BoundedSemaphore(METRIKA_PARALLEL)

    def call(self, method: str, url: str, **kwargs: Any) -> Any:
        for attempt in range(RETRIES):
            try:
                with self.metrika_slots if url.startswith(METRIKA) else nullcontext():
                    response = self.client.request(method, url, headers=self.headers, **kwargs)
            except httpx.HTTPError:
                raise Refused('UNREACHABLE', 'Сервис Яндекса не отвечает') from None
            # «Too many requests»: a moment later it is answered.
            if response.status_code == 429 and attempt < RETRIES - 1:
                pause(1.0 + attempt)
                continue
            break
        if response.status_code >= 300:
            raise _refusal(response)
        return response.json() if response.content else {}

    def get(self, url: str, **params: Any) -> Any:
        return self.call('GET', url, params=params or None)

    def post(self, url: str, body: dict[str, Any]) -> Any:
        return self.call('POST', url, json=body)


def _run(tasks: dict[Hashable, Callable[[], Any]]) -> tuple[dict[Hashable, Any], dict[Hashable, Refused]]:
    """Independent calls side by side; each failure is kept as a Refused under its key, the other results stay."""
    results: dict[Hashable, Any] = {}
    failures: dict[Hashable, Refused] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {key: pool.submit(task) for key, task in tasks.items()}
    for key, future in futures.items():
        try:
            results[key] = future.result()
        except Refused as exc:
            failures[key] = exc
        except Exception:
            logger.exception('{"event": "yandex_block_failed", "block": "%s"}', key)
            failures[key] = Refused('UNEXPECTED', 'Не удалось разобрать ответ Яндекса')
    return results, failures


def _messages(failures: list[Refused]) -> list[str]:
    return list(dict.fromkeys(f.message for f in failures))


def today() -> date:
    return datetime.now(ZoneInfo(settings.company_timezone)).date()


def span(days: int, end: date) -> tuple[date, date]:
    return end - timedelta(days=days - 1), end


def dates(period: tuple[date, date]) -> list[str]:
    return [(period[0] + timedelta(days=i)).isoformat() for i in range((period[1] - period[0]).days + 1)]


# ── Metrica ──

def stat(api: Api, ym: str, period: tuple[date, date], metrics: list[str], dimensions: str = '',
         **extra: Any) -> dict[str, Any]:
    params: dict[str, Any] = {'ids': ym, 'metrics': ','.join(metrics), 'date1': period[0].isoformat(),
                              'date2': period[1].isoformat(), 'accuracy': 'full', 'lang': 'ru', 'limit': TOP, **extra}
    if dimensions:
        params['dimensions'] = dimensions
    return api.get(f'{METRIKA}/stat/v1/data', **params)


def _dimension(row: dict[str, Any]) -> dict[str, Any]:
    return (row.get('dimensions') or [{}])[0] or {}


def metrika_goals(api: Api, ym: str) -> list[dict[str, Any]]:
    """Goals of the counter: id, name and, for JavaScript events, the identifier."""
    goals = api.get(f'{METRIKA}/management/v1/counter/{ym}/goals').get('goals') or []
    out = []
    for goal in goals:
        conditions = goal.get('conditions') or []
        identifier = conditions[0].get('url') if goal.get('type') == 'action' and conditions else None
        out.append({'id': goal['id'], 'name': goal.get('name') or '', 'identifier': identifier})
    return out


def metrika_period(api: Api, ym: str, period: tuple[date, date],
                   goals: list[dict[str, Any]]) -> dict[Hashable, Callable[[], Any]]:
    def overview() -> dict[str, Any]:
        data = stat(api, ym, period, ['ym:s:visits', 'ym:s:users', 'ym:s:pageviews', 'ym:s:bounceRate',
                                      'ym:s:avgVisitDurationSeconds'], 'ym:s:date', sort='ym:s:date', limit=400)
        t = list(data.get('totals') or []) + [0] * 5
        by_day = {_dimension(r).get('name'): r.get('metrics') or [0, 0] for r in data.get('data') or []}
        return {'totals': {'visits': int(t[0]), 'users': int(t[1]), 'pageviews': int(t[2]),
                           'bounceRate': round(float(t[3]), 1), 'duration': int(t[4])},
                'days': [{'date': d, 'visits': int(by_day.get(d, [0, 0])[0]), 'users': int(by_day.get(d, [0, 0])[1])}
                         for d in dates(period)]}

    def sources() -> list[dict[str, Any]]:
        data = stat(api, ym, period, ['ym:s:visits', 'ym:s:users'], 'ym:s:lastsignTrafficSource', sort='-ym:s:visits')
        return [{'key': _dimension(r).get('id'), 'name': _dimension(r).get('name') or '—',
                 'visits': int(r['metrics'][0]), 'users': int(r['metrics'][1])} for r in data.get('data') or []]

    def engines() -> list[dict[str, Any]]:
        data = stat(api, ym, period, ['ym:s:visits'], 'ym:s:lastsignSearchEngineRoot', sort='-ym:s:visits',
                    filters="ym:s:lastsignTrafficSource=='organic'", limit=10)
        return [{'name': _dimension(r).get('name') or '—', 'visits': int(r['metrics'][0])}
                for r in data.get('data') or []]

    def pages() -> list[dict[str, Any]]:
        data = stat(api, ym, period, ['ym:s:visits', 'ym:s:bounceRate'], 'ym:s:startURLPath', sort='-ym:s:visits')
        return [{'path': _dimension(r).get('name') or '—', 'visits': int(r['metrics'][0]),
                 'bounceRate': round(float(r['metrics'][1]), 1)} for r in data.get('data') or []]

    def reached() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        # Up to 20 metrics in one request: reaches and conversion of ten goals at a time.
        for start in range(0, len(goals), 10):
            chunk = goals[start:start + 10]
            metrics = [m for g in chunk for m in (f'ym:s:goal{g["id"]}reaches', f'ym:s:goal{g["id"]}conversionRate')]
            totals = list(stat(api, ym, period, metrics).get('totals') or []) + [0] * len(metrics)
            out += [{**g, 'reaches': int(totals[2 * i]), 'conversion': round(float(totals[2 * i + 1]), 2)}
                    for i, g in enumerate(chunk)]
        return out

    return {'overview': overview, 'sources': sources, 'engines': engines, 'pages': pages, 'goals': reached}


# ── Webmaster ──

def webmaster_host(api: Api) -> tuple[int, str, str]:
    """(user id, host id, address) of the site in the account's Webmaster."""
    uid = api.get(f'{WEBMASTER}/user')['user_id']
    hosts = api.get(f'{WEBMASTER}/user/{uid}/hosts').get('hosts') or []
    wanted = urlsplit(settings.site_url).hostname
    for host in hosts:
        if urlsplit(host.get('ascii_host_url') or '').hostname == wanted:
            if not host.get('verified'):
                raise Refused('NOT_VERIFIED', f'Права на {wanted} в Вебмастере не подтверждены')
            return uid, host['host_id'], host.get('ascii_host_url') or ''
    raise Refused('NO_HOST', f'Сайта {wanted} нет в Вебмастере этого аккаунта')


def _history(points: list[dict[str, Any]] | None) -> dict[str, float]:
    return {str(p.get('date') or '')[:10]: float(p.get('value') or 0) for p in points or []}


def webmaster_shared(api: Api, base: str) -> dict[Hashable, Callable[[], Any]]:
    def summary() -> dict[str, Any]:
        data = api.get(f'{base}/summary')
        return {'inSearch': int(data.get('searchable_pages_count') or 0),
                'excluded': int(data.get('excluded_pages_count') or 0), 'sqi': int(data.get('sqi') or 0),
                'problems': {k: int(v or 0) for k, v in (data.get('site_problems') or {}).items()}}

    def problems() -> list[dict[str, Any]]:
        found = (api.get(f'{base}/diagnostics').get('problems') or {}).items()
        order = list(SEVERITY)
        rows = [{'code': code, 'title': PROBLEMS.get(code, code), 'severity': p.get('severity'),
                 'severityTitle': SEVERITY.get(p.get('severity') or '', p.get('severity') or '')}
                for code, p in found if p.get('state') == 'PRESENT']
        return sorted(rows, key=lambda r: order.index(r['severity']) if r['severity'] in order else len(order))

    def sitemaps() -> list[dict[str, Any]]:
        known = api.get(f'{base}/sitemaps').get('sitemaps') or []
        added = {s.get('sitemap_url') for s in api.get(f'{base}/user-added-sitemaps').get('sitemaps') or []}
        rows = [{'url': s.get('sitemap_url'), 'urls': int(s.get('urls_count') or 0),
                 'errors': int(s.get('errors_count') or 0), 'children': int(s.get('children_count') or 0),
                 'lastAccess': s.get('last_access_date'), 'added': s.get('sitemap_url') in added} for s in known]
        rows += [{'url': url, 'urls': 0, 'errors': 0, 'children': 0, 'lastAccess': None, 'added': True}
                 for url in sorted(u for u in added if u and u not in {r['url'] for r in rows})]
        return rows

    def removed() -> list[dict[str, Any]]:
        samples = api.get(f'{base}/search-urls/events/samples', offset=0, limit=100).get('samples') or []
        groups: dict[str, dict[str, Any]] = {}
        for s in samples:
            if s.get('event') != 'REMOVED_FROM_SEARCH':
                continue
            reason = str(s.get('excluded_url_status') or 'UNKNOWN')
            title = EXCLUDED.get(reason, reason)
            group = groups.setdefault(title, {'title': title, 'count': 0, 'examples': []})
            group['count'] += 1
            if len(group['examples']) < 5:
                group['examples'].append(s.get('url'))
        return sorted(groups.values(), key=lambda g: -g['count'])

    return {'summary': summary, 'problems': problems, 'sitemaps': sitemaps, 'removed': removed}


def webmaster_period(api: Api, base: str, period: tuple[date, date]) -> dict[Hashable, Callable[[], Any]]:
    window = {'date_from': period[0].isoformat(), 'date_to': period[1].isoformat()}

    def queries() -> list[dict[str, Any]]:
        data = api.get(f'{base}/search-queries/popular', order_by='TOTAL_SHOWS', limit=QUERIES,
                       query_indicator=['TOTAL_SHOWS', 'TOTAL_CLICKS', 'AVG_SHOW_POSITION'], **window)
        rows = []
        for q in data.get('queries') or []:
            values = q.get('indicators') or {}
            rows.append({'text': q.get('query_text') or '', 'shows': int(values.get('TOTAL_SHOWS') or 0),
                         'clicks': int(values.get('TOTAL_CLICKS') or 0),
                         'position': round(float(values.get('AVG_SHOW_POSITION') or 0), 1)})
        return rows

    def query_days() -> dict[str, Any]:
        data = api.get(f'{base}/search-queries/all/history', query_indicator=['TOTAL_SHOWS', 'TOTAL_CLICKS'],
                       **window)
        values = data.get('indicators') or {}
        shows, clicks = _history(values.get('TOTAL_SHOWS')), _history(values.get('TOTAL_CLICKS'))
        days = [{'date': d, 'shows': int(shows.get(d, 0)), 'clicks': int(clicks.get(d, 0))} for d in dates(period)]
        return {'shows': sum(d['shows'] for d in days), 'clicks': sum(d['clicks'] for d in days), 'days': days}

    def in_search() -> list[dict[str, Any]]:
        points = _history(api.get(f'{base}/search-urls/in-search/history', **window).get('history'))
        # Webmaster counts pages in search every few days: carry the last known value over the gaps.
        out, last = [], None
        for d in dates(period):
            last = int(points[d]) if d in points else last
            out.append({'date': d, 'value': last})
        return out

    def crawled() -> dict[str, int]:
        values = api.get(f'{base}/indexing/history', **window).get('indicators') or {}
        total = {k: int(sum(_history(v).values())) for k, v in values.items()}
        return {'ok': total.get('HTTP_2XX', 0), 'redirect': total.get('HTTP_3XX', 0),
                'notFound': total.get('HTTP_4XX', 0), 'error': total.get('HTTP_5XX', 0) + total.get('OTHER', 0)}

    return {'queries': queries, 'queryTotals': query_days, 'inSearch': in_search, 'crawled': crawled}


# ── the snapshot ──

def fetch(oauth: str, ym: str, end: date | None = None) -> dict[str, Any]:
    """All the reports of every period in one snapshot."""
    end = end or today()
    with http_client() as client:
        api = Api(oauth, client)
        first, failed = _run({'goals': (lambda: metrika_goals(api, ym)) if ym else (lambda: None),
                              'host': lambda: webmaster_host(api)})
        goals = first.get('goals') or []
        host = first.get('host')
        tasks: dict[Hashable, Callable[[], Any]] = {}
        if ym and 'goals' in first:
            for days in PERIODS:
                for name, task in metrika_period(api, ym, span(days, end), goals).items():
                    tasks[('metrika', days, name)] = task
        if host:
            base = f'{WEBMASTER}/user/{host[0]}/hosts/{host[1]}'
            for name, task in webmaster_shared(api, base).items():
                tasks[('webmaster', 0, name)] = task
            for days in PERIODS:
                for name, task in webmaster_period(api, base, span(days, end)).items():
                    tasks[('webmaster', days, name)] = task
        results, later = _run(tasks)
    failed.update(later)

    def system(key: Hashable) -> str:
        if key == 'goals':
            return 'metrika'
        if key == 'host':
            return 'webmaster'
        return str(key[0]) if isinstance(key, tuple) else ''

    def blocks(name: str, days: int) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in results.items():
            if isinstance(key, tuple) and key[0] == name and key[1] == days:
                if key[2] == 'overview':  # one request gives the totals and the days
                    out.update(value)
                else:
                    out[str(key[2])] = value
        return out

    metrika_errors = _messages([f for k, f in failed.items() if system(k) == 'metrika'])
    webmaster_errors = _messages([f for k, f in failed.items() if system(k) == 'webmaster'])
    if not ym:
        metrika_errors.insert(0, 'Не задан номер счётчика Метрики')
    present = {g['identifier'] for g in goals if g.get('identifier')}
    return {
        'fetchedAt': utcnow().isoformat(),
        'tokenInvalid': any(f.code == 'TOKEN_INVALID' for f in failed.values()),
        'metrika': {'counter': ym or None, 'errors': metrika_errors,
                    'missingGoals': [i for i, _ in GOALS if i not in present] if 'goals' in first and ym else [],
                    'periods': {str(days): blocks('metrika', days) for days in PERIODS}},
        'webmaster': {'host': host[2] if host else None, 'errors': webmaster_errors, **blocks('webmaster', 0),
                      'periods': {str(days): blocks('webmaster', days) for days in PERIODS}},
    }


def refresh(db: Session) -> dict[str, Any] | None:
    """Fetch the snapshot and keep it; None — no token."""
    oauth, ym = token(db), counter(db)
    if not oauth:
        return None
    data = fetch(oauth, ym)
    set_setting(db, 'yandex_reports', data)
    set_setting(db, 'yandex_reports_at', data['fetchedAt'])
    event(logger, 'yandex_reports_fetched', metrika_errors=len(data['metrika']['errors']),
          webmaster_errors=len(data['webmaster']['errors']))
    return data


def due(db: Session, now: datetime | None = None) -> bool:
    if not token(db):
        return False
    last = get_setting(db, 'yandex_reports_at')
    return not last or (now or utcnow()) - datetime.fromisoformat(last) >= EVERY


def report(db: Session, days: int) -> dict[str, Any]:
    """The admin panel's page: the connection and the snapshot of one period."""
    data = get_setting(db, 'yandex_reports') or {}
    out: dict[str, Any] = {'status': status(db), 'period': days, 'fetchedAt': data.get('fetchedAt'),
                           'metrika': None, 'webmaster': None}
    for name in ('metrika', 'webmaster'):
        part = data.get(name)
        if part:
            periods = part.get('periods') or {}
            out[name] = {**{k: v for k, v in part.items() if k != 'periods'}, **(periods.get(str(days)) or {})}
    return out


# ── what the administrator does ──

def _access(check: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return {'ok': True, **check()}
    except Refused as exc:
        return {'ok': False, 'error': exc.message}


def connect(db: Session, raw: str, author: str) -> dict[str, Any]:
    """Check the pasted token against both services and keep it; it is refused only if neither accepts it."""
    value = raw.strip()
    if value.lower().startswith('oauth '):
        value = value[6:].strip()
    if not TOKEN_SHAPE.fullmatch(value):
        raise DomainError('TOKEN_INVALID', 'Это не похоже на токен Яндекса: длинная строка без пробелов, обычно '
                                           'начинается на y0_', 422, 'token')
    ym = counter(db)

    def metrika() -> dict[str, Any]:
        if not ym:
            raise Refused('NO_COUNTER', 'Не задан номер счётчика Метрики')
        found = api.get(f'{METRIKA}/management/v1/counter/{ym}').get('counter') or {}
        return {'name': found.get('name'), 'login': found.get('owner_login'), 'permission': found.get('permission')}

    def webmaster() -> dict[str, Any]:
        return {'host': webmaster_host(api)[2]}

    with http_client() as client:
        api = Api(value, client)
        access = {'metrika': _access(metrika), 'webmaster': _access(webmaster)}
    if not (access['metrika']['ok'] or access['webmaster']['ok']):
        raise DomainError('TOKEN_REFUSED', f'Метрика: {access["metrika"]["error"]} Вебмастер: '
                                           f'{access["webmaster"]["error"]}', 422, 'token')
    set_setting(db, 'yandex_token', {'cipher': _cipher().encrypt(value.encode()).decode(), 'tail': value[-4:],
                                     'login': access['metrika'].get('login'), 'savedAt': utcnow().isoformat(),
                                     'savedBy': author, 'access': access})
    # The worker fetches the reports with the new token within a minute.
    set_setting(db, 'yandex_reports_at', None)
    return access


def disconnect(db: Session) -> None:
    set_setting(db, 'yandex_token', None)
    set_setting(db, 'yandex_reports', {})
    set_setting(db, 'yandex_reports_at', None)


def _connected(db: Session) -> tuple[str, str]:
    oauth = token(db)
    if not oauth:
        raise DomainError('YANDEX_NOT_CONNECTED', 'Сначала подключите Яндекс в настройках', 409)
    return oauth, counter(db)


def ensure_goals(db: Session) -> list[dict[str, Any]]:
    """Goals of GOALS the counter does not have yet; the existing ones are left as they are."""
    oauth, ym = _connected(db)
    if not ym:
        raise DomainError('YANDEX_NO_COUNTER', 'Не задан номер счётчика Метрики', 409)
    out = []
    with http_client() as client:
        api = Api(oauth, client)
        try:
            existing = {g['identifier']: g['name'] for g in metrika_goals(api, ym) if g['identifier']}
        except Refused as exc:
            raise exc.domain() from None
        for identifier, name in GOALS:
            if identifier in existing:
                out.append({'identifier': identifier, 'name': existing[identifier], 'state': 'exists'})
                continue
            goal = {'name': name, 'type': 'action', 'conditions': [{'type': 'exact', 'url': identifier}]}
            try:
                api.post(f'{METRIKA}/management/v1/counter/{ym}/goals', {'goal': goal})
                out.append({'identifier': identifier, 'name': name, 'state': 'created'})
            except Refused as exc:
                out.append({'identifier': identifier, 'name': name, 'state': 'error', 'error': exc.message})
    set_setting(db, 'yandex_reports_at', None)
    return out


def add_sitemap(db: Session) -> dict[str, Any]:
    """The site's sitemap index in Webmaster («Файлы Sitemap»), once."""
    oauth, _ = _connected(db)
    url = f'{settings.site_url.rstrip("/")}/sitemap.xml'
    with http_client() as client:
        api = Api(oauth, client)
        try:
            uid, host, _address = webmaster_host(api)
            base = f'{WEBMASTER}/user/{uid}/hosts/{host}/user-added-sitemaps'
            added = {s.get('sitemap_url') for s in api.get(base).get('sitemaps') or []}
            if url in added:
                return {'url': url, 'state': 'exists'}
            api.post(base, {'url': url})
        except Refused as exc:
            raise exc.domain() from None
    set_setting(db, 'yandex_reports_at', None)
    return {'url': url, 'state': 'added'}
