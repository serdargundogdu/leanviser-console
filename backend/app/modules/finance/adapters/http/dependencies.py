"""Finance HTTP adapter bağımlılıkları (provider wiring).

Aktif ExchangeRateProvider burada seçilir. Şimdilik sabit kur; canlı TCMB'ye
geçiş için yalnız bu fonksiyon değişir (route ve use case aynı kalır).
"""

from __future__ import annotations

from app.modules.finance.adapters.fixed_exchange_rate_provider import FixedExchangeRateProvider
from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider


def get_exchange_rate_provider() -> ExchangeRateProvider:
    """FastAPI dependency: kullanılacak döviz kuru sağlayıcısı."""
    return FixedExchangeRateProvider()
