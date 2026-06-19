"""Finance HTTP uç noktası testleri (FastAPI TestClient; sabit-kur dependency override)."""

import re
from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.modules.finance.adapters.http.dependencies import (
    get_einvoice_gateway,
    get_einvoice_supplier,
    get_exchange_rate_provider,
    get_invoice_repository,
)
from app.modules.finance.adapters.sqlite_invoice_repository import SqliteInvoiceRepository
from app.modules.finance.application.einvoice_models import (
    EInvoiceSendResult,
    EInvoiceStatus,
    EInvoiceStatusLog,
    Party,
)
from app.modules.finance.domain.fx import ExchangeRate
from app.modules.finance.domain.money import Currency


class _StubRates:
    """Sabit kur döndüren sahte ExchangeRateProvider (test izolasyonu için)."""

    def get_rate(self, base: Currency, quote: Currency, as_of: date) -> ExchangeRate:
        return ExchangeRate(base=base, rate=Decimal("47.7841"), as_of=as_of, quote=quote)


class _FakeEInvoiceGateway:
    """Ağa çıkmayan sahte entegratör; sonuç testlerce ayarlanır."""

    def __init__(self) -> None:
        self.result = EInvoiceSendResult(succeeded=True, invoice_id="X", ettn="ETTN-API")
        self.aliases: tuple[str, ...] = ()  # boş -> e-Arşiv yolu

    def get_recipient_aliases(self, vkn_tckn: str) -> tuple[str, ...]:
        return self.aliases

    def send_invoice(self, req, *, customer_alias=None, local_document_id=None):
        return self.result

    def get_invoice_status(self, invoice_id: str) -> EInvoiceStatus:
        return EInvoiceStatus(
            invoice_id=invoice_id,  # ETTN ile sorgulandığını doğrular
            local_document_id="DOC",
            status="Succeed",
            status_code=1,
            message="",
            logs=(
                EInvoiceStatusLog(
                    created_at=datetime(2026, 6, 19, 10, 0), message="işlendi", type=2
                ),
            ),
        )

    def get_invoice_pdf(self, invoice_id: str) -> bytes:
        return b"%PDF-1.4 fake"


app.dependency_overrides[get_exchange_rate_provider] = _StubRates
_test_repository = SqliteInvoiceRepository(":memory:")
app.dependency_overrides[get_invoice_repository] = lambda: _test_repository
_fake_gateway = _FakeEInvoiceGateway()
app.dependency_overrides[get_einvoice_gateway] = lambda: _fake_gateway
app.dependency_overrides[get_einvoice_supplier] = lambda: Party(
    tax_id="9000068418", name="LeanViser", tax_office="Beşiktaş"
)
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


def test_response_includes_vat_breakdown():
    payload = {
        "invoice_id": "INV-VAT",
        "customer_company": "ACME",
        "issue_date": "2026-06-19",
        "currency": "TRY",
        "service_items": [
            {
                "description": "Danışmanlık (TRY)",
                "daily_rate": "1000.00",
                "currency": "TRY",
                "days": "2",
                "vat_rate": "0.20",
            }
        ],
        "expenses": [],
    }
    body = client.post("/finance/invoices", json=payload).json()
    assert body["total"] == "2000.00"  # net
    assert body["vat_total"] == "400.00"
    assert body["gross_total"] == "2400.00"
    assert body["lines"][0]["vat_rate"] == "0.20"
    assert body["lines"][0]["vat_amount"] == "400.00"


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


def _expense_payload(invoice_id: str) -> dict:
    return {
        "invoice_id": invoice_id,
        "customer_company": "ACME",
        "issue_date": "2026-06-19",
        "currency": "TRY",
        "service_items": [],
        "expenses": [{"type": "Fuel", "gross": "120.00", "vat_rate": "0.20", "currency": "TRY"}],
    }


def test_approve_then_send_transitions():
    client.post("/finance/invoices", json=_expense_payload("INV-FLOW"))
    approved = client.post("/finance/invoices/INV-FLOW/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "Approved"
    sent = client.post("/finance/invoices/INV-FLOW/send")
    assert sent.status_code == 200
    assert sent.json()["status"] == "Sent"


def test_issue_einvoice_marks_sent_and_records_ettn():
    client.post("/finance/invoices", json=_expense_payload("INV-ISSUE"))
    client.post("/finance/invoices/INV-ISSUE/approve")
    _fake_gateway.result = EInvoiceSendResult(
        succeeded=True, invoice_id="INV-ISSUE", ettn="ETTN-API"
    )
    response = client.post(
        "/finance/invoices/INV-ISSUE/issue",
        json={"customer": {"tax_id": "11111111111", "name": "Ahmet Yılmaz"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Sent"
    assert body["ettn"] == "ETTN-API"


def test_issue_assigns_gib_number():
    client.post("/finance/invoices", json=_expense_payload("INV-GIB"))
    client.post("/finance/invoices/INV-GIB/approve")
    _fake_gateway.result = EInvoiceSendResult(succeeded=True, invoice_id="INV-GIB", ettn="ETTN-GIB")
    body = client.post(
        "/finance/invoices/INV-GIB/issue",
        json={"customer": {"tax_id": "11111111111", "name": "Ahmet Yılmaz"}},
    ).json()
    assert body["status"] == "Sent"
    assert re.match(r"^LVS\d{13}$", body["gib_number"])  # 3 harf + yıl + 9 sıra


def test_issue_retry_reuses_gib_number():
    client.post("/finance/invoices", json=_expense_payload("INV-RETRY"))
    client.post("/finance/invoices/INV-RETRY/approve")
    payload = {"customer": {"tax_id": "11111111111", "name": "Ahmet Yılmaz"}}
    # İlk deneme entegratörce reddedilir; numara atanır ve faturada kalır.
    _fake_gateway.result = EInvoiceSendResult(succeeded=False, message="geçici hata")
    assert client.post("/finance/invoices/INV-RETRY/issue", json=payload).status_code == 422
    assigned = client.get("/finance/invoices/INV-RETRY").json()["gib_number"]
    assert assigned is not None
    # Yeniden deneme aynı numarayı kullanır (ardışıklık korunur, boşluk olmaz).
    _fake_gateway.result = EInvoiceSendResult(
        succeeded=True, invoice_id="INV-RETRY", ettn="ETTN-RETRY"
    )
    retry = client.post("/finance/invoices/INV-RETRY/issue", json=payload).json()
    assert retry["gib_number"] == assigned


def test_issue_unapproved_invoice_returns_409():
    client.post("/finance/invoices", json=_expense_payload("INV-ISSUE-D"))
    response = client.post(
        "/finance/invoices/INV-ISSUE-D/issue",
        json={"customer": {"tax_id": "11111111111", "name": "X Y"}},
    )
    assert response.status_code == 409


def test_issue_business_failure_returns_422_and_keeps_approved():
    client.post("/finance/invoices", json=_expense_payload("INV-ISSUE-F"))
    client.post("/finance/invoices/INV-ISSUE-F/approve")
    _fake_gateway.result = EInvoiceSendResult(succeeded=False, message="alıcı hatalı")
    response = client.post(
        "/finance/invoices/INV-ISSUE-F/issue",
        json={"customer": {"tax_id": "11111111111", "name": "X Y"}},
    )
    assert response.status_code == 422
    assert "alıcı" in response.json()["detail"]
    assert client.get("/finance/invoices/INV-ISSUE-F").json()["status"] == "Approved"


def _issue(invoice_id: str, ettn: str) -> None:
    client.post("/finance/invoices", json=_expense_payload(invoice_id))
    client.post(f"/finance/invoices/{invoice_id}/approve")
    _fake_gateway.result = EInvoiceSendResult(succeeded=True, invoice_id=invoice_id, ettn=ettn)
    client.post(
        f"/finance/invoices/{invoice_id}/issue",
        json={"customer": {"tax_id": "11111111111", "name": "Ahmet Yılmaz"}},
    )


def test_einvoice_status_after_issue():
    _issue("INV-ST", "ETTN-ST")
    response = client.get("/finance/invoices/INV-ST/einvoice-status")
    assert response.status_code == 200
    body = response.json()
    assert body["invoice_id"] == "ETTN-ST"  # ETTN ile sorgulanır
    assert body["status"] == "Succeed"
    assert len(body["logs"]) == 1
    assert body["logs"][0]["message"] == "işlendi"


def test_einvoice_pdf_after_issue():
    _issue("INV-PDF", "ETTN-PDF")
    response = client.get("/finance/invoices/INV-PDF/einvoice-pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_recipient_aliases_returns_list():
    _fake_gateway.aliases = ("defaultpk", "urn:mail:x@y.com")
    try:
        body = client.get("/finance/recipient-aliases/9000068418").json()
        assert body["vkn_tckn"] == "9000068418"
        assert body["aliases"] == ["defaultpk", "urn:mail:x@y.com"]
    finally:
        _fake_gateway.aliases = ()


def test_recipient_aliases_empty_for_unregistered():
    body = client.get("/finance/recipient-aliases/11111111111").json()
    assert body["aliases"] == []


def test_einvoice_status_not_issued_returns_409():
    client.post("/finance/invoices", json=_expense_payload("INV-NOISSUE"))
    assert client.get("/finance/invoices/INV-NOISSUE/einvoice-status").status_code == 409
    assert client.get("/finance/invoices/INV-NOISSUE/einvoice-pdf").status_code == 409


def test_send_before_approve_returns_409():
    client.post("/finance/invoices", json=_expense_payload("INV-DRAFT"))
    response = client.post("/finance/invoices/INV-DRAFT/send")
    assert response.status_code == 409


def test_transition_unknown_invoice_returns_404():
    assert client.post("/finance/invoices/NOPE/approve").status_code == 404


def test_delete_draft_invoice():
    client.post("/finance/invoices", json=_expense_payload("INV-DEL"))
    deleted = client.delete("/finance/invoices/INV-DEL")
    assert deleted.status_code == 204
    assert client.get("/finance/invoices/INV-DEL").status_code == 404


def test_delete_non_draft_returns_409():
    client.post("/finance/invoices", json=_expense_payload("INV-DEL2"))
    client.post("/finance/invoices/INV-DEL2/approve")
    assert client.delete("/finance/invoices/INV-DEL2").status_code == 409


def test_delete_unknown_returns_404():
    assert client.delete("/finance/invoices/NOPE").status_code == 404


def test_compile_stores_source_for_edit():
    client.post("/finance/invoices", json=_expense_payload("INV-SRC"))
    source = client.get("/finance/invoices/INV-SRC/source")
    assert source.status_code == 200
    assert source.json()["invoice_id"] == "INV-SRC"
    assert source.json()["expenses"][0]["type"] == "Fuel"


def test_source_missing_returns_404():
    assert client.get("/finance/invoices/NOPE/source").status_code == 404


def test_recompile_non_draft_returns_409():
    client.post("/finance/invoices", json=_expense_payload("INV-LOCK"))
    client.post("/finance/invoices/INV-LOCK/approve")
    assert client.post("/finance/invoices", json=_expense_payload("INV-LOCK")).status_code == 409
