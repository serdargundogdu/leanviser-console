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
    """send_invoice çağrısını yakalayan, alıcı etiketleri ayarlanabilen sahte port."""

    def __init__(
        self, aliases: tuple[str, ...] = (), result: EInvoiceSendResult | None = None
    ) -> None:
        self._aliases = aliases
        self._result = result or EInvoiceSendResult(
            succeeded=True, invoice_id="INV-1", ettn="ETTN-1"
        )
        self.sent_request: EInvoiceRequest | None = None
        self.sent_alias: str | None = None
        self.sent_local_document_id: str | None = None

    def get_recipient_aliases(self, vkn_tckn: str) -> tuple[str, ...]:
        return self._aliases

    def send_invoice(self, req, *, customer_alias=None, local_document_id=None):
        self.sent_request = req
        self.sent_alias = customer_alias
        self.sent_local_document_id = local_document_id
        return self._result


def _approved_invoice() -> Invoice:
    invoice = Invoice(
        id="INV-INTERNAL-1",  # iç id; resmi GİB numarasından farklı
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
        gib_number="LVS2026000000001",
        customer_alias="defaultpk",
    )


def test_maps_invoice_lines_and_parties():
    gateway = _FakeGateway()
    result = IssueEInvoice(gateway).execute(_approved_invoice(), _command())
    assert result.succeeded
    assert result.ettn == "ETTN-1"
    req = gateway.sent_request
    assert req.number == "LVS2026000000001"  # resmi GİB numarası -> cbc:ID
    assert req.supplier.tax_id == "9000068418"
    assert req.customer.tax_id == "11111111111"
    assert len(req.lines) == 1
    assert req.lines[0].name == "Danışmanlık"
    assert req.lines[0].unit_price == Decimal("1000.00")
    assert req.lines[0].vat_rate == Decimal("0.10")
    assert gateway.sent_alias == "defaultpk"
    assert gateway.sent_local_document_id == "INV-INTERNAL-1"  # iç fatura id


def test_profile_is_earchive_for_unregistered_customer():
    gateway = _FakeGateway(aliases=())
    IssueEInvoice(gateway).execute(_approved_invoice(), _command())
    assert gateway.sent_request.profile == "EARSIVFATURA"


def test_profile_is_einvoice_for_registered_customer():
    gateway = _FakeGateway(aliases=("defaultpk",))
    customer = Party(tax_id="3360571475", name="ACME A.Ş.", tax_office="Beşiktaş")
    IssueEInvoice(gateway).execute(_approved_invoice(), _command(customer))
    assert gateway.sent_request.profile == "TICARIFATURA"


def test_registered_customer_auto_picks_first_alias():
    gateway = _FakeGateway(aliases=("urn:mail:x@y.com", "defaultpk"))
    customer = Party(tax_id="3360571475", name="ACME A.Ş.", tax_office="Beşiktaş")
    # customer_alias verilmedi -> bulunan ilk etiket kullanılır
    command = IssueEInvoiceCommand(
        customer=customer,
        supplier=Party(tax_id="9000068418", name="LeanViser", tax_office="Beşiktaş"),
        gib_number="LVS2026000000001",
    )
    IssueEInvoice(gateway).execute(_approved_invoice(), command)
    assert gateway.sent_request.profile == "TICARIFATURA"
    assert gateway.sent_alias == "urn:mail:x@y.com"


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
