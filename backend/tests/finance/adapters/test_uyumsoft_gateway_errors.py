"""UyumsoftEInvoiceGateway taşıma hatası sarmalaması (offline, ağsız).

Entegratör erişilemezken (ör. 503 / bağlantı reddi) çekirdeğe ham requests/zeep
istisnası sızmamalı; EInvoiceGatewayError'a sarılmalı — router bunu temiz 502'ye
çevirir (yoksa kullanıcı anlamsız 500 alır; gelen-kutusu 500 hatasının kök nedeni
buydu). Erişilemez bir adres kullanılır: dış servise gidilmez, hızlı/deterministik.
"""

from datetime import datetime

import pytest

from app.modules.finance.adapters.uyumsoft_einvoice_gateway import (
    EInvoiceGatewayError,
    UyumsoftEInvoiceGateway,
)


def _unreachable_gateway() -> UyumsoftEInvoiceGateway:
    # 127.0.0.1:1 -> bağlantı reddi; WSDL yüklenemez (kısa timeout ile hızlı başarısızlık).
    return UyumsoftEInvoiceGateway(
        username="x",
        password="y",
        wsdl_url="http://127.0.0.1:1/services/Integration?singleWsdl",
        timeout=2,
    )


def test_get_system_date_transport_failure_is_wrapped():
    with pytest.raises(EInvoiceGatewayError):
        _unreachable_gateway().get_system_date()


def test_recipient_aliases_transport_failure_is_wrapped():
    with pytest.raises(EInvoiceGatewayError):
        _unreachable_gateway().get_recipient_aliases("9000068418")


def test_inbox_transport_failure_is_wrapped():
    # Gelen kutusu "Getir" akışının birebir karşılığı: ham HTTPError değil port hatası.
    with pytest.raises(EInvoiceGatewayError):
        _unreachable_gateway().list_inbox_invoices(
            datetime(2026, 1, 1), datetime(2026, 1, 31)
        )
