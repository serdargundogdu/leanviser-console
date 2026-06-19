"""SQLite tabanlı InvoiceRepository adapter'ı (stdlib sqlite3).

Faturayı JSON blob olarak saklar: invoices(id PK, data). Tek bağlantı tutulur
(check_same_thread=False) ve işlemler bir Lock ile serileştirilir — FastAPI sync
uçları threadpool'da çalıştığı için. Tutarlar string (Decimal kesinliği korunur).

Not: Cloud Run dosya sistemi geçicidir; kalıcı prod için aynı port'a takılacak bir
Cloud SQL/Postgres adapter'ı gerekir. Yerel/dev için bu dosya kalıcıdır.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date
from decimal import Decimal

from app.modules.finance.application.invoice_repository import InvoiceRepository
from app.modules.finance.domain.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.modules.finance.domain.money import Currency, Money


class SqliteInvoiceRepository(InvoiceRepository):
    """InvoiceRepository port'unun SQLite implementasyonu."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        self._connection.commit()

    def save(self, invoice: Invoice) -> None:
        payload = json.dumps(_to_dict(invoice))
        with self._lock:
            self._connection.execute(
                "INSERT INTO invoices (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                (invoice.id, payload),
            )
            self._connection.commit()

    def get(self, invoice_id: str) -> Invoice | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT data FROM invoices WHERE id = ?", (invoice_id,)
            ).fetchone()
        if row is None:
            return None
        return _from_dict(json.loads(row[0]))

    def list_all(self) -> list[Invoice]:
        with self._lock:
            rows = self._connection.execute("SELECT data FROM invoices ORDER BY id").fetchall()
        return [_from_dict(json.loads(row[0])) for row in rows]


def _to_dict(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "customer_company": invoice.customer_company,
        "currency": invoice.currency.code,
        "issue_date": invoice.issue_date.isoformat(),
        "status": invoice.status.value,
        "lines": [
            {
                "description": line.description,
                "unit_price": str(line.unit_price.amount),
                "currency": line.unit_price.currency.code,
                "quantity": str(line.quantity),
            }
            for line in invoice.lines
        ],
    }


def _from_dict(data: dict) -> Invoice:
    lines = [
        InvoiceLine(
            description=line["description"],
            unit_price=Money(Decimal(line["unit_price"]), Currency[line["currency"]]),
            quantity=Decimal(line["quantity"]),
        )
        for line in data["lines"]
    ]
    return Invoice.reconstitute(
        id=data["id"],
        customer_company=data["customer_company"],
        currency=Currency[data["currency"]],
        issue_date=date.fromisoformat(data["issue_date"]),
        status=InvoiceStatus(data["status"]),
        lines=lines,
    )
