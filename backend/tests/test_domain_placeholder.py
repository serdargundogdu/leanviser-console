"""finance · domain için framework-süz placeholder test.

Domain katmanı, framework gerektirmeden (FastAPI/DB importu olmadan) test
edilebilir olmalıdır. Bu placeholder o sözleşmeyi belgeler; gerçek iş kuralı
testleri Bedel Hesaplama diliminde (Core) eklenecek.
"""

from app.modules.finance import domain


def test_finance_domain_package_is_importable() -> None:
    # Saf domain paketi hiçbir altyapı bağımlılığı olmadan import edilebilir.
    assert domain is not None
