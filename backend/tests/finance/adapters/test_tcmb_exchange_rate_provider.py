"""TCMB ACL adapter'ı testleri — ağsız; enjekte fetcher + gerçek yapıda XML fixture."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.finance.adapters.tcmb_exchange_rate_provider import (
    ExchangeRateUnavailableError,
    TcmbExchangeRateProvider,
    parse_tcmb_forex_buying,
    tcmb_url_for,
)
from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import Currency

SAMPLE_XML = (Path(__file__).parent / "fixtures" / "tcmb_sample.xml").read_bytes()
AS_OF = date(2026, 6, 19)


def _provider_with(xml: bytes) -> tuple[TcmbExchangeRateProvider, list[str]]:
    captured: list[str] = []

    def fake_fetch(url: str) -> bytes:
        captured.append(url)
        return xml

    return TcmbExchangeRateProvider(fetch=fake_fetch), captured


def test_get_rate_parses_forex_buying():
    provider, _ = _provider_with(SAMPLE_XML)
    assert provider.get_rate(Currency.EUR, Currency.TRY, AS_OF) == ExchangeRate(
        base=Currency.EUR, rate=Decimal("47.7841"), as_of=AS_OF, quote=Currency.TRY
    )
    assert provider.get_rate(Currency.USD, Currency.TRY, AS_OF) == ExchangeRate(
        base=Currency.USD, rate=Decimal("43.1234"), as_of=AS_OF, quote=Currency.TRY
    )


def test_builds_correct_dated_url():
    provider, captured = _provider_with(SAMPLE_XML)
    provider.get_rate(Currency.EUR, Currency.TRY, AS_OF)
    assert captured == ["https://www.tcmb.gov.tr/kurlar/202606/19062026.xml"]


def test_tcmb_url_zero_pads_day_and_month():
    assert tcmb_url_for(date(2026, 1, 2)) == "https://www.tcmb.gov.tr/kurlar/202601/02012026.xml"


def test_unit_greater_than_one_is_divided():
    xml = (
        b'<?xml version="1.0" encoding="ISO-8859-9"?>'
        b'<Tarih_Date><Currency Kod="EUR"><Unit>100</Unit>'
        b"<ForexBuying>4778.41</ForexBuying></Currency></Tarih_Date>"
    )
    assert parse_tcmb_forex_buying(xml, Currency.EUR) == Decimal("47.7841")


def test_unknown_currency_raises():
    xml = (
        b'<?xml version="1.0" encoding="ISO-8859-9"?>'
        b'<Tarih_Date><Currency Kod="EUR"><Unit>1</Unit>'
        b"<ForexBuying>47.7841</ForexBuying></Currency></Tarih_Date>"
    )
    provider, _ = _provider_with(xml)
    with pytest.raises(ExchangeRateUnavailableError):
        provider.get_rate(Currency.USD, Currency.TRY, AS_OF)


def test_quote_must_be_try_and_skips_fetch():
    provider, captured = _provider_with(SAMPLE_XML)
    with pytest.raises(ExchangeRateUnavailableError):
        provider.get_rate(Currency.EUR, Currency.USD, AS_OF)
    assert captured == []


def test_base_try_rejected():
    provider, _ = _provider_with(SAMPLE_XML)
    with pytest.raises(ExchangeRateUnavailableError):
        provider.get_rate(Currency.TRY, Currency.TRY, AS_OF)


def test_malformed_xml_raises():
    provider, _ = _provider_with(b"not-an-xml-payload")
    with pytest.raises(ExchangeRateUnavailableError):
        provider.get_rate(Currency.EUR, Currency.TRY, AS_OF)


def test_falls_back_to_previous_day_when_date_missing():
    available = tcmb_url_for(date(2026, 6, 18))

    def fetch(url: str) -> bytes:
        if url == available:
            return SAMPLE_XML
        raise ExchangeRateUnavailableError(f"veri yok: {url}")

    provider = TcmbExchangeRateProvider(fetch=fetch)
    result = provider.get_rate(Currency.EUR, Currency.TRY, date(2026, 6, 19))
    assert result.as_of == date(2026, 6, 18)
    assert result.rate == Decimal("47.7841")


def test_gives_up_after_lookback_window():
    def fetch(url: str) -> bytes:
        raise ExchangeRateUnavailableError(f"hep 404: {url}")

    provider = TcmbExchangeRateProvider(fetch=fetch, max_lookback_days=3)
    with pytest.raises(ExchangeRateUnavailableError):
        provider.get_rate(Currency.EUR, Currency.TRY, date(2026, 6, 19))
