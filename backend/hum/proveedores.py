"""
Con qué modelo piensa HUM. Tres caminos, para que funcione en cualquier JFlowOS:

  anthropic     API de Claude con clave propia (ANTHROPIC_API_KEY en hum.env). La mejor
                latencia para hablar por voz, con caché de prompt.
  claude-code   Claude Code ya instalado y logueado (lo trae Ideas Box): no pide ninguna
                clave extra. Corre sin herramientas, sin MCP y sin ajustes del usuario.
  ollama        Un modelo local. Nada sale del equipo; la calidad depende del modelo.

«auto» elige el primero disponible en ese orden.

Todos exponen lo mismo:
  conversar(estable, vivo, mensajes, rapido) -> iterador de fragmentos de texto
  estructurado(sistema, pedido, esquema)     -> dict que cumple el esquema JSON
"""
import json
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterator

from config import DATA_DIR, leer_env
from db import ajuste

MODELO_ANTHROPIC = "claude-opus-5-5"


class ErrorProveedor(RuntimeError):
    pass


# --- Anthropic (API) --------------------------------------------------------------

def _cliente_anthropic():
    import anthropic  # noqa: PLC0415

    clave = leer_env().get("ANTHROPIC_API_KEY")
    if not clave:
        raise ErrorProveedor("Falta ANTHROPIC_API_KEY en ~/.config/hum/hum.env")
    return anthropic.Anthropic(api_key=clave)


def _anthropic_conversar(estable: str, vivo: str, mensajes: list[dict], rapido: bool, modelo: str) -> Iterator[str]:
    import anthropic  # noqa: PLC0415

    cliente = _cliente_anthropic()
    try:
        with cliente.beta.messages.stream(
            model=modelo or MODELO_ANTHROPIC,
            max_tokens=8000,
            # La parte estable (identidad, marco de las 12 inteligencias, seguridad) va
            # primero y se cachea; lo que cambia en cada turno (perfil, recuerdos, metas) después.
            system=[
                {"type": "text", "text": estable, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": vivo},
            ],
            messages=mensajes,
            output_config={"effort": "low" if rapido else "medium"},
            # Si un clasificador de seguridad declina (temas sensibles aparecen seguido en
            # una IA que acompaña emociones), el servidor reintenta en el modelo que corresponda.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            for texto in stream.text_stream:
                yield texto
            final = stream.get_final_message()
            if final.stop_reason == "refusal":
                yield ("\n\nNo puedo seguir por este camino, pero sigo acá con vos. "
                       "Si estás pasando un momento difícil, mirá las líneas de ayuda en la pantalla.")
            elif final.stop_reason == "max_tokens":
                yield "…"
    except anthropic.AuthenticationError:
        raise ErrorProveedor("La clave de Anthropic no es válida.")
    except anthropic.RateLimitError:
        raise ErrorProveedor("Anthropic pidió esperar un momento (límite de uso). Probá de nuevo en un rato.")
    except anthropic.APIStatusError as e:
        raise ErrorProveedor(f"Anthropic devolvió {e.status_code}: {str(e.message)[:200]}")
    except anthropic.APIConnectionError:
        raise ErrorProveedor("No hay conexión con Anthropic. ¿Hay internet?")


def _anthropic_estructurado(sistema: str, pedido: str, esquema: dict, modelo: str) -> dict:
    import anthropic  # noqa: PLC0415

    cliente = _cliente_anthropic()
    try:
        with cliente.beta.messages.stream(
            model=modelo or MODELO_ANTHROPIC,
            max_tokens=16000,
            system=sistema,
            messages=[{"role": "user", "content": pedido}],
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": esquema}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            final = stream.get_final_message()
    except anthropic.APIStatusError as e:
        raise ErrorProveedor(f"Anthropic devolvió {e.status_code}: {str(e.message)[:200]}")
    except anthropic.APIConnectionError:
        raise ErrorProveedor("No hay conexión con Anthropic.")
    if final.stop_reason == "refusal":
        raise ErrorProveedor("El modelo declinó procesar esta conversación.")
    texto = next((b.text for b in final.content if b.type == "text"), "")
    return json.loads(texto)


# --- Claude Code (CLI con la cuenta del equipo) -----------------------------------

def claude_bin() -> str | None:
    home = Path.home()
    for c in (shutil.which("claude"), home / ".local" / "bin" / "claude", home / ".claude" / "local" / "claude"):
        if c and Path(c).exists():
            return str(c)
    return None


def _claude_cmd(sistema_archivo: str, modelo: str, rapido: bool) -> list[str]:
    cmd = [
        claude_bin() or "claude", "-p",
        "--system-prompt-file", sistema_archivo,
        # HUM no ejecuta nada: sin herramientas, sin MCP, sin ajustes ni hooks del usuario.
        "--tools", "", "--strict-mcp-config", "--setting-sources", "",
        "--no-session-persistence",
        "--effort", "low" if rapido else "medium",
    ]
    if modelo:
        cmd += ["--model", modelo]
    return cmd


def _transcripcion(mensajes: list[dict]) -> str:
    partes = []
    for m in mensajes[:-1]:
        quien = "Persona" if m["role"] == "user" else "HUM"
        partes.append(f"{quien}: {m['content']}")
    previo = "\n\n".join(partes)
    ultimo = mensajes[-1]["content"]
    if previo:
        return (f"<conversacion_hasta_ahora>\n{previo}\n</conversacion_hasta_ahora>\n\n"
                f"Nuevo mensaje de la persona (respondelo como HUM, sin prefijos):\n{ultimo}")
    return ultimo


def _cwd_aislado() -> str:
    d = DATA_DIR / "claude-cwd"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def _claude_conversar(estable: str, vivo: str, mensajes: list[dict], rapido: bool, modelo: str) -> Iterator[str]:
    if not claude_bin():
        raise ErrorProveedor("No encuentro Claude Code en este equipo.")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(estable + "\n\n" + vivo)
        archivo = f.name
    try:
        cmd = _claude_cmd(archivo, modelo, rapido) + [
            "--output-format", "stream-json", "--include-partial-messages", "--verbose",
        ]
        proc = subprocess.Popen(
            cmd, cwd=_cwd_aislado(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
        )
        proc.stdin.write(_transcripcion(mensajes))
        proc.stdin.close()
        dio_texto = False
        for linea in proc.stdout:
            try:
                ev = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "stream_event":
                e = ev.get("event", {})
                if e.get("type") == "content_block_delta" and e.get("delta", {}).get("type") == "text_delta":
                    dio_texto = True
                    yield e["delta"]["text"]
            elif ev.get("type") == "result" and ev.get("is_error"):
                raise ErrorProveedor(f"Claude Code no pudo responder: {str(ev.get('result'))[:200]}")
        proc.wait(timeout=30)
        if not dio_texto and proc.returncode:
            raise ErrorProveedor(f"Claude Code terminó con error: {proc.stderr.read()[:300]}")
    finally:
        Path(archivo).unlink(missing_ok=True)


def _claude_estructurado(sistema: str, pedido: str, esquema: dict, modelo: str) -> dict:
    if not claude_bin():
        raise ErrorProveedor("No encuentro Claude Code en este equipo.")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(sistema)
        archivo = f.name
    try:
        cmd = _claude_cmd(archivo, modelo, False) + ["--output-format", "json", "--json-schema", json.dumps(esquema)]
        r = subprocess.run(cmd, cwd=_cwd_aislado(), input=pedido, capture_output=True, text=True, timeout=300)
    finally:
        Path(archivo).unlink(missing_ok=True)
    try:
        datos = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise ErrorProveedor(f"Respuesta inesperada de Claude Code: {(r.stdout or r.stderr)[:300]}")
    if datos.get("is_error"):
        raise ErrorProveedor(f"Claude Code no pudo responder: {str(datos.get('result'))[:300]}")
    if isinstance(datos.get("structured_output"), dict):
        return datos["structured_output"]
    return _json_de_texto(datos.get("result") or "")


# --- Ollama (local) ---------------------------------------------------------------

def _ollama_url() -> str:
    return leer_env().get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


def ollama_modelos() -> list[str]:
    try:
        with urllib.request.urlopen(_ollama_url() + "/api/tags", timeout=2) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", []) if not m["name"].endswith(":cloud")]
    except (urllib.error.URLError, OSError, ValueError):
        return []


def _ollama_post(cuerpo: dict, timeout: int):
    req = urllib.request.Request(
        _ollama_url() + "/api/chat", data=json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as e:
        raise ErrorProveedor(f"No pude hablar con Ollama: {e}")


def _ollama_modelo(modelo: str) -> str:
    if modelo:
        return modelo
    disponibles = ollama_modelos()
    if not disponibles:
        raise ErrorProveedor("Ollama no tiene modelos descargados (probá: ollama pull qwen3).")
    return disponibles[0]


def _ollama_conversar(estable: str, vivo: str, mensajes: list[dict], rapido: bool, modelo: str) -> Iterator[str]:
    cuerpo = {
        "model": _ollama_modelo(modelo), "stream": True, "think": False,
        "messages": [{"role": "system", "content": estable + "\n\n" + vivo}, *mensajes],
    }
    with _ollama_post(cuerpo, timeout=300) as r:
        for linea in r:
            try:
                ev = json.loads(linea)
            except ValueError:
                continue
            if ev.get("error"):
                raise ErrorProveedor(f"Ollama: {ev['error']}")
            trozo = ev.get("message", {}).get("content")
            if trozo:
                yield trozo


def _ollama_estructurado(sistema: str, pedido: str, esquema: dict, modelo: str) -> dict:
    cuerpo = {
        "model": _ollama_modelo(modelo), "stream": False, "format": esquema, "think": False,
        "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": pedido}],
    }
    with _ollama_post(cuerpo, timeout=600) as r:
        datos = json.loads(r.read())
    return _json_de_texto(datos.get("message", {}).get("content", ""))


# --- común --------------------------------------------------------------------------

def _json_de_texto(texto: str) -> dict:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[1].rsplit("```", 1)[0]
    ini, fin = texto.find("{"), texto.rfind("}")
    if ini < 0 or fin < 0:
        raise ErrorProveedor("El modelo no devolvió JSON.")
    return json.loads(texto[ini:fin + 1])


def disponibles() -> dict:
    return {
        "anthropic": bool(leer_env().get("ANTHROPIC_API_KEY")),
        "claude-code": bool(claude_bin()),
        "ollama": bool(ollama_modelos()),
    }


def elegido() -> tuple[str, str]:
    """(proveedor, modelo) según ajustes; «auto» toma el primero disponible."""
    env = leer_env()
    proveedor = ajuste("proveedor", env.get("HUM_PROVEEDOR", "auto"))
    modelo = ajuste("modelo", env.get("HUM_MODELO", ""))
    if proveedor == "auto":
        hay = disponibles()
        proveedor = next((p for p in ("anthropic", "claude-code", "ollama") if hay[p]), "")
        modelo = ""
        if not proveedor:
            raise ErrorProveedor(
                "HUM todavía no tiene con qué pensar. La forma más simple: abrí «Configurar Ideas Box» "
                "(instala Claude Code con tu cuenta). También podés cargar una clave de Anthropic en Ajustes "
                "o instalar un modelo local con Ollama."
            )
    return proveedor, modelo


def conversar(estable: str, vivo: str, mensajes: list[dict], rapido: bool = False) -> Iterator[str]:
    proveedor, modelo = elegido()
    funcion = {"anthropic": _anthropic_conversar, "claude-code": _claude_conversar, "ollama": _ollama_conversar}[proveedor]
    return funcion(estable, vivo, mensajes, rapido, modelo)


def estructurado(sistema: str, pedido: str, esquema: dict) -> dict:
    proveedor, modelo = elegido()
    funcion = {"anthropic": _anthropic_estructurado, "claude-code": _claude_estructurado, "ollama": _ollama_estructurado}[proveedor]
    return funcion(sistema, pedido, esquema, modelo)
