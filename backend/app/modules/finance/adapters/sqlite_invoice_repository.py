"""SQLite tabanlı InvoiceRepository adapter'ı (stdlib sqlite3).

Faturayı JSON blob olarak saklar: invoices(id PK, data). Faturanın kaynak girdileri
(derleme isteği) ayrı invoice_sources tablosunda opak JSON olarak tutulur (düzenleme
için). Tek bağlantı tutulur (check_same_thread=False) ve işlemler bir Lock ile
serileştirilir. Fatura serileştirmesi invoice_serialization'da ortaktır.

Not: Cloud Run dosya sistemi geçicidir; kalıcı prod için PostgresInvoiceRepository
(DATABASE_URL) kullanılır — aynı port.
"""

from __future__ import annotations

import json
import sqlite3
import threading

from app.modules.finance.adapters.invoice_serialization import invoice_from_dict, invoice_to_dict
from app.modules.finance.application.invoice_repository import InvoiceRepository
from app.modules.finance.domain.invoice import Invoice


class SqliteInvoiceRepository(InvoiceRepository):
    """InvoiceRepository port'unun SQLite implementasyonu."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS invoice_sources (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        self._connection.commit()

    def save(self, invoice: Invoice) -> None:
        payload = json.dumps(invoice_to_dict(invoice))
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
        return invoice_from_dict(json.loads(row[0]))

    def list_all(self) -> list[Invoice]:
        with self._lock:
            rows = self._connection.execute("SELECT data FROM invoices ORDER BY id").fetchall()
        return [invoice_from_dict(json.loads(row[0])) for row in rows]

    def delete(self, invoice_id: str) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
            self._connection.execute("DELETE FROM invoice_sources WHERE id = ?", (invoice_id,))
            self._connection.commit()

    def save_source(self, invoice_id: str, source: dict) -> None:
        payload = json.dumps(source)
        with self._lock:
            self._connection.execute(
                "INSERT INTO invoice_sources (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                (invoice_id, payload),
            )
            self._connection.commit()

    def get_source(self, invoice_id: str) -> dict | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT data FROM invoice_sources WHERE id = ?", (invoice_id,)
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])
