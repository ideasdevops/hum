"""
Digestión: lo que convierte una conversación en mejora real.

Hoy la gente le habla a una IA de su trabajo, sus emociones o sus dudas, y eso no
queda en ningún lado. HUM, después de cada tramo de conversación, la «digiere»:

  · recuerdos      lo que aprendió de su vida (para no volver a preguntarlo)
  · observaciones  evidencia concreta sobre alguna de las 12 inteligencias
  · lecturas       actualiza lo que entiende de cada inteligencia tocada
  · propuestas     metas (con WOOP) y acciones pequeñas (con si-entonces) —
                   quedan como PROPUESTA hasta que la persona las acepte
  · seguimientos   qué retomar y cuándo («¿cómo te fue en la entrevista?»)
  · título         para encontrar la conversación después

Se dispara cuando la conversación queda quieta unos minutos, cada tantos mensajes,
o a mano. Solo procesa los mensajes nuevos desde la última digestión.
"""
import logging
import threading
from datetime import date, timedelta

from db import ahora, db, filas
from hum import proveedores
from hum.inteligencias import IDS, INTELIGENCIAS, validas

log = logging.getLogger("hum.digestion")
_candado = threading.Lock()

TIPOS_RECUERDO = ["hecho", "experiencia", "emocion", "aprendizaje", "vinculo", "valor", "preferencia", "salud", "trabajo", "meta"]
FRECUENCIAS = ["una_vez", "diaria", "semanal", "dias_semana"]

_lista_ids = {"type": "array", "items": {"type": "string", "enum": IDS}}

ESQUEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["titulo", "recuerdos", "observaciones", "lecturas", "metas_propuestas",
                 "acciones_propuestas", "seguimientos", "perfil"],
    "properties": {
        "titulo": {"type": "string", "description": "Título corto (3-7 palabras), cálido y discreto: nunca palabras alarmantes ni clínicas (para un momento de crisis: «Un momento difícil»)"},
        "recuerdos": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["tipo", "contenido", "inteligencias", "importancia"],
            "properties": {
                "tipo": {"type": "string", "enum": TIPOS_RECUERDO},
                "contenido": {"type": "string"},
                "inteligencias": _lista_ids,
                "importancia": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
            }}},
        "observaciones": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["inteligencia", "texto", "senal"],
            "properties": {
                "inteligencia": {"type": "string", "enum": IDS},
                "texto": {"type": "string"},
                "senal": {"type": "integer", "enum": [-1, 0, 1]},
            }}},
        "lecturas": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["inteligencia", "lectura"],
            "properties": {
                "inteligencia": {"type": "string", "enum": IDS},
                "lectura": {"type": "string"},
            }}},
        "metas_propuestas": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["titulo", "porque", "area", "inteligencias", "deseo", "resultado", "obstaculo", "plan", "horizonte"],
            "properties": {
                "titulo": {"type": "string"}, "porque": {"type": "string"}, "area": {"type": "string"},
                "inteligencias": _lista_ids, "deseo": {"type": "string"}, "resultado": {"type": "string"},
                "obstaculo": {"type": "string"}, "plan": {"type": "string"},
                "horizonte": {"type": "string", "enum": ["semana", "mes", "trimestre", "año"]},
            }}},
        "acciones_propuestas": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["titulo", "inteligencia", "frecuencia", "si_entonces", "meta"],
            "properties": {
                "titulo": {"type": "string"}, "inteligencia": {"type": "string", "enum": IDS},
                "frecuencia": {"type": "string", "enum": FRECUENCIAS},
                "si_entonces": {"type": "string"},
                "meta": {"type": "string", "description": "Título exacto de la meta (activa o propuesta) a la que pertenece, o vacío"},
            }}},
        "seguimientos": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["texto", "en_dias"],
            "properties": {"texto": {"type": "string"}, "en_dias": {"type": "integer"}},
        }},
        "perfil": {
            "type": "object", "additionalProperties": False,
            "required": ["nombre", "como_llamarte", "contexto_nuevo", "valores_nuevos"],
            "properties": {
                "nombre": {"type": "string"}, "como_llamarte": {"type": "string"},
                "contexto_nuevo": {"type": "string"}, "valores_nuevos": {"type": "string"},
            }},
    },
}

SISTEMA = """Sos el proceso de memoria de HUM, la IA humanizada de JFlowOS. Leés un tramo de
conversación entre HUM y una persona y devolvés SOLO lo que vale la pena guardar para
acompañarla mejor, en español rioplatense, en JSON según el esquema.

Las 12 inteligencias (id: nombre — definición):
{marco}

Criterios:
- recuerdos: hechos y experiencias de SU vida que sirvan en futuras charlas (familia, trabajo,
  salud, emociones relevantes, valores, preferencias, logros, dificultades). Frases autocontenidas
  en tercera persona («Tiene una hija de 6 años, Ema»). Nada que ya esté en lo que sabe HUM.
  Nada trivial. Importancia 5 = central en su vida. Si no hay nada nuevo, lista vacía.
- observaciones: evidencia CONCRETA de lo dicho, ligada a una inteligencia. senal 1 = fortaleza o
  avance, -1 = dificultad, 0 = dato neutro. No inventes ni diagnostiques: describí conductas y dichos.
- lecturas: solo para las inteligencias que este tramo realmente tocó; una o dos frases que
  integren la lectura anterior con lo nuevo (cómo está hoy, qué la fortalece, qué la frena).
- metas_propuestas: SOLO si la persona expresó un deseo, problema o intención que pide un plan y no
  existe ya como meta. Formulá WOOP con sus palabras: deseo, mejor resultado, obstáculo INTERNO
  principal, plan «si <obstáculo>, entonces <acción>». Mejor ninguna que una forzada.
- acciones_propuestas: pasos pequeños y concretos (versión mínima, menos de 5 minutos para empezar),
  con un ancla «después de <rutina existente>, voy a <acción>». Si la persona ya aceptó o rechazó
  algo parecido en la charla, respetalo. Máximo 3.
- seguimientos: lo que HUM debería retomar más adelante (un evento próximo, un compromiso, una emoción
  difícil) y en cuántos días (0 = hoy, 1 = mañana…).
- perfil: nombre o forma de llamarle si la dijo; contexto_nuevo y valores_nuevos solo con datos
  nuevos (vacío si no hay).
- Si la persona dijo algo que indica riesgo para su vida o la de otros, registralo como recuerdo
  tipo «salud» importancia 5 y un seguimiento en 0 días para preguntarle cómo está.
"""


def _marco_breve() -> str:
    return "\n".join(f"- {i['id']}: {i['nombre']} — {i['definicion']}" for i in INTELIGENCIAS)


def _lo_que_ya_sabe(con) -> str:
    p = dict(con.execute("SELECT * FROM persona WHERE id = 1").fetchone())
    rec = filas(con.execute("SELECT contenido FROM recuerdos WHERE activo = 1 ORDER BY id DESC LIMIT 60"))
    metas = filas(con.execute("SELECT titulo, estado FROM metas WHERE estado IN ('activa','propuesta','pausada')"))
    acciones = filas(con.execute("SELECT titulo, estado FROM acciones WHERE estado IN ('activa','propuesta')"))
    lect = filas(con.execute("SELECT id, lectura FROM inteligencias WHERE lectura != ''"))
    partes = [f"Perfil: nombre={p['nombre']!r}, como_llamarte={p['como_llamarte']!r}, contexto={p['contexto']!r}, valores={p['valores']!r}"]
    partes.append("Recuerdos ya guardados:\n" + "\n".join(f"- {r['contenido']}" for r in rec) if rec else "Recuerdos: ninguno.")
    partes.append("Metas: " + ("; ".join(f"{m['titulo']} ({m['estado']})" for m in metas) or "ninguna"))
    partes.append("Acciones: " + ("; ".join(f"{a['titulo']} ({a['estado']})" for a in acciones) or "ninguna"))
    partes.append("Lecturas actuales:\n" + "\n".join(f"- {l['id']}: {l['lectura']}" for l in lect) if lect else "Lecturas: ninguna.")
    return "\n\n".join(partes)


def digerir(conversacion_id: int) -> dict:
    """Digiere los mensajes nuevos de una conversación. Devuelve un resumen de lo guardado."""
    with _candado:
        with db() as con:
            conv = con.execute("SELECT * FROM conversaciones WHERE id = ?", (conversacion_id,)).fetchone()
            if not conv:
                return {"ok": False, "motivo": "no existe"}
            nuevos = filas(con.execute(
                "SELECT * FROM mensajes WHERE conversacion_id = ? AND id > ? ORDER BY id",
                (conversacion_id, conv["digerida_hasta"])))
            if not any(m["rol"] == "user" for m in nuevos):
                return {"ok": True, "nada": True}
            previos = filas(con.execute(
                "SELECT * FROM mensajes WHERE conversacion_id = ? AND id <= ? ORDER BY id DESC LIMIT 6",
                (conversacion_id, conv["digerida_hasta"])))[::-1]
            sabido = _lo_que_ya_sabe(con)

        def fmt(ms):
            return "\n".join(f"{'Persona' if m['rol'] == 'user' else 'HUM'}: {m['contenido']}" for m in ms)

        pedido = (f"<lo_que_hum_ya_sabe>\n{sabido}\n</lo_que_hum_ya_sabe>\n\n"
                  + (f"<contexto_previo_ya_digerido>\n{fmt(previos)}\n</contexto_previo_ya_digerido>\n\n" if previos else "")
                  + f"<tramo_nuevo>\n{fmt(nuevos)}\n</tramo_nuevo>\n\nFecha de hoy: {date.today().isoformat()}.")
        datos = proveedores.estructurado(SISTEMA.format(marco=_marco_breve()), pedido, ESQUEMA)
        resumen = _guardar(conversacion_id, conv, datos, nuevos[-1]["id"])
        log.info("conversación %s digerida: %s", conversacion_id, resumen)
        return {"ok": True, **resumen}


def _guardar(cid: int, conv, d: dict, ultimo_id: int) -> dict:
    t = ahora()
    cuenta = {"recuerdos": 0, "observaciones": 0, "metas": 0, "acciones": 0, "seguimientos": 0}
    with db() as con:
        if d.get("titulo") and conv["titulo"] == "Conversación nueva":
            con.execute("UPDATE conversaciones SET titulo = ? WHERE id = ?", (d["titulo"][:80], cid))
        for r in d.get("recuerdos", []):
            if r.get("contenido", "").strip():
                con.execute(
                    "INSERT INTO recuerdos (tipo, contenido, inteligencias, importancia, fecha, conversacion_id) VALUES (?,?,?,?,?,?)",
                    (r.get("tipo", "hecho"), r["contenido"].strip(), ",".join(validas(r.get("inteligencias"))),
                     max(1, min(5, int(r.get("importancia", 3)))), t, cid))
                cuenta["recuerdos"] += 1
        for o in d.get("observaciones", []):
            if o.get("inteligencia") in IDS and o.get("texto", "").strip():
                con.execute("INSERT INTO observaciones (inteligencia, texto, senal, fecha, conversacion_id) VALUES (?,?,?,?,?)",
                            (o["inteligencia"], o["texto"].strip(), max(-1, min(1, int(o.get("senal", 0)))), t, cid))
                cuenta["observaciones"] += 1
        for l in d.get("lecturas", []):
            if l.get("inteligencia") in IDS and l.get("lectura", "").strip():
                con.execute(
                    "INSERT INTO inteligencias (id, lectura, actualizada) VALUES (?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET lectura = excluded.lectura, actualizada = excluded.actualizada",
                    (l["inteligencia"], l["lectura"].strip(), t))
        metas_por_titulo = {r["titulo"].lower(): r["id"] for r in con.execute(
            "SELECT id, titulo FROM metas WHERE estado IN ('activa','propuesta','pausada')")}
        for m in d.get("metas_propuestas", []):
            if not m.get("titulo", "").strip() or m["titulo"].lower() in metas_por_titulo:
                continue
            cur = con.execute(
                """INSERT INTO metas (titulo, porque, area, inteligencias, deseo, resultado, obstaculo, plan, horizonte,
                   estado, origen, conversacion_id, creada, actualizada) VALUES (?,?,?,?,?,?,?,?,?, 'propuesta','hum',?,?,?)""",
                (m["titulo"].strip(), m.get("porque", ""), m.get("area", ""), ",".join(validas(m.get("inteligencias"))),
                 m.get("deseo", ""), m.get("resultado", ""), m.get("obstaculo", ""), m.get("plan", ""),
                 m.get("horizonte", "mes"), cid, t, t))
            metas_por_titulo[m["titulo"].lower()] = cur.lastrowid
            cuenta["metas"] += 1
        existentes = {r[0].lower() for r in con.execute("SELECT titulo FROM acciones WHERE estado IN ('activa','propuesta')")}
        for a in d.get("acciones_propuestas", [])[:3]:
            if not a.get("titulo", "").strip() or a["titulo"].lower() in existentes:
                continue
            con.execute(
                """INSERT INTO acciones (meta_id, titulo, inteligencia, frecuencia, si_entonces, estado, origen, conversacion_id, creada)
                   VALUES (?,?,?,?,?, 'propuesta','hum',?,?)""",
                (metas_por_titulo.get((a.get("meta") or "").lower()), a["titulo"].strip(),
                 a.get("inteligencia") if a.get("inteligencia") in IDS else "",
                 a.get("frecuencia") if a.get("frecuencia") in FRECUENCIAS else "una_vez",
                 a.get("si_entonces", ""), cid, t))
            cuenta["acciones"] += 1
        for s in d.get("seguimientos", []):
            if s.get("texto", "").strip():
                fecha = (date.today() + timedelta(days=max(0, min(365, int(s.get("en_dias", 1)))))).isoformat()
                con.execute("INSERT INTO seguimientos (texto, fecha, conversacion_id, creado) VALUES (?,?,?,?)",
                            (s["texto"].strip(), fecha, cid, t))
                cuenta["seguimientos"] += 1
        p = d.get("perfil") or {}
        actual = con.execute("SELECT * FROM persona WHERE id = 1").fetchone()
        cambios = {}
        if p.get("nombre") and not actual["nombre"]:
            cambios["nombre"] = p["nombre"].strip()
        if p.get("como_llamarte") and not actual["como_llamarte"]:
            cambios["como_llamarte"] = p["como_llamarte"].strip()
        if p.get("contexto_nuevo", "").strip():
            cambios["contexto"] = (actual["contexto"] + " " + p["contexto_nuevo"].strip()).strip()[-2500:]
        if p.get("valores_nuevos", "").strip():
            cambios["valores"] = (actual["valores"] + " " + p["valores_nuevos"].strip()).strip()[-1200:]
        if cambios:
            sets = ", ".join(f"{k} = ?" for k in cambios)
            con.execute(f"UPDATE persona SET {sets}, actualizada = ? WHERE id = 1", (*cambios.values(), t))
        con.execute("UPDATE conversaciones SET digerida_hasta = ? WHERE id = ?", (ultimo_id, cid))
    return cuenta


def pendientes_de_digerir(minutos_quieta: int = 4) -> list[int]:
    """Conversaciones con mensajes nuevos sin digerir y sin actividad hace unos minutos."""
    with db() as con:
        rows = con.execute(
            """SELECT c.id FROM conversaciones c
               WHERE EXISTS (SELECT 1 FROM mensajes m WHERE m.conversacion_id = c.id AND m.id > c.digerida_hasta AND m.rol = 'user')
                 AND replace(c.actualizada, 'T', ' ') <= datetime('now', 'localtime', ?)""",
            (f"-{minutos_quieta} minutes",)).fetchall()
    return [r["id"] for r in rows]
