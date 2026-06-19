"""Uyumsoft özel entegratör e-Fatura ACL adapter'ı (SOAP).

Ticari e-Dönüşüm entegratör servisi (efatura.uyumsoft.com.tr). GİB portalının
CAPTCHA'lı e-Devlet API'sinden farklı olarak CAPTCHA'sızdır; kimlik her çağrıda
WS-Security UsernameToken ile sağlanır. Yanıt deseni {IsSucceded, Message, Value}.
Çekirdek bu dış sistemden habersizdir.

Basit tipli çağrılar (GetSystemDate, IsEInvoiceUser) zeep ile yapılır. SendInvoice
ise elle kurulan SOAP zarfıyla gönderilir: entegratör, UBL faturasını tempuri
ad-uzaylı bir <Invoice> sarmalayıcı içinde (alt elemanlar cbc/cac) bekler; bu
yerleşim zeep'in WSDL tiplerinden temiz üretilemediğinden zarf elle kurulur.
Bu biçim canlı test endpoint'inde ampirik doğrulandı (IsSucceded=true).
"""

from __future__ import annotations

from datetime import datetime
from functools import cached_property

from lxml import etree
from requests import Session
from zeep import Client
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken

from app.modules.finance.adapters.ubl_tr import populate_invoice
from app.modules.finance.application.einvoice_gateway import EInvoiceGateway
from app.modules.finance.application.einvoice_models import EInvoiceRequest, EInvoiceSendResult

# Test ortamı (CAPTCHA'sız; herkese açık test creds: Uyumsoft/Uyumsoft).
TEST_WSDL_URL = "https://efatura-test.uyumsoft.com.tr/services/Integration?singleWsdl"
LIVE_WSDL_URL = "https://efatura.uyumsoft.com.tr/services/Integration?singleWsdl"

# SendInvoice zarfı için ad-uzayları ve sabitler.
_SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
_WSSE_NS = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
_TEMPURI_NS = "http://tempuri.org/"
_CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
_CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_PASSWORD_TEXT = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText"
_SEND_INVOICE_ACTION = "http://tempuri.org/IIntegration/SendInvoice"
_EARCHIVE_PROFILE = "EARSIVFATURA"
_DEFAULT_EARCHIVE_ALIAS = "defaultpk"  # e-Arşiv nihai tüketici varsayılan posta kutusu


class EInvoiceGatewayError(Exception):
    """Entegratör çağrısı başarısız (IsSucceded=False ya da taşıma hatası)."""


class UyumsoftEInvoiceGateway(EInvoiceGateway):
    """EInvoiceGateway port'unun Uyumsoft (SOAP) implementasyonu."""

    def __init__(
        self,
        username: str,
        password: str,
        wsdl_url: str = TEST_WSDL_URL,
        timeout: int = 40,
    ) -> None:
        self._username = username
        self._password = password
        self._wsdl_url = wsdl_url
        self._endpoint = wsdl_url.split("?", 1)[0]  # ?singleWsdl olmadan servis adresi
        self._timeout = timeout

    @cached_property
    def _client(self) -> Client:
        # Tembel: bağlantı/WSDL ilk çağrıda kurulur (import/yapımda ağ yok).
        transport = Transport(
            session=Session(), timeout=self._timeout, operation_timeout=self._timeout
        )
        return Client(
            self._wsdl_url,
            transport=transport,
            wsse=UsernameToken(self._username, self._password),
        )

    @cached_property
    def _session(self) -> Session:
        # SendInvoice ham SOAP POST'u için (zeep'ten ayrı, elle kurulan zarf).
        return Session()

    def _value(self, response: object) -> object:
        if not getattr(response, "IsSucceded", False):
            message = getattr(response, "Message", None) or "Bilinmeyen entegratör hatası"
            raise EInvoiceGatewayError(message)
        return response.Value

    def get_system_date(self) -> datetime:
        return self._value(self._client.service.GetSystemDate())

    def is_einvoice_user(self, vkn_tckn: str, alias: str | None = None) -> bool:
        return bool(self._value(self._client.service.IsEInvoiceUser(vkn_tckn, alias)))

    def send_invoice(
        self,
        req: EInvoiceRequest,
        *,
        customer_alias: str | None = None,
        local_document_id: str | None = None,
    ) -> EInvoiceSendResult:
        envelope = self._build_send_envelope(
            req,
            customer_alias=self._resolve_alias(req, customer_alias),
            local_document_id=local_document_id or req.number,
        )
        headers = {
            "Content-Type": 'text/xml;charset="utf-8"',
            "SOAPAction": _SEND_INVOICE_ACTION,
        }
        response = self._session.post(
            self._endpoint, data=envelope, headers=headers, timeout=self._timeout
        )
        return self._parse_send_result(response.content)

    @staticmethod
    def _resolve_alias(req: EInvoiceRequest, customer_alias: str | None) -> str:
        if customer_alias:
            return customer_alias
        if req.profile == _EARCHIVE_PROFILE:
            return _DEFAULT_EARCHIVE_ALIAS  # e-Arşiv: nihai tüketici posta kutusu
        raise EInvoiceGatewayError("e-Fatura gönderimi için alıcı etiketi (alias) gerekli")

    def _build_send_envelope(
        self, req: EInvoiceRequest, *, customer_alias: str, local_document_id: str
    ) -> bytes:
        """Kanıtlanmış SendInvoice SOAP zarfını kurar (WSSE + tempuri-sarmalı UBL)."""
        env = etree.Element(f"{{{_SOAP_NS}}}Envelope", nsmap={"s": _SOAP_NS})

        header = etree.SubElement(env, f"{{{_SOAP_NS}}}Header")
        security = etree.SubElement(header, f"{{{_WSSE_NS}}}Security", nsmap={"o": _WSSE_NS})
        security.set(f"{{{_SOAP_NS}}}mustUnderstand", "1")
        token = etree.SubElement(security, f"{{{_WSSE_NS}}}UsernameToken")
        etree.SubElement(token, f"{{{_WSSE_NS}}}Username").text = self._username
        password = etree.SubElement(token, f"{{{_WSSE_NS}}}Password")
        password.set("Type", _PASSWORD_TEXT)
        password.text = self._password

        body = etree.SubElement(env, f"{{{_SOAP_NS}}}Body")
        send = etree.SubElement(body, f"{{{_TEMPURI_NS}}}SendInvoice", nsmap={None: _TEMPURI_NS})
        invoices = etree.SubElement(send, f"{{{_TEMPURI_NS}}}invoices")
        info = etree.SubElement(invoices, f"{{{_TEMPURI_NS}}}InvoiceInfo")
        info.set("LocalDocumentId", local_document_id)

        # UBL faturası tempuri <Invoice> sarmalayıcısı içinde; çocuklar cbc/cac.
        invoice = etree.SubElement(
            info, f"{{{_TEMPURI_NS}}}Invoice", nsmap={"cac": _CAC_NS, "cbc": _CBC_NS}
        )
        populate_invoice(invoice, req)

        target = etree.SubElement(info, f"{{{_TEMPURI_NS}}}TargetCustomer")
        target.set(req.customer.scheme_id, req.customer.tax_id)  # TCKN ya da VKN
        target.set("Alias", customer_alias)
        target.set("Title", req.customer.name)
        if req.profile == _EARCHIVE_PROFILE:
            earchive = etree.SubElement(info, f"{{{_TEMPURI_NS}}}EArchiveInvoiceInfo")
            earchive.set("DeliveryType", "Electronic")
        etree.SubElement(info, f"{{{_TEMPURI_NS}}}Scenario").text = "Automated"

        return etree.tostring(env, xml_declaration=True, encoding="UTF-8")

    def _parse_send_result(self, content: bytes) -> EInvoiceSendResult:
        root = etree.fromstring(content)
        result = root.find(f".//{{{_TEMPURI_NS}}}SendInvoiceResult")
        if result is None:
            fault = root.findtext(f".//{{{_SOAP_NS}}}Fault/faultstring")
            raise EInvoiceGatewayError(fault or "Beklenmeyen entegratör yanıtı")
        if result.get("IsSucceded") != "true":
            return EInvoiceSendResult(succeeded=False, message=result.get("Message") or "")
        value = result.find(f"{{{_TEMPURI_NS}}}Value")
        return EInvoiceSendResult(
            succeeded=True,
            message=result.get("Message") or "",
            invoice_id=value.get("Number") if value is not None else None,
            ettn=value.get("Id") if value is not None else None,
        )
