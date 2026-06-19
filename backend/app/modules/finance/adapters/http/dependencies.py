"""Finance HTTP adapter bağımlılıkları (provider wiring).

Aktif ExchangeRateProvider burada seçilir: canlı TCMB. Sağlayıcı değişimi yalnız
bu fonksiyonu etkiler (route ve use case aynı kalır); testlerde FastAPI dependency
override ile sahte sağlayıcı takılır (ağsız). Deterministik offline alternatif:
FixedExchangeRateProvider.
"""

from __future__ import annotations

from app.modules.finance.adapters.tcmb_exchange_rate_provider import TcmbExchangeRateProvider
from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider


def get_exchange_rate_provider() -> ExchangeRateProvider:
    """FastAPI dependency: kullanılacak döviz kuru sağlayıcısı (canlı TCMB)."""
    return TcmbExchangeRateProvider()
