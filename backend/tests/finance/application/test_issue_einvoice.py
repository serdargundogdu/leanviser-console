"""IssueEInvoice use case testleri — sahte EInvoiceGateway; ağsız."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.finance.application.einvoice_models import (
    EInvoiceRequest,
    EInvoiceSendResult,
    Party,
)
from app.modules.finance.application.issue_einvoice import (
    EInvoiceIssueError,
    IssueEInvoice,
    IssueEInvoiceCommand,
)
from app.modules.finance.domain.invoice import Invoice, InvoiceLine
from app.modules.finance.domain.money import Currency, Money
from app.modules.finance.domain.vat import VatRate


class _FakeGateway:
    """send_invoice çağrısını yakalayan, is_einvoice_user'ı ayarlanabilen sahte port."""

    def __init__(self, is_user: bool = False, result: EInvoiceSendResult | None = None) -> None:
        self._is_user = is_user
        self._result = result or EInvoiceSendResult(
            succeeded=True, invoice_id="INV-1", ettn="ETTN-1"
        )
        self.sent_request: EInvoiceRequest | None = None
        self.sent_alias: str | None = None

    def is_einvoice_user(self, vkn_tckn: str, alias: str | None = None) -> bool:
        return self._is_user

    def send_invoice(self, req, *, customer_alias=None, local_document_id=None):
        self.sent_request = req
        self.sent_alias = customer_alias
        return self._result


def _approved_invoice() -> Invoice:
    invoice = Invoice(
        id="LVS2026000000001",
        customer_company="ACME",
        currency=Currency.TRY,
        issue_date=date(2026, 6, 18),
    )
    invoice.add_line(
        InvoiceLine(
            description="Danışmanlık",
            unit_price=Money(Decimal("1000.00"), Currency.TRY),
            quantity=Decimal("2"),
            vat_rate=VatRate(Decimal("0.10")),
        )
    )
    invoice.approve()
    return invoice


def _command(customer: Party | None = None) -> IssueEInvoiceCommand:
    return IssueEInvoiceCommand(
        customer=customer or Party(tax_id="11111111111", name="Ahmet Yılmaz", city="İstanbul"),
        supplier=Party(tax_id="9000068418", name="LeanViser", tax_office="Beşiktaş"),
        customer_alias="defaultpk",
    )


def test_maps_invoice_lines_and_parties():
    gateway = _FakeGateway()
    result = IssueEInvoice(gateway).execute(_approved_invoice(), _command())
    assert result.succeeded
    assert result.ettn == "ETTN-1"
    req = gateway.sent_request
    assert req.number == "LVS2026000000001"
    assert req.supplier.tax_id == "9000068418"
    assert req.customer.tax_id == "11111111111"
    assert len(req.lines) == 1
    assert req.lines[0].name == "Danışmanlık"
    assert req.lines[0].unit_price == Decimal("1000.00")
    assert req.lines[0].vat_rate == Decimal("0.10")
    assert gateway.sent_alias == "defaultpk"


def test_profile_is_earchive_for_unregistered_customer():
    gateway = _FakeGateway(is_user=False)
    IssueEInvoice(gateway).execute(_approved_invoice(), _command())
    assert gateway.sent_request.profile == "EARSIVFATURA"


def test_profile_is_einvoice_for_registered_customer():
    gateway = _FakeGateway(is_user=True)
    customer = Party(tax_id="3360571475", name="ACME A.Ş.", tax_office="Beşiktaş")
    IssueEInvoice(gateway).execute(_approved_invoice(), _command(customer))
    assert gateway.sent_request.profile == "TICARIFATURA"


def test_draft_invoice_cannot_be_issued():
    invoice = Invoice(
        id="INV-D", customer_company="ACME", currency=Currency.TRY, issue_date=date(2026, 6, 18)
    )
    invoice.add_line(
        InvoiceLine(
            description="x", unit_price=Money(Decimal("10.00"), Currency.TRY), quantity=Decimal("1")
        )
    )
    with pytest.raises(EInvoiceIssueError):
        IssueEInvoice(_FakeGateway()).execute(invoice, _command())
