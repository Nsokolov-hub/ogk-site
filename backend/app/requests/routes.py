"""Public endpoint of the site's forms (API contour /api/v1/public/*, TZ 12.2)."""

from typing import Any

from fastapi import APIRouter, Header, Request, Response
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.db import DB
from app.core.errors import DomainError
from app.requests.schemas import RequestOut
from app.requests.service import accept

router = APIRouter(tags=['Заявки'])


# The storefront keeps a trailing slash on every address (URL-01); both spellings reach the same handler.
@router.post('/public/requests/', status_code=201, response_model=RequestOut, include_in_schema=False)
@router.post('/public/requests', status_code=201, response_model=RequestOut, responses={
    200: {'description': 'Повтор с тем же Idempotency-Key: та же заявка', 'model': RequestOut},
    409: {'description': 'Ключ уже использован для другой заявки'},
    413: {'description': 'Файл больше 10 МБ'},
    422: {'description': 'Ошибки в полях формы: fields[].field — путь поля'},
    428: {'description': 'Нужна SmartCaptcha: повторите с captchaToken'},
    429: {'description': 'Слишком много заявок с адреса'},
})
async def submit_request(request: Request, response: Response, db: DB,
                         idempotency_key: str | None = Header(default=None)) -> dict[str, Any]:
    """Заявка с любой формы сайта: корзина, «Заказать в 1 клик», услуга, общая форма.

    multipart/form-data: часть `payload` — JSON `RequestIn`, необязательная часть `attachment` — файл XLSX, CSV,
    PDF или DOCX до 10 МБ. Заголовок `Idempotency-Key` — UUID, один на отправку формы."""
    form = await request.form(max_files=1, max_fields=5)
    part = form.get('payload')
    payload = part if isinstance(part, str) or part is None else (await part.read()).decode('utf-8', 'replace')
    upload = None
    attachment = form.get('attachment')
    if attachment is not None and not isinstance(attachment, str):
        content = await attachment.read(settings.max_attachment_bytes + 1)
        if len(content) > settings.max_attachment_bytes:
            raise DomainError('FILE_SIZE', 'Размер файла — не больше 10 МБ', 413, 'attachment')
        upload = (attachment.filename or '', content)
    ip = request.client.host if request.client else None
    answer, created = await run_in_threadpool(accept, db, payload, idempotency_key, upload, ip,
                                              request.headers.get('user-agent'), dict(request.cookies))
    if not created:
        response.status_code = 200
    return answer
