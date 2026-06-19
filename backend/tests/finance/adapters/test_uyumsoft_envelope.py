"""UyumsoftEInvoiceGateway zarf kurma + yanıt ayrıştırma birim testleri (ağsız).

SendInvoice gövdesinin entegratörce kabul edilen biçimini sabitler: WSSE
UsernameToken, tempuri ad-uzaylı <Invoice> sarmalayıcı (UBL kökü Invoice-2
DEĞİL), cbc/cac çocukları, TargetCustomer ve e-Arşiv eki. Bu biçim canlı test
endpoint'inde doğrulandı; test onu regresyona karşı korur.
"""

from datetime import date
from decimal import Decimal

import pytest
from lxml import etree

from app.modules.finance.adapters.uyumsoft_einvoice_gateway import (
    EInvoiceGatewayError,
    UyumsoftEInvoiceGateway,
)
from app.modules.finance.application.einvoice_models import EInvoiceLine, EInvoiceRequest, Party

S = "http://schemas.xmlsoap.org/soap/envelope/"
WSSE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
T = "http://tempuri.org/"
CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"


def _gateway() -> UyumsoftEInvoiceGateway:
    return UyumsoftEInvoiceGateway(username="user", password="pass")


def _request(profile: str = "EARSIVFATURA") -> EInvoiceRequest:
    return EInvoiceRequest(
        number="LVS2026000000001",
        uuid="11111111-1111-1111-1111-111111111111",
        issue_date=date(2026, 6, 18),
        issue_time="10:00:00",
        currency="TRY",
        profile=profile,
        invoice_type="SATIS",
        supplier=Party(
            tax_id="9000068418", name="LeanViser", tax_office="Beşiktaş", city="İstanbul"
        ),
        customer=Party(
            tax_id="11111111111",
            name="Ahmet Yılmaz",
            first_name="Ahmet",
            family_name="Yılmaz",
            city="İstanbul",
        ),
        lines=(
            EInvoiceLine(
                name="Danışmanlık",
                quantity=Decimal("1"),
                unit_code="C62",
                unit_price=Decimal("100.00"),
                vat_rate=Decimal("0.20"),
            ),
        ),
    )


def test_envelope_wsse_and_tempuri_invoice_wrapper():
    env = etree.fromstring(
        _gateway()._build_send_envelope(
            _request(), customer_alias="defaultpk", local_document_id="LV-1"
        )
    )
    assert env.findtext(f".//{{{WSSE}}}UsernameToken/{{{WSSE}}}Username") == "user"
    assert env.findtext(f".//{{{WSSE}}}UsernameToken/{{{WSSE}}}Password") == "pass"

    info = env.find(f".//{{{T}}}SendInvoice/{{{T}}}invoices/{{{T}}}InvoiceInfo")
    assert info.get("LocalDocumentId") == "LV-1"
    # UBL kökü tempuri sarmalayıcısında (Invoice-2 DEĞİL); çocuklar cbc.
    invoice = info.find(f"{{{T}}}Invoice")
    assert invoice is not None
    assert invoice.findtext(f"{{{CBC}}}ProfileID") == "EARSIVFATURA"
    assert invoice.findtext(f"{{{CBC}}}UUID") == "11111111-1111-1111-1111-111111111111"


def test_envelope_target_customer_and_earchive():
    env = etree.fromstring(
        _gateway()._build_send_envelope(
            _request(), customer_alias="defaultpk", local_document_id="LV-1"
        )
    )
    info = env.find(f".//{{{T}}}InvoiceInfo")
    target = info.find(f"{{{T}}}TargetCustomer")
    assert target.get("TCKN") == "11111111111"  # TCKN müşteri -> TCKN attribute
    assert target.get("Alias") == "defaultpk"
    assert target.get("Title") == "Ahmet Yılmaz"
    assert info.find(f"{{{T}}}EArchiveInvoiceInfo").get("DeliveryType") == "Electronic"
    assert info.findtext(f"{{{T}}}Scenario") == "Automated"


def test_einvoice_profile_omits_earchive():
    env = etree.fromstring(
        _gateway()._build_send_envelope(
            _request(profile="TICARIFATURA"),
            customer_alias="urn:mail:defaultpk@uyumsoft.com",
            local_document_id="LV-2",
        )
    )
    info = env.find(f".//{{{T}}}InvoiceInfo")
    assert info.find(f"{{{T}}}EArchiveInvoiceInfo") is None  # e-Fatura: e-Arşiv eki yok


def test_resolve_alias():
    gw = _gateway()
    assert gw._resolve_alias(_request("EARSIVFATURA"), None) == "defaultpk"
    assert gw._resolve_alias(_request("TICARIFATURA"), "urn:x") == "urn:x"
    with pytest.raises(EInvoiceGatewayError):
        gw._resolve_alias(_request("TICARIFATURA"), None)  # e-Fatura'da alias zorunlu


def test_parse_send_result_success():
    xml = (
        f'<s:Envelope xmlns:s="{S}"><s:Body><SendInvoiceResponse xmlns="{T}">'
        '<SendInvoiceResult IsSucceded="true"><Value Id="ettn-1" Number="LVS42"/>'
        "</SendInvoiceResult></SendInvoiceResponse></s:Body></s:Envelope>"
    ).encode()
    result = _gateway()._parse_send_result(xml)
    assert result.succeeded
    assert result.invoice_id == "LVS42"
    assert result.ettn == "ettn-1"


def test_parse_send_result_business_failure():
    xml = (
        f'<s:Envelope xmlns:s="{S}"><s:Body><SendInvoiceResponse xmlns="{T}">'
        '<SendInvoiceResult IsSucceded="false" Message="alıcı hatalı"/>'
        "</SendInvoiceResponse></s:Body></s:Envelope>"
    ).encode()
    result = _gateway()._parse_send_result(xml)
    assert not result.succeeded
    assert result.message == "alıcı hatalı"
    assert result.invoice_id is None


def test_parse_send_result_soap_fault_raises():
    xml = (
        f'<s:Envelope xmlns:s="{S}"><s:Body><s:Fault>'
        "<faultstring>InvalidSecurity</faultstring></s:Fault></s:Body></s:Envelope>"
    ).encode()
    with pytest.raises(EInvoiceGatewayError, match="InvalidSecurity"):
        _gateway()._parse_send_result(xml)
