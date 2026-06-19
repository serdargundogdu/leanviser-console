"""UBL-TR 1.2 fatura XML üretici (lxml).

EInvoiceRequest -> GİB UBL-TR fatura XML'i. Mali mühür/imza entegratör tarafından
uygulanır (UBLExtensions burada üretilmez). Tutarlar 2 hane (ROUND_HALF_UP).
İlk-cut: zorunlu omurga (taraflar, vergi toplamları, kalemler); şema uyumu test
endpoint'inde iteratif doğrulanır.
"""

from __future__ import annotations

from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

from lxml import etree

from app.modules.finance.application.einvoice_models import EInvoiceLine, EInvoiceRequest, Party

_INV = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_NSMAP = {None: _INV, "cac": _CAC, "cbc": _CBC}
_Q2 = Decimal("0.01")


def _money(value: Decimal) -> str:
    return str(value.quantize(_Q2, rounding=ROUND_HALF_UP))


def _cbc(parent: etree._Element, tag: str, text: object, **attrs: str) -> etree._Element:
    el = etree.SubElement(parent, f"{{{_CBC}}}{tag}")
    el.text = str(text)
    for key, val in attrs.items():
        el.set(key, val)
    return el


def _cac(parent: etree._Element, tag: str) -> etree._Element:
    return etree.SubElement(parent, f"{{{_CAC}}}{tag}")


def _party(parent: etree._Element, party: Party) -> None:
    p = _cac(parent, "Party")
    _cbc(_cac(p, "PartyIdentification"), "ID", party.tax_id, schemeID=party.scheme_id)
    if party.is_person:
        # Gerçek kişi (TCKN): entegratör PartyName değil Person/Ad-Soyad bekler.
        person = _cac(p, "Person")
        first, family = party.person_names
        _cbc(person, "FirstName", first)
        _cbc(person, "FamilyName", family)
    else:
        _cbc(_cac(p, "PartyName"), "Name", party.name)
    addr = _cac(p, "PostalAddress")
    _cbc(addr, "StreetName", party.street or "-")
    _cbc(addr, "CitySubdivisionName", party.district or "-")
    _cbc(addr, "CityName", party.city or "-")
    _cbc(_cac(addr, "Country"), "Name", party.country)
    if party.tax_office:
        _cbc(_cac(_cac(p, "PartyTaxScheme"), "TaxScheme"), "Name", party.tax_office)


def _tax_subtotal(
    parent: etree._Element, taxable: Decimal, tax: Decimal, rate: Decimal, cur: str
) -> None:
    sub = _cac(parent, "TaxSubtotal")
    _cbc(sub, "TaxableAmount", _money(taxable), currencyID=cur)
    _cbc(sub, "TaxAmount", _money(tax), currencyID=cur)
    _cbc(sub, "Percent", _money(rate * 100))
    scheme = _cac(_cac(sub, "TaxCategory"), "TaxScheme")
    _cbc(scheme, "Name", "KDV")
    _cbc(scheme, "TaxTypeCode", "0015")


def _line(parent: etree._Element, index: int, line: EInvoiceLine, cur: str) -> None:
    el = _cac(parent, "InvoiceLine")
    _cbc(el, "ID", index)
    _cbc(el, "InvoicedQuantity", _money(line.quantity), unitCode=line.unit_code)
    _cbc(el, "LineExtensionAmount", _money(line.net()), currencyID=cur)
    tax_total = _cac(el, "TaxTotal")
    _cbc(tax_total, "TaxAmount", _money(line.vat()), currencyID=cur)
    _tax_subtotal(tax_total, line.net(), line.vat(), line.vat_rate, cur)
    _cbc(_cac(el, "Item"), "Name", line.name)
    _cbc(_cac(el, "Price"), "PriceAmount", _money(line.unit_price), currencyID=cur)


def populate_invoice(root: etree._Element, req: EInvoiceRequest) -> None:
    """UBL-TR fatura gövdesini (cbc/cac alt elemanları) verilen köke ekler.

    Kök elemanın ad-uzayı çağırana bırakılır: tek-başına XML'de Invoice-2,
    SendInvoice gömmesinde tempuri sarmalayıcısı (entegratör bu sarmalayıcıyı
    bekler; kök Invoice-2 olursa faturayı okumaz). Çocuklar daima cbc/cac'tir.
    """
    cur = req.currency
    _cbc(root, "UBLVersionID", "2.1")
    _cbc(root, "CustomizationID", "TR1.2")
    _cbc(root, "ProfileID", req.profile)
    _cbc(root, "ID", req.number)
    _cbc(root, "CopyIndicator", "false")
    _cbc(root, "UUID", req.uuid)
    _cbc(root, "IssueDate", req.issue_date.isoformat())
    _cbc(root, "IssueTime", req.issue_time)
    _cbc(root, "InvoiceTypeCode", req.invoice_type)
    _cbc(root, "DocumentCurrencyCode", cur)
    _cbc(root, "LineCountNumeric", len(req.lines))

    _party(_cac(root, "AccountingSupplierParty"), req.supplier)
    _party(_cac(root, "AccountingCustomerParty"), req.customer)

    # KDV toplamı: oranlara göre grupla (oran -> [taxable, tax])
    by_rate: OrderedDict[Decimal, list[Decimal]] = OrderedDict()
    for line in req.lines:
        bucket = by_rate.setdefault(line.vat_rate, [Decimal(0), Decimal(0)])
        bucket[0] += line.net()
        bucket[1] += line.vat()
    total_net = sum((line.net() for line in req.lines), Decimal(0))
    total_vat = sum((line.vat() for line in req.lines), Decimal(0))

    tax_total = _cac(root, "TaxTotal")
    _cbc(tax_total, "TaxAmount", _money(total_vat), currencyID=cur)
    for rate, (taxable, tax) in by_rate.items():
        _tax_subtotal(tax_total, taxable, tax, rate, cur)

    legal = _cac(root, "LegalMonetaryTotal")
    _cbc(legal, "LineExtensionAmount", _money(total_net), currencyID=cur)
    _cbc(legal, "TaxExclusiveAmount", _money(total_net), currencyID=cur)
    _cbc(legal, "TaxInclusiveAmount", _money(total_net + total_vat), currencyID=cur)
    _cbc(legal, "PayableAmount", _money(total_net + total_vat), currencyID=cur)

    for index, line in enumerate(req.lines, start=1):
        _line(root, index, line, cur)


def build_invoice_element(req: EInvoiceRequest) -> etree._Element:
    """Tek-başına UBL-TR <Invoice> element ağacı (kök Invoice-2 ad-uzayında)."""
    root = etree.Element(f"{{{_INV}}}Invoice", nsmap=_NSMAP)
    populate_invoice(root, req)
    return root


def build_ubl_tr(req: EInvoiceRequest) -> bytes:
    """EInvoiceRequest'ten tek-başına UBL-TR fatura XML'i üretir (UTF-8 bytes)."""
    return etree.tostring(build_invoice_element(req), xml_declaration=True, encoding="UTF-8")
