"""finance · domain katmanı.

Saf iş kuralı ve aggregate'ler burada yaşar. **Framework-süzdür**: FastAPI, DB
veya dış API'leri import etmez. Bağımlılık daima içe akar; bu katman hiçbir dış
katmanı tanımaz. İş kuralı anemik değil, aggregate'te tutulur.

(Bedel Hesaplama mantığı — Money VO, KDV, gün × ücret, döviz — sonraki dilimde: Core.)
"""
