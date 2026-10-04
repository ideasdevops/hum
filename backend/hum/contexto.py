"""
Lo que HUM «tiene presente» en cada turno: el contexto vivo que se suma al prompt.

Se arma en cada mensaje con lo que importa ahora, no con todo lo que HUM sabe:
perfil, mapa de las 12 inteligencias, metas y acciones activas, seguimientos que
vencen, el check-in de hoy, el foco del día y los recuerdos relacionados con lo que
la persona acaba de decir (búsqueda de texto completo) más los más importantes.
"""
import re
from datetime import date, datetime, timedelta

from db import db, filas, hoy
from hum.inteligencias import INTELIGENCIAS, nombre

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def autopercepcion_actual() -> dict[str, int]:
    with db() as con:
        rows = con.execute(
            """SELECT a.inteligencia, a.valor FROM autoevaluaciones a
               JOIN (SELECT inteligencia, MAX(id) AS mid FROM autoevaluaciones GROUP BY inteligencia) u
               ON a.id = u.mid"""
        ).fetchall()
    return {r["inteligencia"]: r["valor"] for r in rows}


def _consulta_fts(texto: str) -> str:
    palabras = [p for p in re.findall(r"\w{4,}", texto.lower())][:12]
    return " OR ".join(f'"{p}"' for p in palabras)


def recuerdos_relevantes(texto: str, limite: int = 12) -> list[dict]:
    with db() as con:
        encontrados: dict[int, dict] = {}
        q = _consulta_fts(texto)
        if q:
            for r in filas(con.execute(
                """SELECT r.* FROM recuerdos_fts f JOIN recuerdos r ON r.id = f.rowid
                   WHERE recuerdos_fts MATCH ? AND r.activo = 1 ORDER BY rank LIMIT 8""", (q,))):
                encontrados[r["id"]] = r
        for r in filas(con.execute(
            "SELECT * FROM recuerdos WHERE activo = 1 ORDER BY importancia DESC, id DESC LIMIT 10")):
            encontrados.setdefault(r["id"], r)
        for r in filas(con.execute("SELECT * FROM recuerdos WHERE activo = 1 ORDER BY id DESC LIMIT 5")):
            encontrados.setdefault(r["id"], r)
    return list(encontrados.values())[:limite]


def armar(ultimo_mensaje: str, modo: str = "texto") -> str:
    ahora = datetime.now()
    with db() as con:
        persona = dict(con.execute("SELECT * FROM persona WHERE id = 1").fetchone())
        lecturas = {r["id"]: r["lectura"] for r in con.execute("SELECT id, lectura FROM inteligencias")}
        metas = filas(con.execute(
            "SELECT * FROM metas WHERE estado = 'activa' ORDER BY actualizada DESC LIMIT 8"))
        acciones = filas(con.execute(
            """SELECT a.*, (SELECT COUNT(*) FROM acciones_hechas h WHERE h.accion_id = a.id
                            AND h.fecha >= ?) AS hechas_7d,
                      (SELECT 1 FROM acciones_hechas h WHERE h.accion_id = a.id AND h.fecha = ?) AS hecha_hoy
               FROM acciones a WHERE a.estado = 'activa' ORDER BY a.id DESC LIMIT 15""",
            ((date.today() - timedelta(days=7)).isoformat(), hoy())))
        propuestas = con.execute(
            "SELECT (SELECT COUNT(*) FROM metas WHERE estado='propuesta') + "
            "(SELECT COUNT(*) FROM acciones WHERE estado='propuesta')").fetchone()[0]
        seguimientos = filas(con.execute(
            "SELECT * FROM seguimientos WHERE estado = 'pendiente' AND fecha <= ? ORDER BY fecha LIMIT 5", (hoy(),)))
        registro = con.execute("SELECT * FROM registros WHERE fecha = ?", (hoy(),)).fetchone()
        foco = con.execute("SELECT * FROM foco_diario WHERE fecha = ?", (hoy(),)).fetchone()
        ultimas_conv = filas(con.execute(
            """SELECT titulo, actualizada FROM conversaciones WHERE titulo != 'Conversación nueva'
               ORDER BY actualizada DESC LIMIT 5"""))
    auto = autopercepcion_actual()

    p = []
    p.append(f"Fecha y hora: {DIAS[ahora.weekday()]} {ahora:%d/%m/%Y %H:%M}. Modo: {'voz (respuestas habladas)' if modo == 'voz' else 'texto'}.")

    nombre_persona = persona["como_llamarte"] or persona["nombre"]
    p.append("## La persona")
    if nombre_persona:
        p.append(f"Se llama {persona['nombre'] or nombre_persona}; prefiere que le digas «{nombre_persona}».")
    else:
        p.append("Todavía no sabés su nombre: preguntalo con naturalidad cuando venga al caso.")
    if persona["contexto"]:
        p.append(f"Contexto de vida: {persona['contexto']}")
    if persona["valores"]:
        p.append(f"Lo que le importa: {persona['valores']}")

    p.append("## Su mapa de las 12 inteligencias")
    if auto or any(lecturas.values()):
        for i in INTELIGENCIAS:
            linea = f"- {i['nombre']} ({i['dimension']})"
            if i["id"] in auto:
                linea += f": se percibe en {auto[i['id']]}/10"
            if lecturas.get(i["id"]):
                linea += f". Tu lectura: {lecturas[i['id']]}"
            p.append(linea)
    else:
        p.append("Todavía no hizo su autoevaluación ni tenés lecturas propias.")

    if metas:
        p.append("## Metas activas")
        for m in metas:
            p.append(f"- [{m['id']}] {m['titulo']} ({m['area'] or 'sin área'}, progreso {m['progreso']}%)"
                     + (f". Por qué: {m['porque']}" if m["porque"] else "")
                     + (f". Plan si-entonces: {m['plan']}" if m["plan"] else ""))
    if acciones:
        p.append("## Acciones y hábitos activos")
        for a in acciones:
            estado = "hecha hoy" if a["hecha_hoy"] else f"{a['hechas_7d']} veces en 7 días"
            p.append(f"- {a['titulo']} [{nombre(a['inteligencia'])}, {a['frecuencia']}] — {estado}")
    if propuestas:
        p.append(f"Hay {propuestas} propuesta(s) tuyas esperando que la persona las acepte en «Planes».")

    if seguimientos:
        p.append("## Para retomar hoy (seguimientos)")
        for s in seguimientos:
            p.append(f"- {s['texto']}")
        p.append("Retomá uno con naturalidad si la conversación lo permite; no los dispares todos juntos.")

    if registro:
        p.append(f"## Check-in de hoy: ánimo {registro['animo']}/10, energía {registro['energia']}/10, "
                 f"sueño {registro['sueno']} h" + (f". Nota: {registro['nota']}" if registro["nota"] else ""))
    if foco:
        p.append(f"## Foco del día que le propusiste: {nombre(foco['inteligencia'])} — {foco['texto']}")

    rec = recuerdos_relevantes(ultimo_mensaje)
    if rec:
        p.append("## Lo que sabés de su vida (recuerdos relevantes)")
        for r in rec:
            p.append(f"- ({r['tipo']}, {r['fecha'][:10]}) {r['contenido']}")
    if ultimas_conv:
        p.append("## Últimas conversaciones: " + "; ".join(c["titulo"] for c in ultimas_conv))

    return "<contexto_vivo>\n" + "\n".join(p) + "\n</contexto_vivo>"
