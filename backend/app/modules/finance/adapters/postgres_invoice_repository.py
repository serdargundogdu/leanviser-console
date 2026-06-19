"""Postgres tabanlı InvoiceRepository adapter'ı (psycopg3, JSONB).

Prod kalıcılık (ör. Cloud SQL). Faturayı invoices(id PK, data JSONB), kaynak
girdileri invoice_sources(id PK, data JSONB) tablolarında saklar. Bağlantı
işlem-başına açılır (düşük hacim; pool sonraki optimizasyon). Fatura serileştirmesi
invoice_serialization'da ortaktır.

Bağlantı dizesi (DSN) dışarıdan verilir (DATABASE_URL). Cloud SQL'de Cloud Run
servisine instance bağlanır ve DSN socket'i gösterir — bu infra config'tir.
"""

from __future__ import annotations

import psycopg
from psycopg.types.json import Jsonb

from app.modules.finance.adapters.invoice_serialization import invoice_from_dict, invoice_to_dict
from app.modules.finance.application.invoice_repository import InvoiceRepository
from app.modules.finance.domain.invoice import Invoice


class PostgresInvoiceRepository(InvoiceRepository):
    """InvoiceRepository port'unun Postgres implementasyonu."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        with psycopg.connect(self._dsn) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY, data JSONB NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS invoice_sources "
                "(id TEXT PRIMARY KEY, data JSONB NOT NULL)"
            )

    def save(self, invoice: Invoice) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(
                "INSERT INTO invoices (id, data) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data",
                (invoice.id, Jsonb(invoice_to_dict(invoice))),
            )

    def get(self, invoice_id: str) -> Invoice | None:
        with psycopg.connect(self._dsn) as connection:
            row = connection.execute(
                "SELECT data FROM invoices WHERE id = %s", (invoice_id,)
            ).fetchone()
        if row is None:
            return None
        return invoice_from_dict(row[0])

    def list_all(self) -> list[Invoice]:
        with psycopg.connect(self._dsn) as connection:
            rows = connection.execute("SELECT data FROM invoices ORDER BY id").fetchall()
        return [invoice_from_dict(row[0]) for row in rows]

    def delete(self, invoice_id: str) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute("DELETE FROM invoices WHERE id = %s", (invoice_id,))
            connection.execute("DELETE FROM invoice_sources WHERE id = %s", (invoice_id,))

    def save_source(self, invoice_id: str, source: dict) -> None:
        with psycopg.connect(self._dsn) as connection:
            connection.execute(
                "INSERT INTO invoice_sources (id, data) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data",
                (invoice_id, Jsonb(source)),
            )

    def get_source(self, invoice_id: str) -> dict | None:
        with psycopg.connect(self._dsn) as connection:
            row = connection.execute(
                "SELECT data FROM invoice_sources WHERE id = %s", (invoice_id,)
            ).fetchone()
        if row is None:
            return None
        return row[0]
