"""UBL-TR üretici birim testleri (ağsız; üretilen XML yapısı + tutarlar)."""

from datetime import date
from decimal import Decimal

from lxml import etree

from app.modules.finance.adapters.ubl_tr import build_ubl_tr
from app.modules.finance.application.einvoice_models import EInvoiceLine, EInvoiceRequest, Party

NS = {
    "i": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


def _request() -> EInvoiceRequest:
    return EInvoiceRequest(
        number="LVS2026000000001",
        uuid="11111111-1111-1111-1111-111111111111",
        issue_date=date(2026, 6, 19),
        currency="TRY",
        profile="EARSIVFATURA",
        invoice_type="SATIS",
        supplier=Party(
            tax_id="1234567890", name="LeanViser", tax_office="Beşiktaş", city="İstanbul"
        ),
        customer=Party(tax_id="9876543210", name="ACME A.Ş.", city="İstanbul"),
        lines=(
            EInvoiceLine(
                name="Danışmanlık",
                quantity=Decimal("16"),
                unit_code="DAY",
                unit_price=Decimal("1000.00"),
                vat_rate=Decimal("0.20"),
            ),
            EInvoiceLine(
                name="Akaryakıt",
                quantity=Decimal("1"),
                unit_code="C62",
                unit_price=Decimal("100.00"),
                vat_rate=Decimal("0.20"),
            ),
        ),
    )


def test_builds_ubl_backbone():
    root = etree.fromstring(build_ubl_tr(_request()))
    assert root.tag == f"{{{NS['i']}}}Invoice"
    assert root.findtext("cbc:CustomizationID", namespaces=NS) == "TR1.2"
    assert root.findtext("cbc:ProfileID", namespaces=NS) == "EARSIVFATURA"
    assert root.findtext("cbc:ID", namespaces=NS) == "LVS2026000000001"
    assert root.findtext("cbc:UUID", namespaces=NS) == "11111111-1111-1111-1111-111111111111"
    assert root.findtext("cbc:InvoiceTypeCode", namespaces=NS) == "SATIS"
    assert root.findtext("cbc:LineCountNumeric", namespaces=NS) == "2"
    assert len(root.findall("cac:InvoiceLine", NS)) == 2


def test_party_identification_and_totals():
    root = etree.fromstring(build_ubl_tr(_request()))
    supplier = root.find("cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID", NS)
    assert supplier.text == "1234567890"
    assert supplier.get("schemeID") == "VKN"
    assert root.findtext("cac:TaxTotal/cbc:TaxAmount", namespaces=NS) == "3220.00"
    payable = root.find("cac:LegalMonetaryTotal/cbc:PayableAmount", NS)
    assert payable.text == "19320.00"
    assert payable.get("currencyID") == "TRY"
    assert root.find("cac:TaxTotal/cac:TaxSubtotal/cbc:Percent", NS).text == "20.00"
