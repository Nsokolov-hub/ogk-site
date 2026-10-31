"""Business remark of 31 October 2026: phones and e-mails of the forms are checked against made-up values."""

import json
from pathlib import Path

import pytest

from app.requests.contacts import RULES, email_problem, plausible_phone

WEB_RULES = Path(__file__).resolve().parents[2] / 'src' / 'lib' / 'contact-rules.json'


def test_the_api_and_the_forms_share_one_set_of_rules():
    if not WEB_RULES.exists():
        pytest.skip('the storefront is not next to the API')
    assert json.loads(WEB_RULES.read_text(encoding='utf-8')) == RULES


@pytest.mark.parametrize(('phone', 'valid'), [
    ('+79991234567', True), ('+74950000000', True), ('+77012345678', True), ('+998901234567', True),
    ('+375291234567', True), ('+12025550123', True), ('+4930123456', True), ('+79012345678', True),
    ('+9987546428', False), ('+7999123456', False), ('+70123456789', False), ('+77777777777', False),
    ('+71234567890', False), ('+3751234567', False), ('+123', False),
])
def test_phone_numbers_have_the_length_of_their_country(phone, valid):
    assert plausible_phone(phone) is valid


@pytest.mark.parametrize(('email', 'problem'), [
    ('kav@delta.com', None), ('info@ogk-chem.ru', None), ('test@почта.рф', None), ('a.b+c@sub.mail.ru', None),
    ('x..y@mail.ru', 'email'), ('.x@mail.ru', 'email'), ('x@mail', 'email'), ('x@-mail.ru', 'email'),
    ('x@mail.r1', 'email'), ('ivan@gmial.com', 'emailTypo'), ('ivan@yandex.ry', 'emailTypo'),
    ('ivan@mail.con', 'emailTypo'), ('a@mailinator.com', 'emailDisposable'), ('a@example.com', 'emailDisposable'),
])
def test_emails_are_checked_for_shape_typos_and_throwaway_domains(email, problem):
    assert email_problem(email) == problem
