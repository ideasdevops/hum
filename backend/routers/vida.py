"""La vida de la persona según HUM: perfil, mapa de inteligencias, planes, hoy y recuerdos."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db import ahora, db, filas, hoy
from hum import contexto, proveedores
from hum.inteligencias import DIMENSIONES, IDS, INTELIGENCIAS, nombre, validas

router = APIRouter(prefix="/api", tags=["vida"])


# --- persona ---------------------------------------------------------------------

class Persona(BaseModel):
    nombre: str = ""
    como_llamarte: str = ""
    contexto: str = ""
    valores: str = ""
    onboarding: bool | None = None


@router.get("/persona")
def persona():
    with db() as con:
        return dict(con.execute("SELECT * FROM persona WHERE id = 1").fetchone())


@router.put("/persona")
def guardar_persona(p: Persona):
    with db() as con:
        con.execute(
            "UPDATE persona SET nombre=?, como_llamarte=?, contexto=?, valores=?, actualizada=? WHERE id = 1",
            (p.nombre.strip(), p.como_llamarte.strip(), p.contexto.strip(), p.valores.strip(), ahora()))
        if p.onboarding is not None:
            con.execute("UPDATE persona SET onboarding = ? WHERE id = 1", (int(p.onboarding),))
    return persona()


# --- mapa de las 12 inteligencias ----------------------------------------------------

class Autoevaluacion(BaseModel):
    valores: dict[str, int]


@router.get("/inteligencias")
def mapa():
    desde = (date.today() - timedelta(days=30)).isoformat()
    with db() as con:
        lecturas = {r["id"]: dict(r) for r in con.execute("SELECT * FROM inteligencias")}
        historial = filas(con.execute("SELECT inteligencia, valor, fecha FROM autoevaluaciones ORDER BY id"))
        obs = filas(con.execute(
            "SELECT inteligencia, texto, senal, fecha FROM observaciones ORDER BY id DESC LIMIT 400"))
        hechas = {r["inteligencia"]: r["n"] for r in con.execute(
            """SELECT a.inteligencia, COUNT(*) AS n FROM acciones_hechas h JOIN acciones a ON a.id = h.accion_id
               WHERE h.fecha >= ? GROUP BY a.inteligencia""", (desde,))}
        metas = filas(con.execute("SELECT id, titulo, inteligencias, estado FROM metas WHERE estado = 'activa'"))
    actual = contexto.autopercepcion_actual()
    salida = []
    for i in INTELIGENCIAS:
        propias = [o for o in obs if o["inteligencia"] == i["id"]]
        recientes = [o for o in propias if o["fecha"][:10] >= desde]
        salida.append({
            **i,
            "autopercepcion": actual.get(i["id"]),
            "historial": [h for h in historial if h["inteligencia"] == i["id"]],
            "lectura": lecturas.get(i["id"], {}).get("lectura", ""),
            "lectura_fecha": lecturas.get(i["id"], {}).get("actualizada"),
            "observaciones": propias[:8],
            "actividad_30d": {
                "observaciones": len(recientes),
                "avances": sum(1 for o in recientes if o["senal"] > 0),
                "dificultades": sum(1 for o in recientes if o["senal"] < 0),
                "acciones_hechas": hechas.get(i["id"], 0),
            },
            "metas": [m for m in metas if i["id"] in m["inteligencias"].split(",")],
        })
    return {"dimensiones": DIMENSIONES, "inteligencias": salida}


@router.post("/autoevaluacion")
def autoevaluar(a: Autoevaluacion):
    t = ahora()
    with db() as con:
        for k, v in a.valores.items():
            if k in IDS and 1 <= int(v) <= 10:
                con.execute("INSERT INTO autoevaluaciones (inteligencia, valor, fecha) VALUES (?,?,?)", (k, int(v), t))
    return {"ok": True}


# --- planes: metas y acciones ---------------------------------------------------------

class Meta(BaseModel):
    titulo: str = Field(min_length=1)
    porque: str = ""
    area: str = ""
    inteligencias: list[str] = []
    deseo: str = ""
    resultado: str = ""
    obstaculo: str = ""
    plan: str = ""
    horizonte: str = "mes"
    estado: str = "activa"


class CambioMeta(BaseModel):
    titulo: str | None = None
    porque: str | None = None
    area: str | None = None
    deseo: str | None = None
    resultado: str | None = None
    obstaculo: str | None = None
    plan: str | None = None
    horizonte: str | None = None
    estado: str | None = None
    progreso: int | None = Field(default=None, ge=0, le=100)


class Accion(BaseModel):
    titulo: str = Field(min_length=1)
    meta_id: int | None = None
    inteligencia: str = ""
    frecuencia: str = "una_vez"
    si_entonces: str = ""
    estado: str = "activa"


class CambioAccion(BaseModel):
    titulo: str | None = None
    meta_id: int | None = None
    inteligencia: str | None = None
    frecuencia: str | None = None
    si_entonces: str | None = None
    estado: str | None = None


ESTADOS_META = {"propuesta", "activa", "pausada", "lograda", "descartada"}
ESTADOS_ACCION = {"propuesta", "activa", "hecha", "descartada"}


def _actualizar(con, tabla: str, id_: int, cambios: dict, estados: set):
    datos = {k: v for k, v in cambios.items() if v is not None}
    if "estado" in datos and datos["estado"] not in estados:
        raise HTTPException(400, "Estado inválido.")
    if not datos:
        return
    if tabla == "metas":
        datos["actualizada"] = ahora()
    sets = ", ".join(f"{k} = ?" for k in datos)
    con.execute(f"UPDATE {tabla} SET {sets} WHERE id = ?", (*datos.values(), id_))


@router.get("/planes")
def planes():
    semana = (date.today() - timedelta(days=6)).isoformat()
    with db() as con:
        metas = filas(con.execute(
            "SELECT * FROM metas WHERE estado != 'descartada' ORDER BY CASE estado WHEN 'propuesta' THEN 0 WHEN 'activa' THEN 1 "
            "WHEN 'pausada' THEN 2 ELSE 3 END, actualizada DESC"))
        acciones = filas(con.execute(
            """SELECT a.*, (SELECT 1 FROM acciones_hechas h WHERE h.accion_id = a.id AND h.fecha = ?) AS hecha_hoy,
                      (SELECT COUNT(*) FROM acciones_hechas h WHERE h.accion_id = a.id AND h.fecha >= ?) AS hechas_7d,
                      (SELECT COUNT(*) FROM acciones_hechas h WHERE h.accion_id = a.id) AS hechas_total
               FROM acciones a WHERE a.estado != 'descartada' ORDER BY a.id DESC""", (hoy(), semana)))
    for m in metas:
        m["inteligencias"] = [x for x in m["inteligencias"].split(",") if x]
    return {"metas": metas, "acciones": acciones}


@router.post("/metas")
def crear_meta(m: Meta):
    t = ahora()
    with db() as con:
        cur = con.execute(
            """INSERT INTO metas (titulo, porque, area, inteligencias, deseo, resultado, obstaculo, plan, horizonte, estado,
               creada, actualizada) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (m.titulo, m.porque, m.area, ",".join(validas(m.inteligencias)), m.deseo, m.resultado, m.obstaculo,
             m.plan, m.horizonte, m.estado if m.estado in ESTADOS_META else "activa", t, t))
    return {"id": cur.lastrowid}


@router.patch("/metas/{mid}")
def cambiar_meta(mid: int, c: CambioMeta):
    with db() as con:
        _actualizar(con, "metas", mid, c.model_dump(), ESTADOS_META)
        if c.estado == "lograda":
            con.execute("UPDATE metas SET progreso = 100 WHERE id = ?", (mid,))
        if c.estado in ("activa", "descartada"):
            # Aceptar o descartar una meta propuesta arrastra sus acciones propuestas.
            nuevo = "activa" if c.estado == "activa" else "descartada"
            con.execute("UPDATE acciones SET estado = ? WHERE meta_id = ? AND estado = 'propuesta'", (nuevo, mid))
    return {"ok": True}


@router.post("/acciones")
def crear_accion(a: Accion):
    with db() as con:
        cur = con.execute(
            "INSERT INTO acciones (meta_id, titulo, inteligencia, frecuencia, si_entonces, estado, creada) VALUES (?,?,?,?,?,?,?)",
            (a.meta_id, a.titulo, a.inteligencia if a.inteligencia in IDS else "", a.frecuencia, a.si_entonces,
             a.estado if a.estado in ESTADOS_ACCION else "activa", ahora()))
    return {"id": cur.lastrowid}


@router.patch("/acciones/{aid}")
def cambiar_accion(aid: int, c: CambioAccion):
    with db() as con:
        _actualizar(con, "acciones", aid, c.model_dump(), ESTADOS_ACCION)
    return {"ok": True}


class Hecha(BaseModel):
    hecha: bool = True
    nota: str = ""


@router.post("/acciones/{aid}/hoy")
def marcar_hoy(aid: int, h: Hecha):
    with db() as con:
        a = con.execute("SELECT * FROM acciones WHERE id = ?", (aid,)).fetchone()
        if not a:
            raise HTTPException(404, "No existe esa acción.")
        if h.hecha:
            con.execute("INSERT OR IGNORE INTO acciones_hechas (accion_id, fecha, nota) VALUES (?,?,?)", (aid, hoy(), h.nota))
            if a["frecuencia"] == "una_vez":
                con.execute("UPDATE acciones SET estado = 'hecha' WHERE id = ?", (aid,))
        else:
            con.execute("DELETE FROM acciones_hechas WHERE accion_id = ? AND fecha = ?", (aid, hoy()))
            if a["frecuencia"] == "una_vez" and a["estado"] == "hecha":
                con.execute("UPDATE acciones SET estado = 'activa' WHERE id = ?", (aid,))
    return {"ok": True}


# --- hoy ---------------------------------------------------------------------------

class Registro(BaseModel):
    animo: int | None = Field(default=None, ge=1, le=10)
    energia: int | None = Field(default=None, ge=1, le=10)
    sueno: float | None = Field(default=None, ge=0, le=24)
    nota: str = ""


def _saludo(nombre_p: str) -> str:
    h = datetime.now().hour
    base = "Buen día" if 5 <= h < 13 else "Buenas tardes" if 13 <= h < 20 else "Buenas noches"
    return f"{base}, {nombre_p}" if nombre_p else base


@router.get("/hoy")
def hoy_resumen():
    with db() as con:
        p = con.execute("SELECT nombre, como_llamarte, onboarding FROM persona WHERE id = 1").fetchone()
        registro = con.execute("SELECT * FROM registros WHERE fecha = ?", (hoy(),)).fetchone()
        acciones = filas(con.execute(
            """SELECT a.*, m.titulo AS meta_titulo,
                      (SELECT 1 FROM acciones_hechas h WHERE h.accion_id = a.id AND h.fecha = ?) AS hecha_hoy
               FROM acciones a LEFT JOIN metas m ON m.id = a.meta_id
               WHERE a.estado = 'activa' OR (a.estado = 'hecha' AND EXISTS
                     (SELECT 1 FROM acciones_hechas h WHERE h.accion_id = a.id AND h.fecha = ?))
               ORDER BY a.id""", (hoy(), hoy())))
        seguimientos = filas(con.execute(
            "SELECT * FROM seguimientos WHERE estado = 'pendiente' AND fecha <= ? ORDER BY fecha", (hoy(),)))
        foco = con.execute("SELECT * FROM foco_diario WHERE fecha = ?", (hoy(),)).fetchone()
        propuestas = con.execute(
            "SELECT (SELECT COUNT(*) FROM metas WHERE estado='propuesta') + (SELECT COUNT(*) FROM acciones WHERE estado='propuesta')"
        ).fetchone()[0]
        racha = _racha(con)
    return {
        "saludo": _saludo(p["como_llamarte"] or p["nombre"]),
        "onboarding": bool(p["onboarding"]),
        "registro": dict(registro) if registro else None,
        "acciones": acciones,
        "seguimientos": seguimientos,
        "foco": {**dict(foco), "nombre": nombre(foco["inteligencia"])} if foco else None,
        "propuestas": propuestas,
        "racha": racha,
    }


def _racha(con) -> int:
    """Días seguidos (hasta hoy o ayer) con al menos una acción hecha."""
    dias = {r[0] for r in con.execute("SELECT DISTINCT fecha FROM acciones_hechas WHERE fecha >= ?",
                                      ((date.today() - timedelta(days=400)).isoformat(),))}
    d = date.today() if date.today().isoformat() in dias else date.today() - timedelta(days=1)
    n = 0
    while d.isoformat() in dias:
        n += 1
        d -= timedelta(days=1)
    return n


@router.put("/registro")
def registrar(r: Registro):
    with db() as con:
        con.execute(
            """INSERT INTO registros (fecha, animo, energia, sueno, nota) VALUES (?,?,?,?,?)
               ON CONFLICT(fecha) DO UPDATE SET animo=excluded.animo, energia=excluded.energia,
               sueno=excluded.sueno, nota=excluded.nota""", (hoy(), r.animo, r.energia, r.sueno, r.nota))
    return {"ok": True}


@router.get("/registros")
def registros(dias: int = 30):
    with db() as con:
        return filas(con.execute("SELECT * FROM registros WHERE fecha >= ? ORDER BY fecha",
                                 ((date.today() - timedelta(days=dias)).isoformat(),)))


ESQUEMA_FOCO = {
    "type": "object", "additionalProperties": False, "required": ["inteligencia", "texto"],
    "properties": {"inteligencia": {"type": "string", "enum": IDS}, "texto": {"type": "string"}},
}


@router.post("/foco")
def generar_foco(rehacer: bool = False):
    with db() as con:
        if not rehacer:
            f = con.execute("SELECT * FROM foco_diario WHERE fecha = ?", (hoy(),)).fetchone()
            if f:
                return {**dict(f), "nombre": nombre(f["inteligencia"])}
    sistema = ("Sos HUM, la IA humanizada de JFlowOS. Elegí UNA de las 12 inteligencias para el foco de hoy de "
               "esta persona y proponé una sola práctica concreta, chica (5-20 minutos) y con respaldo, conectada "
               "con su vida, sus metas y su check-in si lo hay. Variá respecto de días anteriores. Priorizá lo que "
               "más la ayude hoy (si durmió poco, el Cuerpo primero). Texto: 2 frases, de vos, español rioplatense, "
               "cálido y concreto, sin saludo.\n\nInteligencias:\n"
               + "\n".join(f"- {i['id']}: {i['nombre']} — {i['definicion']}" for i in INTELIGENCIAS))
    with db() as con:
        previos = filas(con.execute("SELECT fecha, inteligencia FROM foco_diario ORDER BY fecha DESC LIMIT 6"))
    pedido = contexto.armar("") + "\n\nFocos anteriores: " + (", ".join(f"{p['fecha']} {p['inteligencia']}" for p in previos) or "ninguno")
    try:
        d = proveedores.estructurado(sistema, pedido, ESQUEMA_FOCO)
    except proveedores.ErrorProveedor as e:
        raise HTTPException(503, str(e))
    if d.get("inteligencia") not in IDS:
        raise HTTPException(502, "El modelo no eligió una inteligencia válida.")
    with db() as con:
        con.execute("INSERT INTO foco_diario (fecha, inteligencia, texto) VALUES (?,?,?) "
                    "ON CONFLICT(fecha) DO UPDATE SET inteligencia=excluded.inteligencia, texto=excluded.texto",
                    (hoy(), d["inteligencia"], d["texto"].strip()))
    return {"fecha": hoy(), "inteligencia": d["inteligencia"], "texto": d["texto"].strip(), "nombre": nombre(d["inteligencia"])}


class CambioSeguimiento(BaseModel):
    estado: str


@router.patch("/seguimientos/{sid}")
def cambiar_seguimiento(sid: int, c: CambioSeguimiento):
    if c.estado not in ("pendiente", "hecho", "descartado"):
        raise HTTPException(400, "Estado inválido.")
    with db() as con:
        con.execute("UPDATE seguimientos SET estado = ? WHERE id = ?", (c.estado, sid))
    return {"ok": True}


# --- lo que HUM sabe ----------------------------------------------------------------

class CambioRecuerdo(BaseModel):
    contenido: str | None = None
    importancia: int | None = Field(default=None, ge=1, le=5)


@router.get("/recuerdos")
def recuerdos(q: str = ""):
    with db() as con:
        if q.strip():
            consulta = contexto._consulta_fts(q) or '""'
            return filas(con.execute(
                """SELECT r.* FROM recuerdos_fts f JOIN recuerdos r ON r.id = f.rowid
                   WHERE recuerdos_fts MATCH ? AND r.activo = 1 ORDER BY rank LIMIT 200""", (consulta,)))
        return filas(con.execute("SELECT * FROM recuerdos WHERE activo = 1 ORDER BY id DESC LIMIT 500"))


@router.patch("/recuerdos/{rid}")
def cambiar_recuerdo(rid: int, c: CambioRecuerdo):
    with db() as con:
        if c.contenido is not None:
            con.execute("UPDATE recuerdos SET contenido = ? WHERE id = ?", (c.contenido.strip(), rid))
        if c.importancia is not None:
            con.execute("UPDATE recuerdos SET importancia = ? WHERE id = ?", (c.importancia, rid))
    return {"ok": True}


@router.delete("/recuerdos/{rid}")
def olvidar(rid: int):
    with db() as con:
        con.execute("DELETE FROM recuerdos WHERE id = ?", (rid,))
    return {"ok": True}


@router.delete("/observaciones/{oid}")
def borrar_observacion(oid: int):
    with db() as con:
        con.execute("DELETE FROM observaciones WHERE id = ?", (oid,))
    return {"ok": True}
