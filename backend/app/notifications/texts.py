"""Texts of the letters and alerts (RFQ-05, RFQ-07). Customer letters use the language of the request (EN-06)."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.requests.models import SiteRequest, SiteRequestAttachment, SiteRequestItem

KIND_RU = {'product_rfq': 'Запрос КП (корзина)', 'one_click': 'Заказ в 1 клик', 'service': 'Заявка на услугу',
           'general': 'Общая форма'}
ANALOGUE_RU = {'none': 'только этот товар', 'allowed': 'готовы рассмотреть аналоги', 'requested': 'подберите аналог'}
ANALOGUE_EN = {'none': 'this product only', 'allowed': 'analogues welcome', 'requested': 'please suggest an analogue'}
UNIT_RU = {'pack': 'уп.', 'mg': 'мг', 'g': 'г', 'ml': 'мл', 'pcs': 'шт.'}
UNIT_EN = {'pack': 'pack', 'mg': 'mg', 'g': 'g', 'ml': 'ml', 'pcs': 'pcs'}


def quantity(value: Decimal) -> str:
    return format(value.normalize(), 'f') if value == value.to_integral_value() else format(value, 'f').rstrip('0')


def item_lines(db: Session, row: SiteRequest, english: bool) -> list[str]:
    items = db.scalars(select(SiteRequestItem).where(SiteRequestItem.request_id == row.id)
                       .order_by(SiteRequestItem.position)).all()
    units, analogues = (UNIT_EN, ANALOGUE_EN) if english else (UNIT_RU, ANALOGUE_RU)
    lines = []
    for item in items:
        ids = ', '.join(part for part in (item.brand, item.catalog_number, f'CAS {item.cas}' if item.cas else None)
                        if part)
        packaging = f'{item.packaging} × ' if item.packaging else ''
        line = f'{item.position}. {item.name}' + (f' ({ids})' if ids else '')
        line += f' — {packaging}{quantity(item.quantity)} {units.get(item.unit, item.unit)}; {analogues[item.analogue]}'
        if item.comment:
            line += f'; {item.comment}'
        lines.append(line)
    return lines


def customer_letter(db: Session, row: SiteRequest) -> tuple[str, str]:
    english = row.lang == 'en'
    items = item_lines(db, row, english)
    if english:
        subject = f'Your request {row.number} — OGK-CHEM'
        body = [f'Dear {row.customer_name},', '',
                f'We have received your request {row.number}. A manager will contact you within 2 business hours '
                '(Mon–Fri, 9:00–18:00 Moscow time) with a quotation.']
        if items:
            body += ['', 'Items:', *items]
        body += ['', 'If you need to add something, just reply to this e-mail.', '', 'OGK-CHEM',
                 '+7 495 234 28 63 · order@ogk-chem.ru', settings.site_url]
    else:
        subject = f'Ваша заявка {row.number} — ОГК-ХИМ'
        body = [f'Здравствуйте, {row.customer_name}!', '',
                f'Мы получили вашу заявку {row.number}. Менеджер свяжется с вами в течение 2 рабочих часов '
                '(пн–пт, 9:00–18:00 по Москве) и подготовит коммерческое предложение.']
        if items:
            body += ['', 'Состав заявки:', *items]
        body += ['', 'Если нужно что-то добавить, просто ответьте на это письмо.', '', 'ОГК-ХИМ',
                 '+7 495 234 28 63 · order@ogk-chem.ru', settings.site_url]
    return subject, '\n'.join(body)


def full_content(db: Session, row: SiteRequest) -> list[str]:
    """Everything a manager needs to process the request without the CRM (sales letter and alert e-mail)."""
    files = db.scalars(select(SiteRequestAttachment).where(SiteRequestAttachment.request_id == row.id)).all()
    attribution = row.attribution or {}
    last = attribution.get('last_touch') or attribution.get('first_touch') or {}
    lines = [
        f'Номер: {row.number}', f'Тип: {KIND_RU.get(row.kind, row.kind)}', f'Язык: {row.lang}',
        f'Компания: {row.company}', f'ИНН: {row.inn or "—"}', f'Контакт: {row.customer_name}',
        f'Телефон: {row.phone}', f'E-mail: {row.email}', f'Город: {row.city or "—"}',
    ]
    if row.desired_date:
        lines.append(f'Желаемый срок: {row.desired_date:%d.%m.%Y}')
    if row.service:
        lines += ['', f'Услуга: {row.service.get("name")}']
        lines += [f'{key}: {value}' for key, value in (row.service.get('fields') or {}).items()]
    items = item_lines(db, row, False)
    if items:
        lines += ['', 'Позиции:', *items]
    if row.comment:
        lines += ['', 'Комментарий:', row.comment]
    if files:
        lines += ['', 'Вложения (переданы в CRM): ' + ', '.join(file.file_name for file in files)]
    lines += ['', f'Канал: {attribution.get("channel") or "—"}',
              f'Источник: {last.get("utm_source") or "—"} / {last.get("utm_medium") or "—"}'
              + (f' / {last["utm_campaign"]}' if last.get('utm_campaign') else ''),
              f'Страница: {row.page_url or "—"}']
    if row.suspicious:
        lines += ['', 'Внимание: заявка отмечена антиспамом как подозрительная.']
    return lines


def sales_letter(db: Session, row: SiteRequest) -> tuple[str, str]:
    subject = f'Заявка с сайта {row.number}: {row.company}'
    return subject, '\n'.join(['Новая заявка с сайта ogk-chem.ru.', '', *full_content(db, row)])


def alert_letter(db: Session, row: SiteRequest, reason: str) -> tuple[str, str]:
    subject = f'Заявка {row.number} не доставлена в CRM'
    body = [f'Заявка {row.number} не попала в CRM: {reason}.',
            f'Ошибка доставки: {row.delivery_error or "—"}.',
            'Обработайте её по этому письму. После восстановления CRM сайт доставит её сам; '
            'отклонённую CRM заявку отправьте повторно командой: python -m app.cli resend ' + row.number,
            '', *full_content(db, row)]
    return subject, '\n'.join(body)


def alert_message(row: SiteRequest, reason: str, attempts: int) -> str:
    # No names, phones or companies: see app.notifications.telegram.
    return (f'⚠️ Заявка {row.number} не доставлена в CRM: {reason}. Ошибка: {row.delivery_error or "—"}. '
            f'Попыток: {attempts}. Полный состав отправлен на {settings.alert_emails}.')
