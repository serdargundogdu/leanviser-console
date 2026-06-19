"""UyumsoftEInvoiceGateway smoke testi (dış test servisine gider).

Yalnız UYUMSOFT_EINVOICE_SMOKE=1 iken çalışır; aksi hâlde modül atlanır (CI
ağsız/yeşil kalır). Test creds: Uyumsoft/Uyumsoft (herkese açık test ortamı).
"""

import os
import time
import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.modules.finance.adapters.uyumsoft_einvoice_gateway import UyumsoftEInvoiceGateway
from app.modules.finance.application.einvoice_models import EInvoiceLine, EInvoiceRequest, Party

pytestmark = pytest.mark.skipif(
    os.environ.get("UYUMSOFT_EINVOICE_SMOKE") != "1",
    reason="UYUMSOFT_EINVOICE_SMOKE=1 değil (dış servise gidilmez)",
)

# Test hesabının kayıtlı VKN'si (GetCustomerCreditInfo ile keşfedildi); gönderici
# VKN bununla eşleşmek zorunda, aksi hâlde entegratör reddeder.
_TEST_SENDER_VKN = "9000068418"


def _gateway() -> UyumsoftEInvoiceGateway:
    return UyumsoftEInvoiceGateway(username="Uyumsoft", password="Uyumsoft")


def test_get_system_date_returns_datetime():
    assert isinstance(_gateway().get_system_date(), datetime)


def test_is_einvoice_user_returns_bool():
    assert _gateway().is_einvoice_user("3360571475") in (True, False)


def test_send_invoice_earchive_succeeds():
    # Her koşuda benzersiz No/UUID (entegratör başarılı No'yu tekrar kabul etmez).
    number = f"LVS2026{int(time.time()) % 10**9:09d}"
    req = EInvoiceRequest(
        number=number,
        uuid=str(uuid.uuid4()),
        issue_date=date(2026, 6, 18),
        issue_time="10:00:00",
        currency="TRY",
        profile="EARSIVFATURA",
        invoice_type="SATIS",
        supplier=Party(
            tax_id=_TEST_SENDER_VKN,
            name="LeanViser Danışmanlık",
            tax_office="Beşiktaş",
            city="İstanbul",
            district="Beşiktaş",
            street="Test Cd 1",
        ),
        customer=Party(
            tax_id="11111111111",
            name="Ahmet Yılmaz",
            first_name="Ahmet",
            family_name="Yılmaz",
            city="İstanbul",
            street="Müşteri Sk 2",
        ),
        lines=(
            EInvoiceLine(
                name="Danışmanlık hizmeti",
                quantity=Decimal("1"),
                unit_code="C62",
                unit_price=Decimal("100.00"),
                vat_rate=Decimal("0.20"),
            ),
        ),
    )
    result = _gateway().send_invoice(req, local_document_id=number)
    assert result.succeeded, result.message
    assert result.invoice_id == number
    assert result.ettn
