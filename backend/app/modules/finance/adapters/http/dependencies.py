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
from app.modules.finance.adapters.uyumsoft_einvoice_gateway import (
    LIVE_WSDL_URL,
    TEST_WSDL_URL,
    UyumsoftEInvoiceGateway,
)
from app.modules.finance.application.einvoice_gateway import EInvoiceGateway
from app.modules.finance.application.einvoice_models import Party
from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider
from app.modules.finance.application.invoice_repository import InvoiceRepository

_DB_PATH = "leanviser_console.db"
_invoice_repository: InvoiceRepository | None = None
_einvoice_gateway: EInvoiceGateway | None = None


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


def get_einvoice_gateway() -> EInvoiceGateway:
    """FastAPI dependency: e-Fatura entegratör port'u (Uyumsoft, süreç-ömürlü).

    Kimlik bilgileri env'den gelir; varsayılanlar herkese açık TEST ortamıdır
    (Uyumsoft/Uyumsoft, test WSDL). Prod'da UYUMSOFT_USERNAME/PASSWORD ve
    UYUMSOFT_ENV=live ile canlı servise geçilir.
    """
    global _einvoice_gateway
    if _einvoice_gateway is None:
        username = os.environ.get("UYUMSOFT_USERNAME", "Uyumsoft")
        password = os.environ.get("UYUMSOFT_PASSWORD", "Uyumsoft")
        wsdl = LIVE_WSDL_URL if os.environ.get("UYUMSOFT_ENV") == "live" else TEST_WSDL_URL
        _einvoice_gateway = UyumsoftEInvoiceGateway(username, password, wsdl_url=wsdl)
    return _einvoice_gateway


def get_einvoice_supplier() -> Party:
    """Gönderici (LeanViser) e-Fatura kimliği. Env yoksa TEST hesabı varsayılır.

    Prod'da LEANVISER_VKN vb. ile gerçek mükellef bilgisi verilir. Varsayılan VKN
    (9000068418) Uyumsoft test hesabının kayıtlı VKN'sidir; gönderici VKN buna
    eşit olmazsa entegratör reddeder.
    """
    return Party(
        tax_id=os.environ.get("LEANVISER_VKN", "9000068418"),
        name=os.environ.get("LEANVISER_NAME", "LeanViser Danışmanlık"),
        tax_office=os.environ.get("LEANVISER_TAX_OFFICE", "Beşiktaş"),
        city=os.environ.get("LEANVISER_CITY", "İstanbul"),
        district=os.environ.get("LEANVISER_DISTRICT", "Beşiktaş"),
        street=os.environ.get("LEANVISER_STREET", "-"),
    )
