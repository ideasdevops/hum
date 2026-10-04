# HUM — la inteligencia humanizada de JFlowOS

HUM es la IA de **UEI (Universo Estratégico Inteligente)**, el ecosistema de IdeasDevOps y
Disruptia AI. Acompaña a quien usa JFlowOS a mejorar un poco cada día en su trabajo, su vida, sus
decisiones y lo que aprende. Se basa en **JFlow**, el sistema humano de Joaquín de Rosas: 12
inteligencias en tres dimensiones.

| Cuerpo | Mente | Espíritu |
|---|---|---|
| Vital · Sensorial · Motriz · Adaptativa | Lógica · Lingüística · Financiera · Musical | Conectiva · Introspectiva · Expresiva · Trascendental |

**Lo que lo hace distinto:** la gente ya le habla a la IA de su trabajo, sus dudas y sus emociones,
pero esas conversaciones se pierden. Con HUM no: cada charla se **digiere** y queda como recuerdos,
observaciones sobre las 12 inteligencias, propuestas de metas (WOOP) y acciones pequeñas
(si-entonces), y seguimientos que HUM retoma después. **Nada entra en los planes sin que la persona
lo acepte.**

Se puede chatear por texto, dictar, o **hablar en voz alta** (modo manos libres). El oído (Whisper)
y la voz (Piper, voz es_AR) corren en el equipo.

## Pantallas

| Sección | Qué hace |
|---|---|
| **Hoy** | Saludo, check-in (ánimo, energía, sueño), foco del día (una inteligencia y una práctica), acciones de hoy, lo que HUM quiere retomar, racha |
| **Conversar** | Chat con respuesta en vivo, dictado, modo voz con el orbe, «Guardar aprendizajes», historial |
| **Mi mapa** | Rueda de las 12 (autopercepción actual y la anterior), lectura viva de HUM por inteligencia, observaciones, prácticas con su nivel de evidencia |
| **Planes** | Propuestas de HUM para aceptar o descartar, metas con WOOP y progreso, acciones y hábitos |
| **Lo que HUM sabe** | Todos los recuerdos, para buscar, editar u olvidar; exportar todo; olvidar todo |
| **Ajustes** | Con qué piensa (API de Anthropic, Claude Code u Ollama), voz, velocidad, oído, perfil |

## Instalar y usar

```bash
bin/hum instalar     # venv + dependencias + compila la interfaz (Python 3.10+, Node 20, ffmpeg)
bin/hum              # abre HUM en una ventana propia (levanta el servidor si hace falta)
bin/hum levantar     # solo el servidor, en segundo plano (para el arranque de sesión)
bin/hum estado | detener | servidor
```

Escucha solo en `127.0.0.1:8412`. Para pensar necesita **uno** de estos tres:

1. **Clave de Anthropic** (Ajustes o `~/.config/hum/hum.env`). Usa `claude-opus-5-5` con caché de prompt
   y *fallback* del servidor ante rechazos. Tiene la mejor latencia para hablar por voz.
2. **Claude Code** logueado, el que instala Ideas Box. Corre aislado: sin herramientas, sin MCP, sin
   ajustes ni CLAUDE.md del usuario.
3. **Ollama** con algún modelo. Totalmente local.

## Dónde se guarda cada cosa

```text
~/.local/share/hum/hum.db        perfil, mapa, conversaciones, recuerdos, metas… (SQLite, permisos 600)
~/.local/share/hum/modelos/      Whisper (~480 MB) y voz Piper (~110 MB), se bajan la primera vez
~/.config/hum/hum.env            clave de Anthropic y ajustes de arranque (permisos 600)
~/.local/state/hum/              PID, log y perfil de la ventana
```

`HUM_DATA_DIR` y `HUM_CONFIG_DIR` cambian esas rutas, por ejemplo para que HUM viaje dentro de un
IdeasPackage.

## Estructura

```text
backend/
  main.py                 FastAPI: API + interfaz compilada + digestor en segundo plano
  config.py db.py         rutas, hum.env, esquema SQLite
  conocimiento/inteligencias.json   las 12: definición, señales, preguntas, prácticas con evidencia (editable sin código)
  hum/prompts.py          quién es HUM (parte estable del prompt, cacheada)
  hum/contexto.py         lo que HUM tiene presente en cada turno (perfil, mapa, metas, recuerdos relevantes)
  hum/digestion.py        conversación → recuerdos, observaciones, lecturas, propuestas WOOP, seguimientos
  hum/seguridad.py        detección local de riesgo + líneas de ayuda verificadas de Argentina
  hum/proveedores.py      Anthropic API · Claude Code · Ollama (streaming + JSON estructurado)
  hum/voz.py              faster-whisper (oído) y Piper (voz), locales
  routers/                conversaciones, vida (persona, mapa, planes, hoy, recuerdos), sistema
frontend/                 React 19 + Vite + Tailwind 4 (mismo stack que el panel de Ideas Box)
bin/hum                   lanzador
packaging/                .desktop e ícono para JFlowOS
docs/                     diseño, investigación de las 12 inteligencias, seguridad
```

## Documentos

- [`docs/DISENO_HUM.md`](docs/DISENO_HUM.md): concepto, cómo funciona el motor, decisiones y plan de integración a JFlowOS 12.1 «Chacayes».
- [`docs/INVESTIGACION_12_INTELIGENCIAS.md`](docs/INVESTIGACION_12_INTELIGENCIAS.md): fundamentos, evidencia y fuentes de cada inteligencia; marcos de coaching; escalas de bienestar y sus licencias.
- [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md): protocolo de cuidado, líneas de ayuda verificadas, privacidad.

---
UEI · JFlowOS · IdeasDevOps & Disruptia AI. HUM es una IA de acompañamiento y no reemplaza a
profesionales de la salud, legales ni financieros.
