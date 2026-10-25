"""Load test of the site (NFR-01): mixed traffic at a fixed rate, percentiles per kind of page.

    python scripts/load_test.py --base https://staging.ogk-chem.ru --rps 50 --duration 300 [--auth user:password]

Pages are taken from the live catalog: categories from the tree, products and catalog numbers from listings, so
most product pages and filtered listings are not in any cache. Targets of the TZ: pages without cache p95 ≤ 800 ms,
API p95 ≤ 300 ms, no errors. Before the test raise SEARCH_RATE_PER_MINUTE on the server: the whole test comes
from one address and the per-visitor limit of search would answer 429 (they are counted apart).
"""

import argparse
import asyncio
import random
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field

import httpx

# Share of each kind in the traffic; pages are rendered by the storefront, api — answers of the API itself.
MIX = {'home': 8, 'category': 22, 'category_filtered': 10, 'product': 35, 'search_page': 7, 'suggest': 15,
       'api_listing': 3}
PAGE_TARGET_MS = 800
API_TARGET_MS = 300
API_KINDS = {'suggest', 'api_listing'}


@dataclass
class Pool:
    categories: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)
    brands: dict[str, list[str]] = field(default_factory=dict)


async def build_pool(client: httpx.AsyncClient, pages: int) -> Pool:
    pool = Pool()
    tree = (await client.get('/api/v1/public/catalog/tree')).raise_for_status().json()
    pool.categories = [node['path'] for node in tree]
    for path in pool.categories:
        for page in range(1, pages + 1):
            answer = await client.get('/api/v1/public/catalog/listing',
                                      params={'path': path, 'page': page, 'pageSize': 48, 'facets': 'brand'})
            if answer.status_code != 200:
                break
            data = answer.json()
            for item in data['items']:
                pool.products.append(item['slug'])
                pool.numbers.append(item['catalogNumber'])
            for facet in data.get('facets', []):
                if facet.get('key') == 'brand':
                    pool.brands[path] = [v['value'] for v in facet.get('values', [])][:20]
            if page >= data.get('pageCount', 1):
                break
    if not pool.products:
        sys.exit('Каталог пуст: загрузите товары перед тестом')
    return pool


def pick(kind: str, pool: Pool) -> str:
    if kind == 'home':
        return '/'
    if kind == 'category':
        path = random.choice(pool.categories)
        return f'/catalog/{path}/' + (f'?page={random.randint(2, 20)}' if random.random() < 0.4 else '')
    if kind == 'category_filtered':
        path = random.choice(pool.categories)
        brands = pool.brands.get(path) or ['']
        return f'/catalog/{path}/?brand={random.choice(brands)}&sort=name'
    if kind == 'product':
        return f'/product/{random.choice(pool.products)}/'
    number = random.choice(pool.numbers)
    if kind == 'search_page':
        return f'/search/?q={number}'
    if kind == 'suggest':
        return f'/api/search/suggest/?q={number[: random.randint(3, len(number))]}&lang=ru'
    path = random.choice(pool.categories)
    return f'/api/v1/public/catalog/listing?path={path}&page={random.randint(1, 50)}'


async def run(args: argparse.Namespace) -> int:
    auth = tuple(args.auth.split(':', 1)) if args.auth else None
    limits = httpx.Limits(max_connections=args.concurrency, max_keepalive_connections=args.concurrency)
    async with httpx.AsyncClient(base_url=args.base.rstrip('/'), auth=auth, timeout=30, limits=limits,  # type: ignore[arg-type]
                                 follow_redirects=False, headers={'User-Agent': 'ogk-load-test'}) as client:
        pool = await build_pool(client, args.pages)
        print(f'Пул: {len(pool.categories)} разделов, {len(pool.products)} товаров')
        kinds = list(MIX)
        weights = [MIX[k] for k in kinds]
        times: dict[str, list[float]] = defaultdict(list)
        errors: dict[str, dict[int | str, int]] = defaultdict(lambda: defaultdict(int))
        semaphore = asyncio.Semaphore(args.concurrency)
        tasks: list[asyncio.Task[None]] = []

        async def one(kind: str, url: str) -> None:
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(url)
                    elapsed = (time.perf_counter() - started) * 1000
                    if response.status_code == 200:
                        times[kind].append(elapsed)
                    else:
                        errors[kind][response.status_code] += 1
                except httpx.HTTPError as exc:
                    errors[kind][type(exc).__name__] += 1

        started = time.perf_counter()
        total = int(args.rps * args.duration)
        for i in range(total):
            # Open model: requests start on schedule whatever the answers do.
            delay = started + i / args.rps - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            kind = random.choices(kinds, weights)[0]
            tasks.append(asyncio.create_task(one(kind, pick(kind, pool))))
        await asyncio.gather(*tasks)
        wall = time.perf_counter() - started

    print(f'\nЗапросов: {total} за {wall:.0f} с — {total / wall:.1f} в секунду\n')
    print(f'{"вид":<18}{"ок":>7}{"ошибки":>9}{"p50":>8}{"p95":>8}{"p99":>8}  цель')
    failed = False
    for kind in kinds:
        values = sorted(times[kind])
        bad = sum(errors[kind].values())
        target = API_TARGET_MS if kind in API_KINDS else PAGE_TARGET_MS
        if values:
            p50 = statistics.median(values)
            p95 = values[min(len(values) - 1, int(len(values) * 0.95))]
            p99 = values[min(len(values) - 1, int(len(values) * 0.99))]
            ok = p95 <= target and bad == 0
            failed |= not ok
            print(f'{kind:<18}{len(values):>7}{bad:>9}{p50:>8.0f}{p95:>8.0f}{p99:>8.0f}  ≤ {target} {"✓" if ok else "✗"}')
        else:
            failed = True
            print(f'{kind:<18}{0:>7}{bad:>9}')
        if bad:
            print(f'{"":<18}  ошибки: {dict(errors[kind])}')
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description='Нагрузочный тест сайта (NFR-01)')
    parser.add_argument('--base', required=True, help='адрес сайта, например https://staging.ogk-chem.ru')
    parser.add_argument('--rps', type=float, default=50)
    parser.add_argument('--duration', type=float, default=300, help='секунды')
    parser.add_argument('--concurrency', type=int, default=200)
    parser.add_argument('--pages', type=int, default=10, help='страниц каждого раздела для пула товаров')
    parser.add_argument('--auth', help='пароль стейджа: пользователь:пароль')
    sys.exit(asyncio.run(run(parser.parse_args())))


if __name__ == '__main__':
    main()
