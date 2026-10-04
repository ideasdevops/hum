# HUM: diseño

*Versión 0.1 · 2026-10-03 · para revisar con Joaquín de Rosas (JFlow / DisruptIA)*

## 1. Qué es y para qué

HUM es la «IA humanizada» de UEI. Vive en JFlowOS y acompaña a una sola persona: la que usa el equipo.

El problema que resuelve: hoy la gente usa la IA para trabajar, preguntar, conversar y hasta hablar de
emociones, pero **nada de eso impacta en planes de mejora, resolución de problemas ni motivación
sostenida**. Cada chat empieza de cero y termina en el aire.

La apuesta de HUM:
1. **Mira la vida completa** con el mapa de JFlow: 12 inteligencias en Cuerpo, Mente y Espíritu.
2. **Recuerda**, para que la persona no tenga que explicarse de nuevo.
3. **Convierte cada conversación en mejora**: metas, pasos chicos, seguimientos.
4. **Respeta la autonomía**: propone, la persona decide. Nada entra en sus planes sin su OK.
5. **Cuida**: la seguridad va primero y nunca se hace pasar por terapia.

## 2. El modelo de las 12 inteligencias

Las definiciones operativas de `backend/conocimiento/inteligencias.json` salen de la investigación
(`INVESTIGACION_12_INTELIGENCIAS.md`). El modelo de 12 inteligencias es de **JFlow** y no tiene
material público, así que **las definiciones esperan la validación de Joaquín**: se cambian en ese
JSON sin tocar código.

Honestidad científica, que el producto sostiene en el prompt y en la interfaz:
- Como «inteligencias» separadas y medibles, la evidencia es débil (pasa lo mismo con Gardner). Por
  eso HUM las presenta como **un mapa para mirar la vida completa** y los números como
  **autopercepción**, nunca como medición.
- Las **prácticas** sí tienen respaldo, y cada una lleva su nivel: A sólido, B moderado, C débil o
  conceptual. HUM prefiere las de mayor respaldo.
- Hipótesis que hay que confirmar con Joaquín: si el «Flow» de JFlow remite al *flow* de
  Csikszentmihalyi, que es el estado donde cuerpo, mente y propósito se alinean. Si es así, el flow
  puede ser el «estado objetivo» transversal de HUM.

## 3. Cómo funciona el motor

```
            ┌──────────── contexto vivo (en cada turno) ────────────┐
 persona ─▶ │ perfil · mapa 12 · metas/acciones · seguimientos ·     │ ─▶ modelo ─▶ respuesta en vivo
 (texto     │ check-in · foco · recuerdos relevantes (FTS)           │      ▲         (texto o voz)
  o voz)    └────────────────────────────────────────────────────────┘      │
     │        seguridad.py: patrones locales → alerta + líneas + prioridad ──┘
     ▼
 mensajes ─▶ DIGESTIÓN (cada 6 mensajes, a los 4 min de quietud o a mano)
               → recuerdos · observaciones (+/−) · lectura por inteligencia
               → metas WOOP y acciones si-entonces  ══▶  «propuesta»  ══▶ la persona acepta
               → seguimientos con fecha            ══▶  HUM los retoma en Hoy y en la charla
```

**Estilo de conversación** (en `prompts.py`). Mezcla la entrevista motivacional (preguntas abiertas,
reflejos, resúmenes) y la teoría de la autodeterminación (autonomía, competencia, vínculo). El camino
de mejora, sin nombrar los métodos, va así:

claridad → mejor resultado → obstáculo **interno** → plan si-entonces → paso mínimo anclado a una
rutina → confianza del 1 al 10 (si es menos de 7, se achica el paso).

Una inteligencia foco y de uno a tres hábitos a la vez.

**Por qué propuestas y no acciones automáticas.** El loop humano está aguas arriba, en la decisión,
no en la ejecución. Es la misma idea que la hipótesis de DisruptIA: se aprueba una vez y corre
muchas. HUM propone; la persona elige y lo hace propio.

**Memoria.** Los recuerdos son frases autocontenidas con tipo, importancia y las inteligencias que
tocan. Se recuperan por búsqueda de texto completo sobre el último mensaje, más los más importantes
y los más recientes. No hay embeddings: es suficiente para una sola persona y no agrega
dependencias. Todo es visible, editable y borrable en «Lo que HUM sabe».

**Mapa vivo.** Hay dos fuentes y no se mezclan:
- la **autopercepción**, con historial: la rueda muestra la evaluación actual y la anterior, punteada;
- la **lectura de HUM**, en texto, con las observaciones que la sostienen y la actividad de 30 días
  (acciones hechas, avances, dificultades).

No se inventa un puntaje «objetivo».

## 4. Decisiones técnicas

| Decisión | Por qué |
|---|---|
| App local (FastAPI + React) en `127.0.0.1:8412` | Mismo stack que el panel de Ideas Box; los datos personales no salen del equipo |
| Tres proveedores (Anthropic API, Claude Code, Ollama) | Funciona en cualquier JFlowOS: con clave, con la cuenta de Ideas Box, o 100 % local. Medido: Claude Code ~6 s por respuesta; Ollama qwen3.5 en la GTX 1650 ~108 s la primera (con carga del modelo) y de menor calidad: sirve como respaldo privado, no para voz |
| Claude Code aislado (`--tools "" --strict-mcp-config --setting-sources ""`) | HUM conversa, no ejecuta nada; no hereda CLAUDE.md, ajustes ni MCP del usuario (verificado) |
| Prompt en dos bloques: estable (cacheado) + vivo | Menos costo y latencia por turno con la API |
| `fallbacks: "default"` en la API | Una IA que habla de emociones toca temas sensibles; si un clasificador declina, el servidor reintenta |
| Voz local: faster-whisper `small` int8 + Piper es_AR «daniela» | La voz de la persona no se manda a terceros. Medido en este equipo: oír 1,3-1,5 s; hablar 0,4-0,5 s por frase |
| Respuesta hablada frase por frase | HUM empieza a hablar antes de terminar de pensar |
| Detección de riesgo con patrones locales, además del modelo | La ayuda aparece al instante y no depende del proveedor |
| Conocimiento en JSON | Joaquín y el equipo ajustan las 12 sin programar |

## 5. Integración a JFlowOS 12.1 «Chacayes» (próximo paso)

Esta parte todavía no está hecha.

1. **Paquete**: incluir `hum/` en `/usr/share/jflowos/hum` y `bin/hum` en `/usr/bin/hum` vía el
   overlay de jflow-os. El venv y la compilación de la interfaz se hacen en el chroot de build, en
   `chroot/`, igual que Ideas Box.
2. **Modelos de voz**: decidir si van en la ISO (unos 590 MB más) o se bajan en el primer uso, como
   hoy. Para la ISO conviene `base` (unos 145 MB) y dejar `small` como mejora opcional.
3. **Escritorio**: `hum.desktop` en el dock Plank y en el menú. Atajo global sugerido: Super+H, que
   abre HUM en modo voz. Ícono del orbe en el tema de íconos.
4. **Arranque**: `hum levantar` en el autostart de la sesión, así HUM ya está cuando se lo llama.
5. **Avisos nativos**: un `jflowos-hum-notif`, como `jflowos-plataforma-notif`, que a la mañana
   avise el foco del día y los seguimientos que vencen (`notify-send`).
6. **Bienvenida de JFlowOS**: sumar el paso «Conocé a HUM», que abre el onboarding.
7. **IdeasPackage**: incluir `~/.local/share/hum` en el paquete portable. HUM ya acepta
   `HUM_DATA_DIR`.
8. **Ideas Box**: el «Pensar con Claude Code» de HUM usa la misma cuenta; documentarlo en el
   asistente.

## 6. Pendientes y preguntas abiertas

- **Validar con Joaquín**: definiciones de las 12, grafía de la marca (la web muestra «DisruptIA /
  JOTAFLOW»), el rol del flow, y si quiere sumar sus propias prácticas o preguntas.
- **Escalas de bienestar**: WHO-5 mensual y SWLS trimestral están planeadas, no hechas. La licencia
  del WHO-5 es CC BY-NC-SA: hay que resolver la cláusula no comercial si HUM se vende.
  PERMA-Profiler y WEMWBS requieren licencia comercial.
- **Revisión semanal guiada**: ya existen los datos (cumplimiento, observaciones); falta la pantalla.
- **Supervisión clínica**: si HUM se distribuye a terceros, conviene que un profesional de salud
  mental revise el protocolo de crisis.
- **Datos sensibles (Ley 25.326)**: el consentimiento expreso está en la bienvenida; falta un texto
  legal formal si se distribuye.
- **Menores**: HUM está pensado para mayores de 18 y no lo verifica.
- **Herramientas en la charla**: hoy HUM anota a través de la digestión. Con la API se podría sumar
  uso de herramientas, por ejemplo para marcar un hábito como hecho desde la charla.
