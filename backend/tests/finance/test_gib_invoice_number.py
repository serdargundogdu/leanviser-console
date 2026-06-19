"""GibInvoiceNumber değer nesnesi testleri (saf domain; ağsız)."""

import pytest

from app.modules.finance.domain.gib_invoice_number import GibInvoiceNumber


def test_from_parts_zero_pads_sequence():
    number = GibInvoiceNumber.from_parts("LVS", 2026, 7)
    assert number.value == "LVS2026000000007"
    assert number.series == "LVS"
    assert number.year == 2026
    assert number.sequence == 7


def test_parse_valid_number_exposes_parts():
    number = GibInvoiceNumber("ABC2026000123456")
    assert number.series == "ABC"
    assert number.year == 2026
    assert number.sequence == 123456


@pytest.mark.parametrize(
    "value",
    [
        "INV-001",  # tamamen yanlış
        "LV2026000000001",  # 2 harf
        "lvs2026000000001",  # küçük harf
        "LVS202600000001",  # 15 hane
        "LVS20260000000001",  # 17 hane
        "LVS2026ABCDEFGHI",  # sıra harf içeriyor
    ],
)
def test_invalid_numbers_rejected(value):
    with pytest.raises(ValueError):
        GibInvoiceNumber(value)


@pytest.mark.parametrize(
    ("series", "year", "sequence"),
    [
        ("LV", 2026, 1),  # 2 harf
        ("lvs", 2026, 1),  # küçük harf
        ("LVS", 26, 1),  # yıl 4 hane değil
        ("LVS", 2026, 0),  # sıra < 1
        ("LVS", 2026, 1_000_000_000),  # sıra 9 haneyi aşar
    ],
)
def test_from_parts_validates_inputs(series, year, sequence):
    with pytest.raises(ValueError):
        GibInvoiceNumber.from_parts(series, year, sequence)
