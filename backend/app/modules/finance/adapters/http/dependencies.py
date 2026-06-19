"""Finance HTTP adapter bağımlılıkları (provider/repository wiring).

Aktif ExchangeRateProvider (canlı TCMB) ve InvoiceRepository burada seçilir.
DATABASE_URL tanımlıysa Postgres (prod, ör. Cloud SQL), aksi hâlde yerel SQLite
dosyası kullanılır. Değişim tek noktadadır; testler dependency override ile
in-memory örnekler takar (ağsız, dosyasız).
"""

from __future__ import annotations

import os

from app.modules.finance.adapters.postgres_invoice_repository import PostgresInvoiceRepository
from app.modules.finance.adapters.sqlite_invoice_repository import SqliteInvoiceRepository
from app.modules.finance.adapters.tcmb_exchange_rate_provider import TcmbExchangeRateProvider
from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider
from app.modules.finance.application.invoice_repository import InvoiceRepository

_DB_PATH = "leanviser_console.db"
_invoice_repository: InvoiceRepository | None = None


def get_exchange_rate_provider() -> ExchangeRateProvider:
    """FastAPI dependency: kullanılacak döviz kuru sağlayıcısı (canlı TCMB)."""
    return TcmbExchangeRateProvider()


def get_invoice_repository() -> InvoiceRepository:
    """FastAPI dependency: süreç-ömürlü tek fatura deposu.

    DATABASE_URL varsa Postgres, yoksa yerel SQLite. Tembel kurulur; modül
    import'unda bağlantı/dosya açılmaz (testler bunu override eder).
    """
    global _invoice_repository
    if _invoice_repository is None:
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            _invoice_repository = PostgresInvoiceRepository(database_url)
        else:
            _invoice_repository = SqliteInvoiceRepository(_DB_PATH)
    return _invoice_repository
