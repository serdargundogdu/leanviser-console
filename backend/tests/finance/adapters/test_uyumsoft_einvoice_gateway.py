"""UyumsoftEInvoiceGateway smoke testi (dış test servisine gider).

Yalnız UYUMSOFT_EINVOICE_SMOKE=1 iken çalışır; aksi hâlde modül atlanır (CI
ağsız/yeşil kalır). Test creds: Uyumsoft/Uyumsoft (herkese açık test ortamı).
"""

import os
from datetime import datetime

import pytest

from app.modules.finance.adapters.uyumsoft_einvoice_gateway import UyumsoftEInvoiceGateway

pytestmark = pytest.mark.skipif(
    os.environ.get("UYUMSOFT_EINVOICE_SMOKE") != "1",
    reason="UYUMSOFT_EINVOICE_SMOKE=1 değil (dış servise gidilmez)",
)


def _gateway() -> UyumsoftEInvoiceGateway:
    return UyumsoftEInvoiceGateway(username="Uyumsoft", password="Uyumsoft")


def test_get_system_date_returns_datetime():
    assert isinstance(_gateway().get_system_date(), datetime)


def test_is_einvoice_user_returns_bool():
    assert _gateway().is_einvoice_user("3360571475") in (True, False)
