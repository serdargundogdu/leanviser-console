"""Finance HTTP uç noktası testleri (FastAPI TestClient; sabit-kur dependency override)."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.modules.finance.adapters.http.dependencies import (
    get_exchange_rate_provider,
    get_invoice_repository,
)
from app.modules.finance.adapters.sqlite_invoice_repository import SqliteInvoiceRepository
from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import Currency


class _StubRates:
    """Sabit kur döndüren sahte ExchangeRateProvider (test izolasyonu için)."""

    def get_rate(self, base: Currency, quote: Currency, as_of: date) -> ExchangeRate:
        return ExchangeRate(base=base, rate=Decimal("47.7841"), as_of=as_of, quote=quote)


app.dependency_overrides[get_exchange_rate_provider] = _StubRates
_test_repository = SqliteInvoiceRepository(":memory:")
app.dependency_overrides[get_invoice_repository] = lambda: _test_repository
client = TestClient(app)


def test_compile_invoice_returns_lines_and_total():
    payload = {
        "invoice_id": "INV-1",
        "customer_company": "ACME",
        "issue_date": "2026-06-19",
        "currency": "TRY",
        "service_items": [
            {
                "description": "Danışmanlık",
                "daily_rate": "750.00",
                "currency": "EUR",
                "days": "16",
            }
        ],
        "expenses": [{"type": "Fuel", "gross": "120.00", "vat_rate": "0.20", "currency": "TRY"}],
    }
    response = client.post("/finance/invoices", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Draft"
    assert body["total"] == "573509.28"
    assert len(body["lines"]) == 2
    assert body["lines"][0]["line_total"] == "573409.28"
    assert body["lines"][1]["line_total"] == "100.00"


def test_invalid_currency_returns_422():
    payload = {
        "invoice_id": "INV-2",
        "customer_company": "ACME",
        "issue_date": "2026-06-19",
        "currency": "GBP",
        "service_items": [],
        "expenses": [],
    }
    response = client.post("/finance/invoices", json=payload)
    assert response.status_code == 422


def test_disallowed_vat_rate_returns_422():
    payload = {
        "invoice_id": "INV-3",
        "customer_company": "ACME",
        "issue_date": "2026-06-19",
        "currency": "TRY",
        "service_items": [],
        "expenses": [{"type": "Fuel", "gross": "120.00", "vat_rate": "0.05", "currency": "TRY"}],
    }
    response = client.post("/finance/invoices", json=payload)
    assert response.status_code == 422


def test_compiled_invoice_is_persisted_and_retrievable():
    payload = {
        "invoice_id": "INV-9",
        "customer_company": "ACME",
        "issue_date": "2026-06-19",
        "currency": "TRY",
        "service_items": [],
        "expenses": [{"type": "Fuel", "gross": "120.00", "vat_rate": "0.20", "currency": "TRY"}],
    }
    post = client.post("/finance/invoices", json=payload)
    assert post.status_code == 200
    got = client.get("/finance/invoices/INV-9")
    assert got.status_code == 200
    assert got.json()["id"] == "INV-9"
    assert got.json()["total"] == post.json()["total"] == "100.00"


def test_get_unknown_invoice_returns_404():
    response = client.get("/finance/invoices/NOPE")
    assert response.status_code == 404


def test_list_invoices_includes_saved():
    payload = {
        "invoice_id": "INV-LIST",
        "customer_company": "ACME",
        "issue_date": "2026-06-19",
        "currency": "TRY",
        "service_items": [],
        "expenses": [{"type": "Fuel", "gross": "120.00", "vat_rate": "0.20", "currency": "TRY"}],
    }
    client.post("/finance/invoices", json=payload)
    response = client.get("/finance/invoices")
    assert response.status_code == 200
    ids = [invoice["id"] for invoice in response.json()]
    assert "INV-LIST" in ids
