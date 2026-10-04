"""
Cuidado de la persona. HUM acompaña, pero no es terapia ni atención médica.

Antes de responder, se revisa el mensaje con patrones simples (rápidos, locales, sin
depender del modelo). Si aparece una señal de riesgo:
  · la interfaz muestra de inmediato las líneas de ayuda (no espera a la IA),
  · al prompt se le suma una instrucción de prioridad: primero la seguridad.
El modelo además tiene sus propias reglas en el prompt para lo que los patrones no ven.

Las líneas están verificadas en fuentes oficiales: ver docs/SEGURIDAD.md.
"""
import re
import unicodedata

# Verificadas en fuentes oficiales el 2026-10-03 (docs/SEGURIDAD.md). Revisar cada 3 meses:
# los organismos cambian de ministerio seguido (le pasó al 144).
LINEAS = {
    "vida": [
        {"nombre": "Emergencias", "numero": "911", "detalle": "Si hay peligro inmediato."},
        {"nombre": "Urgencias en salud mental (Nación)", "numero": "0800-999-0091",
         "detalle": "Gratuita, las 24 h, todo el país."},
        {"nombre": "Centro de Asistencia al Suicida", "numero": "135",
         "detalle": "Gratis desde CABA y GBA. Todo el país: 0800-345-1435 o (011) 5275-1135. De 8 a 0 h."},
        {"nombre": "Mendoza — salud mental", "numero": "148",
         "detalle": "Opción 0. También CAS Mendoza: 0800-8000-135."},
    ],
    "violencia": [
        {"nombre": "Emergencias", "numero": "911", "detalle": "Si hay peligro inmediato: el 144 no es línea de emergencia."},
        {"nombre": "Línea 144", "numero": "144",
         "detalle": "Violencia de género. Gratis, las 24 h. WhatsApp +54 9 11 2771-6463."},
        {"nombre": "Línea 102", "numero": "102", "detalle": "Niñas, niños y adolescentes."},
    ],
    "consumo": [
        {"nombre": "Línea 141 (SEDRONAR)", "numero": "141", "detalle": "Consumos problemáticos y juego. Gratis, todo el país."},
        {"nombre": "Urgencias en salud mental (Nación)", "numero": "0800-999-0091", "detalle": "Las 24 h."},
        {"nombre": "Emergencias", "numero": "911", "detalle": "Si hay peligro inmediato."},
    ],
}

_RIESGO_VIDA = [
    r"\bsuicid", r"\bmatarme\b", r"\bme quiero matar", r"\bquitarme la vida", r"\bterminar con (mi vida|todo)",
    r"\bno quiero (seguir )?vivir", r"\bno vale la pena vivir", r"\bquiero morir", r"\bme quiero morir",
    r"\bojala no despertar", r"\bhacerme dano\b", r"\blastimarme\b", r"\bcortarme\b", r"\bautolesi",
    r"\bdesaparecer para siempre", r"\bsin mi estarian mejor", r"\bmejor muert", r"\btomarme todas las pastillas",
]
_CONSUMO = [
    r"\bno puedo dejar de (tomar|beber|consumir|jugar|apostar)", r"\bestoy (enganchad|adicto|adicta)",
    r"\bme (gaste|patine) todo (en el casino|apostando|jugando)", r"\bsobredosis",
]
_VIOLENCIA = [
    r"\bme (pega|golpea|amenaza|maltrata)\b", r"\bme (pego|golpeo|amenazo)\b", r"\bviolencia (de genero|domestica)",
    r"\bme violo\b", r"\babuso sexual", r"\bme abusa", r"\btengo miedo de (el|ella|mi pareja)",
    r"\bme quiere matar", r"\bme va a matar",
]


def _normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def revisar(texto: str) -> dict | None:
    """Devuelve {"tipo": "vida"|"violencia"|"consumo", "lineas": [...]} o None."""
    t = _normalizar(texto)
    if any(re.search(p, t) for p in _RIESGO_VIDA):
        return {"tipo": "vida", "lineas": LINEAS["vida"]}
    if any(re.search(p, t) for p in _VIOLENCIA):
        return {"tipo": "violencia", "lineas": LINEAS["violencia"]}
    if any(re.search(p, t) for p in _CONSUMO):
        return {"tipo": "consumo", "lineas": LINEAS["consumo"]}
    return None


def instruccion(alerta: dict) -> str:
    lineas = "; ".join(f"{l['nombre']}: {l['numero']}" for l in alerta["lineas"])
    if alerta["tipo"] == "vida":
        foco = ("La persona puede estar en riesgo. Dejá de lado planes, metas e inteligencias. "
                "Respondé con calidez y calma, validá lo que siente sin juzgar, preguntá directamente "
                "si está a salvo ahora y si pensó en hacerse daño. Animala a hablar ya con alguien de confianza "
                "y con una línea de ayuda.")
    elif alerta["tipo"] == "consumo":
        foco = ("La persona habla de un consumo o juego que se le fue de las manos. Sin juzgar ni sermonear: "
                "reconocé el coraje de decirlo, explorá con curiosidad qué le pasa y ofrecé el 141. "
                "Si hay riesgo físico inmediato (intoxicación, sobredosis), 911 primero.")
    else:
        foco = ("La persona puede estar sufriendo violencia. Creele, no la culpes, priorizá su seguridad física "
                "y la de sus hijos si los hay, y ofrecé las líneas. No le sugieras confrontar a quien la agrede.")
    return (f"<prioridad_seguridad>\n{foco}\nLíneas de Argentina (la interfaz ya se las está mostrando): {lineas}.\n"
            "Nombrá al menos una en tu respuesta. Sé breve y humano; nada de listas largas.\n</prioridad_seguridad>")
