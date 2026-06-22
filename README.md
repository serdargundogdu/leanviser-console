# LeanViser CONSOLE

LeanViser'ın **iç operasyon uygulaması** (İç Projeler). **Tek-kiracılı** (yalnız LeanViser;
multi-tenant yok, bu aşamada auth yok). İlk route **finance** (`/finance`), ilk süreç **fatura kesme**.

> Mimari, dil kuralı, kilitli kararlar ve Ubiquitous Language için **[CLAUDE.md](./CLAUDE.md)**'ye bakın.
> Bu repo **modüler monolit** + **hexagonal (ports & adapters)** mimarisini izler; bağımlılık daima
> içe akar (`adapters → application → domain`).

## Gereksinimler

- [uv](https://docs.astral.sh/uv/) (Python 3.12'yi de yönetir)
- Node.js 20+ (frontend için)
- Docker (opsiyonel; konteyner çalıştırma/deploy için)

## Backend

```bash
cd backend

# Bağımlılıkları kur (uv, Python 3.12'yi otomatik sağlar)
uv sync

# Geliştirme sunucusu (http://localhost:8000)
uv run uvicorn app.main:app --reload

# Sağlık kontrolü
curl http://localhost:8000/health   # -> {"status":"ok"}
```

### Test & Lint

```bash
cd backend
uv run pytest            # testler yeşil olmalı
uv run ruff check .      # lint
uv run ruff format .     # format
```

## Frontend

```bash
cd frontend

npm install
npm run dev      # http://localhost:5173  (/finance placeholder)
npm run build    # üretim derlemesi -> dist/
```

## Docker (tek servis: SPA + API)

Kök `Dockerfile` çok aşamalıdır: önce frontend'i (Vite → `dist/`) derler, sonra backend'i
kurar ve derlenmiş SPA'yı imaja koyar. **Build context repo köküdür.**

```bash
docker build -t leanviser-console .
docker run -p 8080:8080 leanviser-console
curl http://localhost:8080/health          # -> {"status":"ok"}
open  http://localhost:8080/finance         # SPA (arayüz)
curl http://localhost:8080/api/finance/invoices   # API (/api altında)
```

İmaj `uvicorn` ile çalışır ve Cloud Run'ın enjekte ettiği `$PORT`'u kullanır (varsayılan 8080).
FastAPI API'yi **`/api`** altında, derlenmiş SPA'yı geri kalan tüm yollarda sunar — tek origin,
CORS yok. Geliştirmede arayüz Vite'tan (`:5173`), API backend'ten (`:8000`) gelir; Vite `/api`
isteklerini backend'e proxy'ler (ön ek korunur), böylece yollar prod ile birebir aynıdır.

## CI / CD

- **`.github/workflows/ci.yml`** — her push/PR'da `ruff` + `pytest` + frontend `build`.
- **`.github/workflows/deploy.yml`** — `main`'e push veya manuel tetikte GCP Cloud Run deploy **iskeleti**.
  Çalışması için şu repo secret'ları gerekir (henüz placeholder):
  - `GCP_PROJECT` — GCP proje kimliği
  - `GCP_REGION` — Cloud Run bölgesi (ör. `europe-west1`)
  - `GCP_SA_KEY` — deploy yetkili Service Account JSON anahtarı

  Secret'lar tanımlı değilken deploy işi atlanır (workflow kırmızıya düşmez); girilince gerçek deploy çalışır.

## Kapsam notu (bu dilim)

Bu dilim yalnız **repo scaffold + CI/CD**'dir. **Domain mantığı yok, dış entegrasyon yok.**
Sıradaki dilim: **Core — Bedel Hesaplama** (Money VO, KDV ayrıştırma, gün × ücret, döviz dönüşümü).
Detaylar için [CLAUDE.md](./CLAUDE.md) "Kapsam dışı" bölümüne bakın.
