"""
HUM — la inteligencia humanizada de JFlowOS (UEI · IdeasDevOps & Disruptia AI).

Servidor local: escucha solo en 127.0.0.1. Sirve la API y la interfaz compilada.
Arranque:  venv/bin/uvicorn main:app --host 127.0.0.1 --port 8412
"""
import logging
import threading
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db
from config import FRONTEND_DIST
from hum import digestion, voz
from routers import conversaciones, sistema, vida

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("hum")

db.iniciar()

app = FastAPI(title="HUM", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.include_router(conversaciones.router)
app.include_router(vida.router)
app.include_router(sistema.router)


def _digestor():
    """Cada minuto digiere las conversaciones que quedaron quietas con mensajes nuevos."""
    while True:
        time.sleep(60)
        try:
            for cid in digestion.pendientes_de_digerir():
                digestion.digerir(cid)
        except Exception as e:  # noqa: BLE001
            log.warning("digestor: %s", e)


@app.on_event("startup")
def _arranque():
    threading.Thread(target=_digestor, daemon=True).start()
    if db.ajuste("voz_precargar", "1") == "1":
        voz.precalentar()


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    def interfaz(ruta: str):
        archivo = FRONTEND_DIST / ruta
        if ruta and archivo.is_file() and FRONTEND_DIST in archivo.resolve().parents:
            return FileResponse(archivo)
        return FileResponse(FRONTEND_DIST / "index.html")
