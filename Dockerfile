# syntax=docker/dockerfile:1
#
# Tek servis imajı: derlenmiş SPA + FastAPI tek konteynerde, tek origin.
# Build context = repo kökü (deploy: `gcloud run deploy --source .`).

# ---- Frontend: SPA'yı derle (Vite -> dist) ----
FROM node:20-slim AS frontend
WORKDIR /fe
# Önce manifest'ler — katman önbelleği için kaynaktan ayrı
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Backend bağımlılıkları: uv ile çözümle ve kur ----
FROM python:3.12-slim AS builder

# uv binary'sini resmi imajdan al (reprodüksiyon için tam sürüm sabit)
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
# Önce yalnız bağımlılık manifestleri — katman önbelleği için kod'dan ayrı
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- Runtime: slim imaj, yalnız çalıştırma ----
FROM python:3.12-slim AS runtime

# Root olmayan kullanıcı
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

# Hazır sanal ortam ve uygulama kodu
COPY --from=builder /app/.venv /app/.venv
COPY backend/app ./app
# Derlenmiş SPA backend tarafından sunulur (app/static -> /api dışı tüm yollar)
COPY --from=frontend /fe/dist ./app/static

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080

USER appuser
EXPOSE 8080

# Cloud Run $PORT enjekte eder; yerelde varsayılan 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
