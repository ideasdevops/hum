"""
Las 12 inteligencias humanas de JFlow, en tres dimensiones:

  Cuerpo    vital · sensorial · motriz · adaptativa
  Mente     lógica · lingüística · financiera · musical
  Espíritu  conectiva · introspectiva · expresiva · trascendental

El conocimiento de cada una (definición, señales, preguntas, prácticas y qué tan
sólida es la evidencia) vive en conocimiento/inteligencias.json, para que Joaquín y
el equipo lo puedan ajustar sin tocar código.
"""
import json

from config import CONOCIMIENTO_DIR

_DATOS = json.loads((CONOCIMIENTO_DIR / "inteligencias.json").read_text(encoding="utf-8"))

DIMENSIONES: list[dict] = _DATOS["dimensiones"]
INTELIGENCIAS: list[dict] = _DATOS["inteligencias"]
IDS = [i["id"] for i in INTELIGENCIAS]
_POR_ID = {i["id"]: i for i in INTELIGENCIAS}


def nombre(id_: str) -> str:
    i = _POR_ID.get(id_)
    return i["nombre"] if i else (id_ or "general")


def obtener(id_: str) -> dict | None:
    return _POR_ID.get(id_)


def validas(ids) -> list[str]:
    """Filtra ids que vengan del modelo: solo los 12 conocidos, sin repetir."""
    vistos = []
    for x in ids or []:
        x = str(x).strip().lower()
        if x in _POR_ID and x not in vistos:
            vistos.append(x)
    return vistos


def marco_para_prompt() -> str:
    """Versión compacta del marco para el prompt de sistema (parte estable, cacheada)."""
    lineas = []
    for d in DIMENSIONES:
        lineas.append(f"### {d['nombre']} — {d['descripcion']}")
        for i in (x for x in INTELIGENCIAS if x["dimension_id"] == d["id"]):
            lineas.append(f"**{i['nombre']}** (`{i['id']}`): {i['definicion']}")
            lineas.append(f"  Señales: {'; '.join(i['senales'])}.")
            lineas.append(f"  Preguntas que abren: {' / '.join(i['preguntas'][:3])}")
            lineas.append(f"  Prácticas: {'; '.join(p['nombre'] + ' (' + p['como'] + ')' for p in i['practicas'])}.")
            if i.get("cuidado"):
                lineas.append(f"  Cuidado: {i['cuidado']}")
    return "\n".join(lineas)
