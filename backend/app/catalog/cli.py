"""Catalog operations until the admin panel has them (ADM-03…06, ADM-10).

    python -m app.catalog.cli seed [--content-only]        — categories, brand pages, substances (+ test products)
    python -m app.catalog.cli recategorize [--all]         — categories by the rules for imported products
    python -m app.catalog.cli reindex                      — rebuild the search index without downtime
    python -m app.catalog.cli index                        — push queued products to the index now
    python -m app.catalog.cli import FILE… --source assortment [--brands …] [--dry-run] [--limit N]
    python -m app.catalog.cli batches                      — import journal
    python -m app.catalog.cli issues BATCH [--xlsx out.xlsx] — errors and conflicts of a batch
    python -m app.catalog.cli rollback BATCH               — undo a batch (IMP-06)
    python -m app.catalog.cli controlled FILE.xlsx|.json   — load the lists of controlled substances (TZ 5.2.1)
    python -m app.catalog.cli sync-brands                  — manufacturer registry from the CRM (flow F5)
    python -m app.catalog.cli misses [--days 30]           — top queries without results (SRCH-12)
    python -m app.catalog.cli setting KEY [JSON]           — read or change a catalog setting
    python -m app.catalog.cli indexnow-sitemap             — queue every Russian address of the Sitemap for IndexNow
    python -m app.catalog.cli cas-names FILE.json [--replace] — Russian names of CAS pages ({cas: name})
    python -m app.catalog.cli index-pilot --brands a,b [--limit N] [--undo] — open cards of these brands for indexing
"""

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.core.config import settings
from app.core.db import SessionLocal, utcnow


def _seed(args: argparse.Namespace) -> None:
    from app.catalog import seed
    from app.catalog.search import query

    if settings.environment == 'production' and not args.force and not args.content_only:
        raise SystemExit('Тестовые товары не загружаются в production: для структуры и текстов — --content-only')
    with SessionLocal.begin() as db:
        counts = seed.load(db, products_too=not args.content_only)
    query.reset_directory()
    print('Загружено: ' + ', '.join(f'{k} {v}' for k, v in counts.items()))
    _index(argparse.Namespace())
    _refresh_storefront()


def _recategorize(args: argparse.Namespace) -> None:
    from app.catalog.importer import run

    counts = run.recategorize(SessionLocal, only_missing=not args.all,
                              progress=lambda n: print(f'  {n}', file=sys.stderr))
    print(json.dumps(counts, ensure_ascii=False))
    _index(argparse.Namespace())
    _refresh_storefront()


def _refresh_storefront() -> None:
    """The storefront keeps API answers for a few minutes: drop them so the change is visible at once."""
    from app.core import storefront

    if storefront.revalidate_catalog():
        print('Кэш витрины сброшен')


def _index(_args: argparse.Namespace) -> None:
    from app.catalog.search import indexer
    from app.catalog.search.meili import engine

    with SessionLocal.begin() as db:
        indexer.configure(db, engine())
    total = 0
    while True:
        with SessionLocal.begin() as db:
            done = indexer.index_pending(db, engine())
        if not done:
            break
        total += done
    engine().wait()
    print(f'В индекс отправлено: {total}')


def _reindex(_args: argparse.Namespace) -> None:
    from app.catalog.search import indexer
    from app.catalog.search.meili import engine

    total = indexer.reindex_all(SessionLocal, engine(), progress=lambda n: print(f'  {n}', file=sys.stderr))
    print(f'Индекс перестроен: {total} документов')
    _refresh_storefront()


def _import(args: argparse.Namespace) -> None:
    from app.catalog.importer import run

    files = [Path(f) for f in args.files]
    for path in files:
        if not path.is_file():
            raise SystemExit(f'Нет файла: {path}')
    brands = [b.strip() for b in (args.brands or '').split(',') if b.strip()]
    result = run.import_files(SessionLocal, files, source=args.source, dry_run=args.dry_run, brands=brands,
                              limit=args.limit, progress=lambda n: print(f'  строк: {n}', file=sys.stderr))
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if not args.dry_run and not args.no_index:
        _index(argparse.Namespace())
    if not args.dry_run:
        _refresh_storefront()


def _batches(_args: argparse.Namespace) -> None:
    from app.catalog.models import ImportBatch, ImportSource

    with SessionLocal() as db:
        rows = db.execute(select(ImportBatch, ImportSource.code).join(ImportSource)
                          .order_by(ImportBatch.started_at.desc()).limit(30)).all()
        for batch, code in rows:
            counters = ', '.join(f'{k} {v}' for k, v in batch.counters.items())
            print(f'{batch.id}  {batch.started_at:%Y-%m-%d %H:%M}  {code:<12} {batch.status:<11} '
                  f'{"проверка " if batch.dry_run else ""}{batch.file_name}  {counters}')


def _issues(args: argparse.Namespace) -> None:
    from app.catalog.importer import run

    with SessionLocal() as db:
        if args.xlsx:
            count = run.export_issues(db, args.batch, Path(args.xlsx))
            print(f'Выгружено строк: {count} → {args.xlsx}')
            return
        for line in run.issue_summary(db, args.batch):
            print(line)


def _rollback(args: argparse.Namespace) -> None:
    from app.catalog.importer import run

    with SessionLocal.begin() as db:
        print(json.dumps(run.rollback(db, args.batch), ensure_ascii=False))
    _index(argparse.Namespace())
    _refresh_storefront()


def _controlled(args: argparse.Namespace) -> None:
    from app.catalog import controlled
    from app.catalog.importer import run

    entries = controlled.read_register(Path(args.file))
    with SessionLocal.begin() as db:
        count = controlled.load_register(db, entries)
        changed = run.recheck_controlled(db)
    print(f'Записей в перечнях: {count}; изменён признак у товаров: {changed}')
    _index(argparse.Namespace())
    _refresh_storefront()


def _sync_brands(_args: argparse.Namespace) -> None:
    from app.catalog import brands_sync

    print(json.dumps(brands_sync.sync(SessionLocal), ensure_ascii=False))
    _refresh_storefront()


def _cas_pages(_args: argparse.Namespace) -> None:
    from app.catalog import cas_pages

    print(json.dumps(cas_pages.build(SessionLocal), ensure_ascii=False))
    _refresh_storefront()


def _competitors(args: argparse.Namespace) -> None:
    from app.catalog import competitors

    if args.status:
        with SessionLocal() as db:
            print(json.dumps(competitors.status(db), ensure_ascii=False, default=str))
        return
    if not competitors.enabled():
        raise SystemExit('Проверка складов поставщиков выключена: COMPETITOR_STOCK_ENABLED=true в .env или продакшен')
    with SessionLocal.begin() as db:
        from app.catalog.settings import get_setting, set_setting

        if args.now and not get_setting(db, 'competitor_run'):
            results = get_setting(db, 'competitor_results') or {}
            set_setting(db, 'competitor_results', {**results, 'finishedAt': None})
    print(json.dumps(competitors.run_all(SessionLocal), ensure_ascii=False, default=str))
    _refresh_storefront()


def _indexnow_sitemap(_args: argparse.Namespace) -> None:
    import httpx

    from app.catalog import indexnow

    base = (settings.web_url or settings.site_url).rstrip('/')
    with httpx.Client(timeout=120) as client:
        paths = indexnow.sitemap_paths(client, f'{base}/sitemap.xml')
    with SessionLocal.begin() as db:
        added = indexnow.queue(db, paths)
    state = 'отправит воркер' if indexnow.enabled() else 'не отправляются: не production или нет ключа'
    print(f'В Sitemap {len(paths)} русских адресов, в очередь IndexNow добавлено {added} ({state}).')


def _cas_names(args: argparse.Namespace) -> None:
    from app.catalog.settings import get_setting, set_setting

    names = json.loads(Path(args.file).read_text(encoding='utf-8'))
    if not isinstance(names, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in names.items()):
        raise SystemExit('Нужен JSON-объект {"CAS": "Русское название"}')
    clean = {cas.strip(): name.strip() for cas, name in names.items() if cas.strip() and name.strip()}
    with SessionLocal.begin() as db:
        current = {} if args.replace else dict(get_setting(db, 'cas_names_ru') or {})
        current.update(clean)
        set_setting(db, 'cas_names_ru', current)
    print(f'Русских названий: {len(current)} (из файла {len(clean)}).')
    _refresh_storefront()


def _index_pilot(args: argparse.Namespace) -> None:
    from app.catalog import pilot

    slugs = [b.strip() for b in args.brands.split(',') if b.strip()]
    with SessionLocal.begin() as db:
        try:
            counts, queued = pilot.undo(db, slugs) if args.undo else pilot.open_cards(db, slugs, args.limit)
        except pilot.UnknownBrands as exc:
            raise SystemExit(str(exc)) from None
    action = 'Возвращено решению по полноте' if args.undo else 'Открыто для индексации'
    print(f'{action}: {sum(counts.values())} ' + json.dumps(counts, ensure_ascii=False) + f'; в очередь IndexNow: {queued}')
    _index(argparse.Namespace())
    _refresh_storefront()


def _misses(args: argparse.Namespace) -> None:
    from app.catalog.models import SearchMiss

    since = utcnow() - timedelta(days=args.days)
    with SessionLocal() as db:
        rows = db.execute(select(SearchMiss.query, SearchMiss.lang, func.sum(SearchMiss.count))
                          .where(SearchMiss.last_at >= since).group_by(SearchMiss.query, SearchMiss.lang)
                          .order_by(func.sum(SearchMiss.count).desc()).limit(args.limit)).all()
    for query, lang, count in rows:
        print(f'{count:>6}  {lang}  {query}')


def _setting(args: argparse.Namespace) -> None:
    from app.catalog.service import queue_all
    from app.catalog.settings import DEFAULTS, get_setting, set_setting

    if args.key not in DEFAULTS:
        raise SystemExit('Настройки: ' + ', '.join(DEFAULTS))
    with SessionLocal.begin() as db:
        if args.value is None:
            print(json.dumps(get_setting(db, args.key), ensure_ascii=False, indent=1))
            return
        set_setting(db, args.key, json.loads(args.value))
        if args.key in ('hide_controlled', 'index_threshold', 'completeness_weights'):
            from app.catalog.importer.run import refresh_all

            refresh_all(db)
            queue_all(db)
    print('Сохранено.')
    _refresh_storefront()


def main() -> None:
    import app.models  # noqa: F401
    from app.core.logs import configure_logging

    configure_logging()
    parser = argparse.ArgumentParser(description='Каталог сайта')
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('seed', help='структура каталога и тестовые товары')
    command.add_argument('--content-only', action='store_true', help='только категории, бренды и субстанции')
    command.add_argument('--force', action='store_true')
    command = commands.add_parser('recategorize', help='категории импортированных товаров по правилам')
    command.add_argument('--all', action='store_true', help='и у товаров, где категория уже есть')
    commands.add_parser('index', help='отправить очередь в индекс')
    commands.add_parser('reindex', help='перестроить индекс')
    command = commands.add_parser('import', help='импорт прайса')
    command.add_argument('files', nargs='+')
    command.add_argument('--source', default='assortment')
    command.add_argument('--brands', help='только эти производители, через запятую')
    command.add_argument('--limit', type=int, help='первые N строк')
    command.add_argument('--dry-run', action='store_true', help='предпросмотр без записи товаров')
    command.add_argument('--no-index', action='store_true', help='не отправлять в индекс сразу')
    commands.add_parser('batches', help='журнал партий')
    command = commands.add_parser('issues', help='ошибки и конфликты партии')
    command.add_argument('batch')
    command.add_argument('--xlsx')
    command = commands.add_parser('rollback', help='откатить партию')
    command.add_argument('batch')
    command = commands.add_parser('controlled', help='загрузить перечни подконтрольных веществ')
    command.add_argument('file')
    commands.add_parser('sync-brands', help='реестр производителей из CRM')
    commands.add_parser('cas-pages', help='страницы веществ по CAS из товаров каталога')
    command = commands.add_parser('misses', help='запросы без результатов')
    command.add_argument('--days', type=int, default=30)
    command.add_argument('--limit', type=int, default=50)
    command = commands.add_parser('setting', help='настройка каталога')
    command.add_argument('key')
    command.add_argument('value', nargs='?')
    commands.add_parser('indexnow-sitemap', help='все русские адреса Sitemap — в очередь IndexNow')
    command = commands.add_parser('cas-names', help='русские названия страниц CAS из JSON {cas: название}')
    command.add_argument('file')
    command.add_argument('--replace', action='store_true', help='заменить все, а не дополнить')
    command = commands.add_parser('competitors', help='наличие на складах Химмеда и Скайклада')
    command.add_argument('--now', action='store_true', help='не ждать срока, проверить сейчас')
    command.add_argument('--status', action='store_true', help='только показать последнюю проверку')
    command = commands.add_parser('index-pilot', help='открыть карточки брендов для индексации')
    command.add_argument('--brands', required=True, help='слаги брендов через запятую')
    command.add_argument('--limit', type=int, default=10000)
    command.add_argument('--undo', action='store_true', help='вернуть решение полноте карточки')
    args = parser.parse_args()
    handlers = {'seed': _seed, 'recategorize': _recategorize, 'index': _index, 'reindex': _reindex, 'import': _import, 'batches': _batches,
                'issues': _issues, 'rollback': _rollback, 'controlled': _controlled, 'sync-brands': _sync_brands,
                'cas-pages': _cas_pages, 'indexnow-sitemap': _indexnow_sitemap, 'cas-names': _cas_names,
                'index-pilot': _index_pilot, 'competitors': _competitors,
                'misses': _misses, 'setting': _setting}
    handlers[args.command](args)


if __name__ == '__main__':
    main()
