"""FastAPI application entrypoint for LeanViser CONSOLE backend.

Uygulama kurulumu, sağlık ucu (`/health`), modül router'larının montajı ve (prod'da)
derlenmiş SPA'nın sunumu burada yapılır. İş kuralı modüllerin domain/application
katmanlarındadır; bu dosya yalnız HTTP adapter'larını uygulamaya bağlar
(hexagonal: composition root).

Tek servis topolojisi: API'ler `/api` altında servis edilir; geri kalan tüm yollar
derlenmiş SPA'ya (index.html) düşer. Böylece frontend ve backend tek origin paylaşır
(CORS yok), arayüz `/api/...` çağırır. Bu, geliştirme (Vite proxy `/api`) ile prod'da
birebir aynıdır. `app/static` yoksa (yerel geliştirme) SPA sunumu atlanır; arayüz
Vite (:5173) üzerinden döner.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.modules.finance.adapters.http.invoice_router import router as finance_router

app = FastAPI(title="LeanViser CONSOLE", version="0.1.0")
app.include_router(finance_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness ucu: servis ayakta mı?"""
    return {"status": "ok"}


# Derlenmiş SPA (prod imajında app/static; yerelde yoksa atlanır).
_STATIC_DIR = Path(os.environ.get("FRONTEND_DIST", str(Path(__file__).resolve().parent / "static")))

if _STATIC_DIR.is_dir():
    _INDEX = _STATIC_DIR / "index.html"

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        """SPA sunumu: istenen yol gerçek bir dosyaysa onu, değilse index.html.

        `/api` ve `/health` üstte eşleştiğinden buraya yalnız SPA yolları düşer
        (client-side routing; ör. /finance yenilemesi de index.html döner).
        """
        target = _STATIC_DIR / full_path
        try:
            target.resolve().relative_to(_STATIC_DIR.resolve())  # path traversal guard
        except ValueError:
            return FileResponse(_INDEX)
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(_INDEX)
