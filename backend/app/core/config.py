from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    environment: str = 'development'
    database_url: str = 'postgresql+psycopg://site:site@127.0.0.1:54330/site'
    site_url: str = 'https://www.ogk-chem.ru'
    # Private storage of customer attachments until they are delivered to the CRM.
    storage_dir: Path = Path('.runtime/files')
    max_attachment_bytes: int = 10 * 1024 * 1024
    company_timezone: str = 'Europe/Moscow'

    # ── CRM, flow F1 (my-crm-project docs/site-integration.md) ──
    crm_url: str = ''
    crm_token: str = ''
    crm_signing_secret: str = ''
    # False keeps requests in the queue (they are still saved and mailed to sales): the CRM module is not ready
    # yet, or the CRM is being maintained. Undelivered alerts are off while delivery is off.
    crm_delivery_enabled: bool = False
    crm_timeout_seconds: float = 15.0

    # ── search (TZ 6): Meilisearch behind app.catalog.search, rebuilt from PostgreSQL ──
    meili_url: str = 'http://127.0.0.1:7700'
    meili_key: str = 'development-master-key-0123456789'
    meili_index: str = 'products'
    search_timeout_seconds: float = 5.0
    # Requests to the search API from one address per minute (NFR-05); deeper pages are refused.
    search_rate_per_minute: int = 120
    search_max_page: int = 200
    # Shared limits of all API processes; empty — counted in each process.
    redis_url: str = ''

    # ── storefront cache: the worker drops ISR pages of changed products ──
    web_url: str = ''
    # Shared secret of the storefront and the API: cache drops, and the storefront's cached requests are not
    # counted against the search limits.
    revalidate_secret: str = ''

    # ── error reports (Sentry or GlitchTip, TZ 12.1); empty — only the logs ──
    sentry_dsn: str = ''

    # ── admin panel (TZ 13) ──
    # Encrypts TOTP secrets and signs preview links; in production a random string of at least 32 characters.
    secret_key: str = 'development-secret-key-change-me-0123456789'
    # Address of the admin panel: the only origin allowed to change data, and the base of its links.
    admin_url: str = 'http://127.0.0.1:5174'
    admin_session_hours: int = 12
    # Administrators must turn on a second factor before they can work (ADM-01); on outside development.
    require_totp: bool | None = None

    @property
    def totp_required(self) -> bool:
        return self.require_totp if self.require_totp is not None else self.environment != 'development'

    # ── mail ──
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_password: str = ''
    smtp_starttls: bool = True
    mail_from: str = 'ОГК-ХИМ <noreply@ogk-chem.ru>'
    mail_reply_to: str = 'order@ogk-chem.ru'
    sales_email: str = 'order@ogk-chem.ru'
    # Full content of undelivered requests goes here (comma-separated); Telegram gets no personal data.
    alert_emails: str = 'order@ogk-chem.ru'

    # ── alerts ──
    telegram_bot_token: str = ''
    telegram_chat_id: str = ''
    alert_after_minutes: int = 15

    # ── antispam (RFQ-06) ──
    min_fill_ms: int = 3000
    # Soft limit: above it a request needs SmartCaptcha; hard limit: refused for the window.
    rate_soft_limit: int = 5
    rate_soft_window_minutes: int = 10
    rate_hard_limit: int = 20
    rate_hard_window_minutes: int = 60
    smartcaptcha_server_key: str = ''

    def verify(self) -> None:
        if self.environment == 'production':
            if not self.database_url.startswith('postgresql'):
                raise RuntimeError('Production requires PostgreSQL')
            if self.crm_delivery_enabled and not (self.crm_url and self.crm_token and self.crm_signing_secret):
                raise RuntimeError('CRM_DELIVERY_ENABLED needs CRM_URL, CRM_TOKEN and CRM_SIGNING_SECRET')
        if self.environment in ('production', 'staging') and (
                len(self.secret_key) < 32 or self.secret_key.startswith('development-')):
            raise RuntimeError('SECRET_KEY: a random string of at least 32 characters (scripts/init-env.py)')


settings = Settings()
settings.verify()
