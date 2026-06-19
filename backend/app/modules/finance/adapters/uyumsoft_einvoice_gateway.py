"""Uyumsoft özel entegratör e-Fatura ACL adapter'ı (SOAP, zeep).

Ticari e-Dönüşüm entegratör servisi (efatura.uyumsoft.com.tr). GİB portalının
CAPTCHA'lı e-Devlet API'sinden farklı olarak CAPTCHA'sızdır; kimlik her çağrıda
WS-Security UsernameToken ile sağlanır. Yanıt deseni {IsSucceded, Message, Value}.
Çekirdek bu dış sistemden habersizdir.

Bu dilimde yalnız bağlantı (GetSystemDate) ve alıcı sorgu (IsEInvoiceUser)
gerçeklendi; fatura gönderimi (UBL-TR + SendInvoice) sonraki dilim.
"""

from __future__ import annotations

from datetime import datetime
from functools import cached_property

from requests import Session
from zeep import Client
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken

from app.modules.finance.application.einvoice_gateway import EInvoiceGateway

# Test ortamı (CAPTCHA'sız; herkese açık test creds: Uyumsoft/Uyumsoft).
TEST_WSDL_URL = "https://efatura-test.uyumsoft.com.tr/services/Integration?singleWsdl"
LIVE_WSDL_URL = "https://efatura.uyumsoft.com.tr/services/Integration?singleWsdl"


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

    def _value(self, response: object) -> object:
        if not getattr(response, "IsSucceded", False):
            message = getattr(response, "Message", None) or "Bilinmeyen entegratör hatası"
            raise EInvoiceGatewayError(message)
        return response.Value

    def get_system_date(self) -> datetime:
        return self._value(self._client.service.GetSystemDate())

    def is_einvoice_user(self, vkn_tckn: str, alias: str | None = None) -> bool:
        return bool(self._value(self._client.service.IsEInvoiceUser(vkn_tckn, alias)))
