"""Public API of the site's forms: POST /api/v1/public/requests.

Field names are camelCase, as the storefront already builds them (web src/types/requests.ts); the checks repeat
the forms' own (web src/lib/validation.ts), because a bot posts here without the forms.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

Kind = Literal['product_rfq', 'one_click', 'service', 'general']
Analogue = Literal['none', 'allowed', 'requested']
Unit = Literal['pack', 'mg', 'g', 'ml', 'pcs']

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$')
E164_RE = re.compile(r'^\+[1-9][0-9]{6,14}$')


def valid_inn(value: str) -> bool:
    """INN of a company (10 digits) or of a person (12) with its check digits (RFQ-03)."""
    if not re.fullmatch(r'[0-9]{10}|[0-9]{12}', value):
        return False
    digits = [int(char) for char in value]

    def check(weights: list[int]) -> int:
        return sum(w * d for w, d in zip(weights, digits, strict=False)) % 11 % 10

    if len(digits) == 10:
        return check([2, 4, 10, 3, 5, 9, 4, 6, 8]) == digits[9]
    return (check([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == digits[10]
            and check([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == digits[11])


def blank_to_none(value: object) -> object:
    return None if isinstance(value, str) and not value.strip() else value


class CamelModel(BaseModel):
    # Unknown fields are ignored so a storefront deployed before the API does not break submissions.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra='ignore',
                              str_strip_whitespace=True)


class CustomerIn(CamelModel):
    name: str = Field(min_length=2, max_length=200)
    company: str = Field(min_length=2, max_length=250)
    phone: str = Field(max_length=20, description='E.164: +79991234567')
    email: str = Field(max_length=254)
    inn: str | None = Field(default=None, max_length=12)
    city: str | None = Field(default=None, max_length=200)
    comment: str | None = Field(default=None, max_length=5000)
    marketing_consent: bool = False

    _blank = field_validator('inn', 'city', 'comment', mode='before')(blank_to_none)

    @field_validator('phone')
    @classmethod
    def phone_e164(cls, value: str) -> str:
        if not E164_RE.fullmatch(value) or (value.startswith('+7') and len(value) != 12):
            raise ValueError('phone')
        return value

    @field_validator('email')
    @classmethod
    def email_shape(cls, value: str) -> str:
        if not EMAIL_RE.fullmatch(value):
            raise ValueError('email')
        return value

    @field_validator('inn')
    @classmethod
    def inn_checksum(cls, value: str | None) -> str | None:
        if value is not None:
            value = re.sub(r'\s', '', value)
            if not valid_inn(value):
                raise ValueError('inn')
        return value


class ItemIn(CamelModel):
    site_product_id: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=200)
    catalog_number: str | None = Field(default=None, max_length=150)
    cas: str | None = Field(default=None, max_length=30)
    name: str = Field(min_length=1, max_length=500)
    packaging: str | None = Field(default=None, max_length=200)
    quantity: Decimal = Field(gt=0, le=Decimal(100000), max_digits=12, decimal_places=3)
    unit: Unit = 'pack'
    analogue: Analogue = 'none'
    custom_packaging: bool = False
    comment: str | None = Field(default=None, max_length=2000)
    page_url: str | None = Field(default=None, max_length=2000)

    _blank = field_validator('site_product_id', 'brand', 'catalog_number', 'cas', 'packaging', 'comment',
                             'page_url', mode='before')(blank_to_none)


class ServiceIn(CamelModel):
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=250)
    fields: dict[str, str] = Field(default_factory=dict, max_length=30)

    @field_validator('fields')
    @classmethod
    def short_values(cls, value: dict[str, str]) -> dict[str, str]:
        if any(len(key) > 200 or len(item) > 2000 for key, item in value.items()):
            raise ValueError('Слишком длинное значение поля')
        return value


class AntispamIn(CamelModel):
    # The trap field: always empty for a person.
    website: str = ''
    elapsed_ms: int = Field(default=0, ge=0)


class RequestIn(CamelModel):
    kind: Kind
    lang: Literal['ru', 'en'] = 'ru'
    form_type: str | None = Field(default=None, max_length=40)
    customer: CustomerIn
    items: list[ItemIn] = Field(default_factory=list, max_length=200)
    personal_data_consent: Literal[True]
    antispam: AntispamIn = Field(default_factory=AntispamIn)
    page_url: str | None = Field(default=None, max_length=2000)
    desired_date: date | None = None
    service: ServiceIn | None = None
    # Yandex SmartCaptcha token, sent again after a 428 CAPTCHA_REQUIRED answer.
    captcha_token: str | None = Field(default=None, max_length=4000)

    @model_validator(mode='after')
    def items_for_kind(self) -> 'RequestIn':
        if self.kind in ('product_rfq', 'one_click') and not self.items:
            raise ValueError('items')
        if self.kind == 'one_click' and len(self.items) != 1:
            raise ValueError('items')
        if self.kind == 'service' and self.service is None:
            raise ValueError('service')
        return self


class RequestOut(CamelModel):
    site_request_id: str
    number: str
