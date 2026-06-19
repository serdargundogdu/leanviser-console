"""TCMB döviz kuru ACL adapter'ı (adapters katmanı).

ExchangeRateProvider port'unun TCMB karşılığı. TCMB'nin günlük kur XML'inden
"döviz alış" (ForexBuying) değerini okuyup ExchangeRate'e çevirir. Çekirdek
(domain/application) bu dış sistemden habersizdir — bağımlılık içe akar.

HTTP taşıması enjekte edilebilir (fetch); varsayılanı stdlib urllib'dir. Böylece
parse mantığı ağsız birim test edilir. Kaynakta kimlik/CAPTCHA yoktur.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider
from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import Currency

_TCMB_BASE_URL = "https://www.tcmb.gov.tr/kurlar"
_DEFAULT_TIMEOUT_SECONDS = 10

# HTTP taşıma sözleşmesi: bir URL'i ham byte içeriğe çevirir (enjekte edilebilir).
XmlFetcher = Callable[[str], bytes]


class ExchangeRateUnavailableError(Exception):
    """İstenen tarih/kur için TCMB verisi alınamadığında fırlatılır."""


def tcmb_url_for(as_of: date) -> str:
    """Belirli bir tarih için TCMB kur XML adresini üretir (gün/ay sıfır dolgulu)."""
    return f"{_TCMB_BASE_URL}/{as_of:%Y%m}/{as_of:%d%m%Y}.xml"


def _urllib_fetch(url: str) -> bytes:
    """Varsayılan HTTP taşıması: TCMB XML'ini indirir (stdlib urllib, timeout'lu)."""
    request = urllib.request.Request(url, headers={"User-Agent": "leanviser-console/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=_DEFAULT_TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.URLError as exc:  # 404 (tatil/hafta sonu) dâhil
        raise ExchangeRateUnavailableError(f"TCMB erişilemedi: {url}") from exc


def parse_tcmb_forex_buying(xml_bytes: bytes, base: Currency) -> Decimal:
    """TCMB XML'inden base için birim başına döviz alış (ForexBuying) kurunu döndürür.

    ForexBuying değeri 'Unit' adet döviz içindir; birim başına oran için Unit'e
    bölünür (ör. JPY Unit=100). EUR/USD için Unit=1'dir.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ExchangeRateUnavailableError("TCMB yanıtı XML olarak ayrıştırılamadı") from exc

    node = root.find(f"./Currency[@Kod='{base.code}']")
    if node is None:
        raise ExchangeRateUnavailableError(f"TCMB XML'inde kur bulunamadı: {base.code}")

    forex_buying = node.findtext("ForexBuying")
    unit = node.findtext("Unit")
    if not forex_buying or not forex_buying.strip() or not unit or not unit.strip():
        raise ExchangeRateUnavailableError(f"{base.code} için ForexBuying/Unit eksik")

    try:
        return Decimal(forex_buying.strip()) / Decimal(unit.strip())
    except (InvalidOperation, ArithmeticError) as exc:
        raise ExchangeRateUnavailableError(f"{base.code} kuru sayıya çevrilemedi") from exc


class TcmbExchangeRateProvider(ExchangeRateProvider):
    """ExchangeRateProvider port'unun TCMB ACL implementasyonu.

    Yalnız TRY karşısı kur desteklenir (TCMB kurları TRY bazlıdır).
    """

    def __init__(self, fetch: XmlFetcher | None = None) -> None:
        self._fetch = fetch if fetch is not None else _urllib_fetch

    def get_rate(self, base: Currency, quote: Currency, as_of: date) -> ExchangeRate:
        if quote is not Currency.TRY:
            raise ExchangeRateUnavailableError(
                f"TCMB yalnız TRY karşısı kur verir; istenen quote: {quote.code}"
            )
        if base is Currency.TRY:
            raise ExchangeRateUnavailableError("base TRY olamaz (dönüşüm gereksiz)")

        xml_bytes = self._fetch(tcmb_url_for(as_of))
        rate = parse_tcmb_forex_buying(xml_bytes, base)
        return ExchangeRate(base=base, rate=rate, as_of=as_of, quote=quote)
