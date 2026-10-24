"""Letters over SMTP (a provider with servers in Russia, TZ 12.1). Without SMTP_HOST letters are only logged."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

from app.core.config import settings
from app.core.logs import event

logger = logging.getLogger('site.mail')


class MailUnavailable(Exception):
    """The mail server refused or did not answer; the worker retries the letter later."""


def send(to: list[str], subject: str, body: str, *, reply_to: str | None = None) -> None:
    recipients = [address.strip() for address in to if address.strip()]
    if not recipients:
        return
    if not settings.smtp_host:
        event(logger, 'mail_skipped', subject=subject, recipients=len(recipients))
        return
    message = EmailMessage()
    message['From'] = settings.mail_from
    message['To'] = ', '.join(recipients)
    message['Subject'] = subject
    message['Message-ID'] = make_msgid(domain=settings.mail_from.split('@')[-1].rstrip('>') or None)
    if reply_to:
        message['Reply-To'] = reply_to
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailUnavailable(type(exc).__name__) from None
    event(logger, 'mail_sent', subject=subject, recipients=len(recipients))
