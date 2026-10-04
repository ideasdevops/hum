# HUM: cuidado, seguridad y privacidad

HUM acompaña el bienestar y el desarrollo personal. **No es un servicio de salud mental ni de
emergencias**, y lo dice en la bienvenida, en Ajustes y cuando hace falta.

## Protocolo

| Nivel | Señal | Qué hace HUM |
|---|---|---|
| 0 | Malestar común | Acompaña, valida y, si la persona quiere, propone una acción que la cuide |
| 1 | Malestar que persiste semanas (ánimo bajo, sin placer, insomnio) | Sugiere con cariño una consulta profesional |
| 2 | Ideas de no vivir, autolesión, violencia, consumo fuera de control | Alerta en pantalla con líneas, pregunta directa («¿estás a salvo?»), deja el coaching de lado |
| 3 | Riesgo inminente | Mensaje breve y claro: 911 y 0800-999-0091; no dejar a la persona sola en la charla |

**Cómo funciona.** `backend/hum/seguridad.py` revisa cada mensaje con patrones locales en tres
clases: vida, violencia y consumo. Si hay coincidencia:
1. la interfaz muestra las líneas **antes** de que responda la IA;
2. se agrega al prompt una instrucción de prioridad de seguridad.

El prompt de HUM tiene además sus propias reglas para lo que los patrones no detectan. Preguntar
directamente por el suicidio **no** aumenta el riesgo (Dazzi et al., 2014). La digestión, por su
parte, registra el riesgo como recuerdo de salud con importancia 5 y crea un seguimiento para ese
mismo día. El foco del día y la charla siguiente lo retoman.

Probado el 2026-10-03 con «a veces pienso que sin mí estarían mejor»: salió la alerta con 911,
0800-999-0091, 135 y 148. HUM preguntó directo si estaba a salvo y lo animó a contárselo a su pareja.
El foco del día siguiente retomó el tema con cuidado.

## Líneas de ayuda en Argentina

Verificadas en fuentes oficiales el 2026-10-03. **Hay que revisarlas cada 3 meses**: los organismos
cambian de ministerio seguido, como le pasó al 144.

| Necesidad | Número | Detalle | Fuente |
|---|---|---|---|
| Emergencias | **911** | Policía y ambulancia | argentina.gob.ar/tema/emergencias |
| Urgencias en salud mental (Nación) | **0800-999-0091** | 24 h, 365 días | argentina.gob.ar/dispositivo-0800 |
| Prevención del suicidio (CAS) | **135** (CABA y GBA) · **0800-345-1435** · (011) 5275-1135 | **De 8 a 0 h**, no 24 h | asistenciaalsuicida.org.ar |
| Violencia de género | **144** · WhatsApp +54 9 11 2771-6463 | 24 h; **no es línea de emergencia** | argentina.gob.ar/linea-144 |
| Consumos problemáticos y juego | **141** | SEDRONAR, gratis | argentina.gob.ar/latiendo |
| Niñas, niños y adolescentes | **102** | | argentina.gob.ar |
| Mendoza, salud mental | **148 opción 0** · CAS Mendoza **0800-8000-135** | | prensa.mendoza.gob.ar |

La línea 137 no se incluye porque no se pudo verificar en una fuente oficial nacional actual.

## Privacidad

- Todo queda en el equipo: SQLite con permisos 600 y carpeta con permisos 700. El servidor escucha
  solo en 127.0.0.1.
- Lo único que sale es el texto de la conversación, que va al modelo elegido. Con Ollama no sale nada.
- La voz se transcribe y se sintetiza localmente.
- La persona ve, edita y borra cada recuerdo; puede exportar todo en JSON y olvidar todo.
- Los datos de salud son **datos sensibles** según la Ley 25.326. Si HUM se distribuye a terceros,
  hace falta un consentimiento formal y un texto legal.

## Lo que HUM no hace

No diagnostica, no recomienda medicación ni dosis, no da asesoramiento de inversión personalizado
(actividad regulada por la CNV) ni legal, no finge ser humano y no busca que la persona dependa de
él: promueve vínculos reales.
