"""
Actualizaciones de HUM desde el panel, sin terminal.

Solo para instalaciones hechas con git (install.sh): cada tanto se hace `git fetch` en silencio y,
si el remoto tiene commits nuevos, la interfaz lo avisa con la lista de novedades (los asuntos de
los commits). «Actualizar ahora» lanza `hum actualizar` en un proceso aparte (sesión propia, así
sobrevive al reinicio del servidor), que baja el código, pone al día las dependencias y reinicia HUM.

En JFlowOS HUM viene como paquete del sistema (sin .git): ahí se actualiza con el sistema.
"""
import json
import logging
import os
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime

from config import BACKEND_DIR, ESTADO_DIR

log = logging.getLogger("hum.actualizacion")

RAIZ = BACKEND_DIR.parent
LANZADOR = RAIZ / "bin" / "hum"
ARCHIVO_ESTADO = ESTADO_DIR / "actualizacion.json"
PID = ESTADO_DIR / "hum.pid"
CADA = 6 * 3600  # revisión automática

# Nunca preguntar credenciales: si el repo privado no es accesible sin intervención, se informa y listo.
_ENV_GIT = {
    **os.environ,
    "GIT_TERMINAL_PROMPT": "0",
    "GCM_INTERACTIVE": "never",
    "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=10",
}

_candado = threading.Lock()
_ultimo: dict = {}


def _git(*args: str, timeout: int = 15) -> str:
    r = subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True,
                       timeout=timeout, env=_ENV_GIT)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[:300] or f"git {args[0]} falló")
    return r.stdout.strip()


def version_local() -> str:
    try:
        return (RAIZ / "VERSION").read_text().strip()
    except OSError:
        return "?"


def _gestionable() -> str:
    """Devuelve el motivo por el que no se puede actualizar desde el panel, o '' si se puede."""
    if not (RAIZ / ".git").exists():
        return "Esta copia de HUM se actualiza con el sistema."
    if not LANZADOR.exists():
        return "Falta el lanzador de HUM."
    try:
        _git("remote", "get-url", "origin")
    except Exception:  # noqa: BLE001
        return "Esta copia no tiene de dónde bajar versiones nuevas."
    return ""


def _estado_proceso() -> dict:
    try:
        return json.loads(ARCHIVO_ESTADO.read_text())
    except (OSError, ValueError):
        return {}


def revisar(forzar: bool = False) -> dict:
    """Estado de versión. Con `forzar`, consulta el remoto ya; si no, usa lo último revisado."""
    global _ultimo
    with _candado:
        if _ultimo and not forzar and time.time() - _ultimo.get("_ts", 0) < CADA:
            return {**_ultimo, "proceso": _estado_proceso()}
        base = {"version": version_local(), "commit": "", "disponible": False, "nueva_version": "",
                "novedades": [], "puede": False, "motivo": "", "revisado": "", "_ts": time.time()}
        motivo = _gestionable()
        if motivo:
            _ultimo = {**base, "motivo": motivo}
            return {**_ultimo, "proceso": {}}
        try:
            base["commit"] = _git("rev-parse", "--short", "HEAD")
            rama = _git("rev-parse", "--abbrev-ref", "HEAD")
            _git("fetch", "--quiet", "origin", rama, timeout=40)
            remoto = f"origin/{rama}"
            nuevos = _git("log", "--format=%s", f"HEAD..{remoto}").splitlines()
            base.update(
                disponible=bool(nuevos), novedades=nuevos[:20], puede=True,
                revisado=datetime.now().isoformat(timespec="seconds"),
            )
            if nuevos:
                try:
                    base["nueva_version"] = _git("show", f"{remoto}:VERSION")
                except Exception:  # noqa: BLE001
                    base["nueva_version"] = ""
        except Exception as e:  # noqa: BLE001
            log.warning("no pude revisar actualizaciones: %s", e)
            base.update(motivo="No pude consultar si hay versiones nuevas (¿sin internet o sin acceso al repositorio?).",
                        puede=bool(base["commit"]))
        _ultimo = base
        return {**_ultimo, "proceso": _estado_proceso()}


def actualizar() -> dict:
    """Lanza la actualización en un proceso aparte. El servidor se va a reiniciar."""
    motivo = _gestionable()
    if motivo:
        raise RuntimeError(motivo)
    if _estado_proceso().get("estado") == "en_curso" and time.time() - _estado_proceso().get("ts", 0) < 600:
        return {"ok": True, "ya_en_curso": True}
    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    # El PID real de este servidor: así `hum actualizar` lo detiene aunque el archivo esté viejo o falte.
    PID.write_text(str(os.getpid()))
    ARCHIVO_ESTADO.write_text(json.dumps({"estado": "en_curso", "ts": time.time(), "desde": _git("rev-parse", "--short", "HEAD")}))
    registro = ESTADO_DIR / "actualizacion.log"
    # El resultado lo escribe Python: los mensajes de git traen tabulaciones y comillas que romperían un JSON armado a mano.
    escribir = ("import json, sys, time; json.dump({'estado': sys.argv[2], 'ts': time.time(), "
                "'detalle': ' '.join(open(sys.argv[3], errors='replace').read().split()[-60:]) if sys.argv[2] == 'error' else ''}, "
                "open(sys.argv[1], 'w'))")
    guion = (
        f'if bash {shlex.quote(str(LANZADOR))} actualizar; then e=ok; else e=error; fi; '
        f'{shlex.quote(sys.executable)} -c {shlex.quote(escribir)} '
        f'{shlex.quote(str(ARCHIVO_ESTADO))} "$e" {shlex.quote(str(registro))}; '
        # Si la actualización falló antes de reiniciar, el servidor sigue arriba; si se cayó, se levanta.
        f'bash {shlex.quote(str(LANZADOR))} levantar >/dev/null 2>&1 || true'
    )
    with open(registro, "w") as salida:
        subprocess.Popen(["bash", "-c", guion], cwd=str(RAIZ), stdin=subprocess.DEVNULL, stdout=salida,
                         stderr=subprocess.STDOUT, start_new_session=True, env=_ENV_GIT)
    global _ultimo
    _ultimo = {}
    return {"ok": True}


def vigilar() -> None:
    """Revisión automática en segundo plano: al minuto de arrancar y después cada 6 h."""
    def _tarea():
        time.sleep(60)
        while True:
            try:
                revisar(forzar=True)
            except Exception as e:  # noqa: BLE001
                log.warning("revisión de versión: %s", e)
            time.sleep(CADA)
    threading.Thread(target=_tarea, daemon=True).start()
