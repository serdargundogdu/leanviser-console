"""FastAPI application entrypoint for LeanViser CONSOLE backend.

Yalnızca uygulama kurulumu ve sağlık ucu (`/health`) burada yer alır. İş kuralı
modüllerin (ör. finance) domain katmanında tutulur; bu dosya hiçbir domain
mantığı içermez (hexagonal: adapter katmanı dış dünyaya bağlar).
"""

from fastapi import FastAPI

app = FastAPI(title="LeanViser CONSOLE", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness ucu: servis ayakta mı?"""
    return {"status": "ok"}
