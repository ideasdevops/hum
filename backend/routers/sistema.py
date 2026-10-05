"""Estado, ajustes, voz y exportación."""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from config import WHISPER_DEFECTO, guardar_env, leer_env
from db import ajuste, db, filas, guardar_ajuste
from hum import proveedores, voz

router = APIRouter(prefix="/api", tags=["sistema"])

TABLAS_EXPORTABLES = ["persona", "autoevaluaciones", "inteligencias", "conversaciones", "mensajes", "recuerdos",
                      "observaciones", "metas", "acciones", "acciones_hechas", "seguimientos", "registros", "foco_diario"]


@router.get("/estado")
def estado():
    try:
        proveedor, modelo = proveedores.elegido()
        error = ""
    except proveedores.ErrorProveedor as e:
        proveedor, modelo, error = "", "", str(e)
    with db() as con:
        p = con.execute("SELECT nombre, como_llamarte, onboarding FROM persona WHERE id = 1").fetchone()
    return {
        "persona": dict(p),
        "proveedor": proveedor, "modelo": modelo or (proveedores.MODELO_ANTHROPIC if proveedor == "anthropic" else ""),
        "error_proveedor": error,
        "disponibles": proveedores.disponibles(),
        "voz": voz.estado(),
    }


class Ajustes(BaseModel):
    proveedor: str | None = None
    modelo: str | None = None
    anthropic_key: str | None = None
    voz: str | None = None
    voz_velocidad: float | None = None
    whisper_modelo: str | None = None
    voz_auto: bool | None = None


@router.get("/ajustes")
def ver_ajustes():
    return {
        "proveedor": ajuste("proveedor", "auto"),
        "modelo": ajuste("modelo", ""),
        "anthropic_key": bool(leer_env().get("ANTHROPIC_API_KEY")),
        "voz": ajuste("voz", "es_AR-daniela-high"),
        "voz_velocidad": float(ajuste("voz_velocidad", "1.0")),
        "whisper_modelo": ajuste("whisper_modelo", WHISPER_DEFECTO),
        "voz_auto": ajuste("voz_auto", "1") == "1",
        "voces": list(voz.VOCES),
        "ollama_modelos": proveedores.ollama_modelos(),
        "disponibles": proveedores.disponibles(),
    }


@router.put("/ajustes")
def guardar(a: Ajustes):
    if a.proveedor is not None:
        if a.proveedor not in ("auto", "anthropic", "claude-code", "ollama"):
            raise HTTPException(400, "Proveedor inválido.")
        guardar_ajuste("proveedor", a.proveedor)
    if a.modelo is not None:
        guardar_ajuste("modelo", a.modelo.strip())
    if a.anthropic_key is not None:
        clave = a.anthropic_key.strip()
        if clave and not clave.startswith("sk-ant-"):
            raise HTTPException(400, "Esa no parece una clave de Anthropic (empiezan con sk-ant-).")
        guardar_env({"ANTHROPIC_API_KEY": clave})
    if a.voz is not None:
        if a.voz not in voz.VOCES:
            raise HTTPException(400, "Voz desconocida.")
        guardar_ajuste("voz", a.voz)
    if a.voz_velocidad is not None:
        guardar_ajuste("voz_velocidad", str(max(0.6, min(1.6, a.voz_velocidad))))
    if a.whisper_modelo is not None:
        if a.whisper_modelo not in ("tiny", "base", "small", "medium"):
            raise HTTPException(400, "Modelo de Whisper inválido.")
        guardar_ajuste("whisper_modelo", a.whisper_modelo)
    if a.voz_auto is not None:
        guardar_ajuste("voz_auto", "1" if a.voz_auto else "0")
    return ver_ajustes()


@router.post("/voz/transcribir")
async def transcribir(request: Request):
    audio = await request.body()
    if not audio:
        raise HTTPException(400, "No llegó audio.")
    if len(audio) > 25 * 1024 * 1024:
        raise HTTPException(413, "El audio es demasiado largo.")
    tipo = request.headers.get("content-type", "audio/webm")
    sufijo = ".wav" if "wav" in tipo else ".ogg" if "ogg" in tipo else ".mp4" if "mp4" in tipo else ".webm"
    try:
        from starlette.concurrency import run_in_threadpool  # noqa: PLC0415
        texto = await run_in_threadpool(voz.transcribir, audio, sufijo)
    except voz.ErrorVoz as e:
        raise HTTPException(503, str(e))
    return {"texto": texto}


@router.post("/voz/precalentar")
def precalentar():
    """Carga Whisper y Piper en segundo plano (se llama al abrir el modo voz o al dictar)."""
    voz.precalentar()
    return {"ok": True}


class Decir(BaseModel):
    texto: str


@router.post("/voz/hablar")
def hablar(d: Decir):
    if not d.texto.strip():
        raise HTTPException(400, "No hay nada para decir.")
    try:
        wav = voz.sintetizar(d.texto[:3000])
    except voz.ErrorVoz as e:
        raise HTTPException(503, str(e))
    return Response(wav, media_type="audio/wav")


@router.get("/exportar")
def exportar():
    """Todo lo que HUM sabe, en un JSON. Los datos son de la persona."""
    with db() as con:
        datos = {t: filas(con.execute(f"SELECT * FROM {t}")) for t in TABLAS_EXPORTABLES}
    nombre = f"hum-{datetime.now():%Y%m%d-%H%M}.json"
    return JSONResponse({"exportado": datetime.now().isoformat(timespec="seconds"), **datos},
                        headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


class Confirmar(BaseModel):
    confirmacion: str


@router.post("/olvidar-todo")
def olvidar_todo(c: Confirmar):
    if c.confirmacion.strip().upper() != "OLVIDAR":
        raise HTTPException(400, "Escribí OLVIDAR para confirmar.")
    with db() as con:
        for t in reversed(TABLAS_EXPORTABLES):
            if t != "persona":
                con.execute(f"DELETE FROM {t}")
        con.execute("UPDATE persona SET nombre='', como_llamarte='', contexto='', valores='', onboarding=0 WHERE id = 1")
    return {"ok": True}
