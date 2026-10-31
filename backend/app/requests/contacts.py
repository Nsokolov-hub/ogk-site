"""Checks of the customer's phone and e-mail (business remark of 31 October 2026: no more made-up contacts).

The rules (lengths of numbers by country code, mistyped and disposable mail domains) are shared with the forms:
contact_rules.json here is a copy of web src/lib/contact-rules.json, and a test keeps them equal. On top of the
forms, the API asks DNS whether the mail domain exists at all: a domain without MX and address records gets no
mail. A DNS failure or a timeout lets the address through — the check never blocks a request on our own trouble.
"""

import json
import random
import re
import socket
import struct
from functools import lru_cache
from pathlib import Path

RULES = json.loads((Path(__file__).with_name('contact_rules.json')).read_text(encoding='utf-8'))
PHONE_CODES = sorted(RULES['phoneLengths'], key=len, reverse=True)
LOCAL_RE = re.compile(r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*$", re.I)
LABEL_RE = re.compile(r'^(?!-)[a-z0-9а-яё-]{1,63}(?<!-)$', re.I)
FAKE_STARTS = ('1234567', '0123456', '9876543', '7654321')
TLD_RE = re.compile(r'^(?:[a-zа-яё]{2,24}|xn--[a-z0-9-]{2,59})$', re.I)


def plausible_phone(e164: str) -> bool:
    """+79991234567 looks like a real number: the length of its country, a real Russian code, not 1111111111."""
    if not re.fullmatch(r'\+[1-9][0-9]{6,14}', e164):
        return False
    digits = e164[1:]
    if not RULES['phoneMinDigits'] <= len(digits) <= RULES['phoneMaxDigits']:
        return False
    code = next((prefix for prefix in PHONE_CODES if digits.startswith(prefix)), None)
    if code and len(digits) != RULES['phoneLengths'][code]:
        return False
    national = digits[len(code):] if code else digits[-10:]
    if code == '7' and national[0] not in RULES['ruFirstDigits']:
        return False
    if len(set(national)) == 1:
        return False
    # 1234567…, 0123456…, 9876543…: a keyboard run instead of a number.
    return national[:7] not in FAKE_STARTS


def email_problem(value: str) -> str | None:
    """'email' — not an address, 'emailTypo' — a mistyped popular domain, 'emailDisposable' — a throwaway one."""
    at = value.rfind('@')
    if at < 1 or len(value) > 254:
        return 'email'
    local, domain = value[:at], value[at + 1:].lower()
    labels = domain.split('.')
    if len(local) > 64 or not LOCAL_RE.fullmatch(local) or len(labels) < 2 or len(domain) > 253:
        return 'email'
    if not all(LABEL_RE.fullmatch(label) for label in labels) or not TLD_RE.fullmatch(labels[-1]):
        return 'email'
    if domain in RULES['typoDomains'] or labels[-1] in RULES['badTlds']:
        return 'emailTypo'
    if any(domain == bad or domain.endswith('.' + bad) for bad in RULES['disposableDomains']):
        return 'emailDisposable'
    return None


def _nameservers() -> list[str]:
    try:
        text = Path('/etc/resolv.conf').read_text(encoding='utf-8')
    except OSError:
        return []
    return re.findall(r'^\s*nameserver\s+([0-9.]+)\s*$', text, re.M)[:2]


def _query(server: str, domain: str, kind: int, timeout: float) -> int | None:
    """DNS answer code and record count for one question, or None when the server did not answer."""
    ident = random.randrange(65536)
    question = b''.join(bytes([len(part)]) + part for part in (label.encode('ascii') for label in domain.split('.')))
    packet = struct.pack('>HHHHHH', ident, 0x0100, 1, 0, 0, 0) + question + b'\x00' + struct.pack('>HH', kind, 1)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.sendto(packet, (server, 53))
            answer, _ = sock.recvfrom(4096)
        except OSError:
            return None
    if len(answer) < 12 or struct.unpack('>H', answer[:2])[0] != ident:
        return None
    flags, _, count = struct.unpack('>HHH', answer[2:8])
    rcode = flags & 0x000F
    if rcode == 3:
        return -1  # NXDOMAIN: no such domain
    if rcode != 0:
        return None
    return count


@lru_cache(maxsize=2048)
def domain_receives_mail(domain: str, timeout: float = 1.5) -> bool | None:
    """True — the domain has MX or address records; False — it does not exist or has neither; None — unknown."""
    try:
        ascii_domain = domain.encode('idna').decode('ascii')
    except UnicodeError:
        return False
    servers = _nameservers()
    for server in servers:
        mx = _query(server, ascii_domain, 15, timeout)
        if mx is None:
            continue
        if mx == -1:
            return False
        if mx > 0:
            return True
        address = _query(server, ascii_domain, 1, timeout)
        if address is None:
            return None
        return address > 0
    return None
