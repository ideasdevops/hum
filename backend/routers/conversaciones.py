"""Conversar con HUM: chats por texto o voz, con respuesta en vivo (SSE)."""
import json
import logging
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db import ahora, db, filas
from hum import contexto, digestion, proveedores, seguridad
from hum.prompts import sistema_estable

router = APIRouter(prefix="/api/conversaciones", tags=["conversaciones"])
log = logging.getLogger("hum.chat")

HISTORIAL_MAX = 40          # mensajes que viajan completos al modelo
DIGERIR_CADA = 6            # mensajes de la persona sin digerir que disparan la digestión


class Nueva(BaseModel):
    modo: str = "texto"


class Mensaje(BaseModel):
    texto: str = Field(min_length=1, max_length=20000)
    modo: str = "texto"
    por_voz: bool = False


@router.get("")
def listar():
    with db() as con:
        return filas(con.execute(
            """SELECT c.*, (SELECT COUNT(*) FROM mensajes m WHERE m.conversacion_id = c.id) AS mensajes
               FROM conversaciones c WHERE archivada = 0 ORDER BY actualizada DESC LIMIT 200"""))


@router.post("")
def crear(n: Nueva):
    with db() as con:
        cur = con.execute("INSERT INTO conversaciones (modo, creada, actualizada) VALUES (?,?,?)",
                          (n.modo, ahora(), ahora()))
        return {"id": cur.lastrowid}


@router.get("/{cid}")
def ver(cid: int):
    with db() as con:
        c = con.execute("SELECT * FROM conversaciones WHERE id = ?", (cid,)).fetchone()
        if not c:
            raise HTTPException(404, "No existe esa conversación.")
        return {**dict(c), "mensajes": filas(con.execute(
            "SELECT id, rol, contenido, por_voz, creado FROM mensajes WHERE conversacion_id = ? ORDER BY id", (cid,)))}


@router.delete("/{cid}")
def borrar(cid: int):
    with db() as con:
        con.execute("DELETE FROM conversaciones WHERE id = ?", (cid,))
    return {"ok": True}


@router.post("/{cid}/digerir")
def digerir_ahora(cid: int):
    try:
        return digestion.digerir(cid)
    except proveedores.ErrorProveedor as e:
        raise HTTPException(503, str(e))


def _digerir_en_fondo(cid: int):
    def tarea():
        try:
            digestion.digerir(cid)
        except Exception as e:  # noqa: BLE001
            log.warning("digestión de %s falló: %s", cid, e)
    threading.Thread(target=tarea, daemon=True).start()


def _evento(datos: dict) -> str:
    return f"data: {json.dumps(datos, ensure_ascii=False)}\n\n"


@router.post("/{cid}/mensaje")
def enviar(cid: int, m: Mensaje):
    texto = m.texto.strip()
    with db() as con:
        c = con.execute("SELECT * FROM conversaciones WHERE id = ?", (cid,)).fetchone()
        if not c:
            raise HTTPException(404, "No existe esa conversación.")
        con.execute("INSERT INTO mensajes (conversacion_id, rol, contenido, por_voz, creado) VALUES (?,?,?,?,?)",
                    (cid, "user", texto, int(m.por_voz), ahora()))
        historial = filas(con.execute(
            "SELECT rol, contenido FROM mensajes WHERE conversacion_id = ? ORDER BY id DESC LIMIT ?", (cid, HISTORIAL_MAX)))[::-1]
        con.execute("UPDATE conversaciones SET actualizada = ? WHERE id = ?", (ahora(), cid))

    # La API pide alternar persona/HUM empezando por la persona: se juntan seguidos del mismo rol.
    mensajes: list[dict] = []
    for h in historial:
        rol = "user" if h["rol"] == "user" else "assistant"
        if mensajes and mensajes[-1]["role"] == rol:
            mensajes[-1]["content"] += "\n\n" + h["contenido"]
        else:
            mensajes.append({"role": rol, "content": h["contenido"]})
    while mensajes and mensajes[0]["role"] != "user":
        mensajes.pop(0)

    alerta = seguridad.revisar(texto)
    vivo = contexto.armar(texto, m.modo)
    if alerta:
        vivo += "\n\n" + seguridad.instruccion(alerta)

    def flujo():
        if alerta:
            yield _evento({"tipo": "alerta", "clase": alerta["tipo"], "lineas": alerta["lineas"]})
        respuesta = []
        try:
            for trozo in proveedores.conversar(sistema_estable(), vivo, mensajes, rapido=(m.modo == "voz")):
                respuesta.append(trozo)
                yield _evento({"tipo": "texto", "t": trozo})
        except proveedores.ErrorProveedor as e:
            yield _evento({"tipo": "error", "detalle": str(e)})
        except Exception as e:  # noqa: BLE001
            log.exception("error conversando")
            yield _evento({"tipo": "error", "detalle": f"Algo falló: {e}"})
        final = "".join(respuesta).strip()
        if not final:
            return
        with db() as con:
            cur = con.execute("INSERT INTO mensajes (conversacion_id, rol, contenido, por_voz, creado) VALUES (?,?,?,?,?)",
                              (cid, "assistant", final, int(m.modo == "voz"), ahora()))
            con.execute("UPDATE conversaciones SET actualizada = ? WHERE id = ?", (ahora(), cid))
            sin_digerir = con.execute(
                "SELECT COUNT(*) FROM mensajes WHERE conversacion_id = ? AND rol = 'user' AND id > ?",
                (cid, c["digerida_hasta"])).fetchone()[0]
        yield _evento({"tipo": "fin", "id": cur.lastrowid})
        if sin_digerir >= DIGERIR_CADA:
            _digerir_en_fondo(cid)

    return StreamingResponse(flujo(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
