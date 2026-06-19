"""Finance HTTP adapter bağımlılıkları (provider/repository wiring).

Aktif ExchangeRateProvider (canlı TCMB) ve InvoiceRepository (kalıcı SQLite) burada
seçilir. Değişim tek noktadadır (route ve use case aynı kalır); testlerde FastAPI
dependency override ile sahte/in-memory örnekler takılır (ağsız, dosyasız).
Deterministik offline kur alternatifi: FixedExchangeRateProvider.
"""

from __future__ import annotations

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
    """FastAPI dependency: süreç-ömürlü tek fatura deposu (kalıcı SQLite).

    Tembel kurulur; modül import'unda dosya açılmaz (testler bunu override eder).
    """
    global _invoice_repository
    if _invoice_repository is None:
        _invoice_repository = SqliteInvoiceRepository(_DB_PATH)
    return _invoice_repository
