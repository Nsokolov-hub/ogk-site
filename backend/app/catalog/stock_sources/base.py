"""Small, conservative contract shared by public stock adapters."""

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

import httpx

from app.catalog.normalize import clean_spaces


class Refused(Exception):
    """Access was refused: stop this source, without retries or alternate access."""


class ParseChanged(ValueError):
    """The expected warehouse listing cannot be verified; never reconcile it as an empty warehouse."""


@dataclass
class Offer:
    external_id: str
    brand_name: str
    catalog_number: str
    name: str
    url: str
    cas: str | None = None
    pack: str | None = None
    quantity: int | None = None
    price: str | None = None
    # The supplier's declared update date, when present; fetching old news does not renew its stock evidence.
    stock_updated_at: datetime | None = None
    # Some public stock lists identify a substance but omit manufacturer/article. Keep their evidence private.
    review_only: bool = False


@dataclass
class Page:
    offers: list[Offer] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    truncated: int = 0
    # An adapter can preserve useful rows while declaring that the full warehouse was not checked.
    incomplete: str | None = None


def text(fragment: str) -> str:
    return clean_spaces(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)))


def check_answer(response: httpx.Response) -> httpx.Response:
    if response.status_code in (401, 403, 429, 451):
        raise Refused(f'{response.status_code}')
    head = response.text[:16000].lower()
    if ('captcha' in head and ('<form' in head or 'smartcaptcha' in head)) or \
            any(marker in head for marker in ('cf-chl-', 'challenge-platform', 'проверка браузера',
                                              'antibot-btn', 'sorry, your request has been denied', '/protect980/')):
        raise Refused('captcha')
    if 300 <= response.status_code < 400:
        raise Refused('redirect_requires_review')
    response.raise_for_status()
    return response


def _robot_path(value: str) -> str:
    # RFC 9309: compare URI octets; decode only percent-encoded unreserved ASCII, preserving reserved separators.
    def decode(match: re.Match[str]) -> str:
        char = chr(int(match.group(1), 16))
        return char if char.isascii() and (char.isalnum() or char in '-._~') else match.group(0).upper()

    return re.sub(r'%([0-9a-fA-F]{2})', decode,
                  quote(value, safe="/%?*-$&=:+;@!~'(),[]"))


class Robots:
    """Robots allow/disallow groups with longest matching path, wildcard and terminal-dollar support.

    Matching includes the literal query separator. In particular Disallow: /? blocks root queries rather than
    every path, and a longer Allow rule wins over a shorter Disallow. Only these access directives are relevant;
    sitemap, host and crawl-delay never turn a forbidden path into an allowed one.
    """

    def __init__(self, content: str, user_agent: str) -> None:
        groups: list[tuple[list[str], list[tuple[bool, str]]]] = []
        agents: list[str] = []
        rules: list[tuple[bool, str]] = []
        started_rules = False
        for line in content.splitlines():
            name, separator, value = line.split('#', 1)[0].partition(':')
            if not separator:
                continue
            name, value = name.strip().casefold(), value.strip()
            if name == 'user-agent':
                if started_rules:
                    groups.append((agents, rules))
                    agents, rules = [], []
                    started_rules = False
                agents.append(value.casefold())
            elif name in ('allow', 'disallow') and agents:
                started_rules = True
                if value:
                    rules.append((name == 'allow', _robot_path(value)))
        if agents:
            groups.append((agents, rules))
        candidates = [(max((len(a) for a in names if a != '*' and a in user_agent.casefold()), default=0),
                       '*' in names, lines) for names, lines in groups]
        longest = max((length for length, _wildcard, _lines in candidates), default=0)
        self.rules = [rule for length, wildcard, lines in candidates
                      if (length == longest if longest else wildcard) for rule in lines]

    def allowed(self, url: str) -> bool:
        parsed = urlsplit(url)
        target = _robot_path((parsed.path or '/') + (f'?{parsed.query}' if parsed.query else ''))
        matches: list[tuple[int, bool]] = []
        for allow, pattern in self.rules:
            terminal = pattern.endswith('$')
            body = pattern[:-1] if terminal else pattern
            regex = '^' + re.escape(body).replace(r'\*', '.*') + ('$' if terminal else '')
            if re.search(regex, target):
                matches.append((len(body.replace('*', '')), allow))
        return max(matches, default=(0, True))[1]


class PublicClient:
    """Restrict an adapter to its declared origin, public paths and current robots rules.

    Only canonical GET redirects (301/308) inside the declared public paths are followed, with robots checked
    again before every hop. A login wall, another host, robots refusal or captcha never triggers alternate access.
    """

    def __init__(self, client: httpx.Client, origin: str, user_agent: str, paths: list[str]) -> None:
        self.client = client
        self.origin = origin.rstrip('/')
        self.user_agent = user_agent
        self.paths = paths
        response = client.get(f'{self.origin}/robots.txt', follow_redirects=False)
        if response.status_code == 404:
            self.robots: Robots | None = None
        else:
            check_answer(response)
            if response.status_code != 200 or len(response.content) > 256000:
                raise Refused('robots_unavailable')
            if re.search(r'<(?:!doctype|html)\b', response.text[:1000], re.I):
                raise Refused('robots_unavailable')
            self.robots = Robots(response.text, user_agent)

    def _check_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if f'{parsed.scheme}://{parsed.netloc}'.rstrip('/') != self.origin or parsed.username or parsed.password:
            raise Refused('origin_not_allowed')
        if not any(parsed.path == path or path != '/' and parsed.path.startswith(path.rstrip('/') + '/')
                   for path in self.paths):
            raise Refused('path_not_allowed')
        if self.robots and not self.robots.allowed(url):
            raise Refused('robots_disallow')

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        request = self.client.build_request(method, url, **kwargs)
        visited: set[str] = set()
        for _ in range(5):
            current = str(request.url)
            self._check_url(current)
            if current in visited:
                raise Refused('redirect_loop')
            visited.add(current)
            response = self.client.send(request, follow_redirects=False)
            if method == 'GET' and response.status_code in (301, 308) and response.headers.get('location'):
                target = urljoin(current, response.headers['location'])
                self._check_url(target)  # Validate before making any further network request.
                request = self.client.build_request('GET', target)
                continue
            return check_answer(response)
        raise Refused('redirect_limit')

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self._request('GET', url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self._request('POST', url, **kwargs)
