"""FastAPI application entrypoint for LeanViser CONSOLE backend.

Uygulama kurulumu, sağlık ucu (`/health`) ve modül router'larının montajı burada
yapılır. İş kuralı modüllerin domain/application katmanlarındadır; bu dosya yalnız
HTTP adapter'larını uygulamaya bağlar (hexagonal: composition root).
"""

from fastapi import FastAPI

from app.modules.finance.adapters.http.invoice_router import router as finance_router

app = FastAPI(title="LeanViser CONSOLE", version="0.1.0")
app.include_router(finance_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness ucu: servis ayakta mı?"""
    return {"status": "ok"}
