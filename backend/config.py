"""
Configuración de HUM. Todo es local a la persona: los datos viven en su home y nunca
salen del equipo, salvo el texto de la conversación que se le manda al modelo elegido
(y con Ollama, ni eso).

    ~/.config/hum/hum.env          claves y ajustes de arranque (KEY=valor)
    ~/.local/share/hum/hum.db      la vida que HUM conoce: perfil, recuerdos, metas, conversaciones
    ~/.local/share/hum/modelos/    modelos de voz descargados (Whisper y Piper)

Las variables HUM_CONFIG_DIR y HUM_DATA_DIR cambian esas carpetas (por ejemplo, para
llevar HUM dentro de un IdeasPackage).
"""
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("HUM_CONFIG_DIR", Path.home() / ".config" / "hum")).expanduser()
DATA_DIR = Path(os.environ.get("HUM_DATA_DIR", Path.home() / ".local" / "share" / "hum")).expanduser()
ENV_PATH = CONFIG_DIR / "hum.env"
DB_PATH = DATA_DIR / "hum.db"
MODELOS_DIR = DATA_DIR / "modelos"
# Modelos de voz que ya trae el sistema (JFlowOS): se usan antes de bajar nada.
MODELOS_SISTEMA = Path(os.environ.get("HUM_MODELOS_SISTEMA", "/usr/share/jflowos/hum-modelos"))
WHISPER_DEFECTO = os.environ.get("HUM_WHISPER_MODELO", "small")

BACKEND_DIR = Path(__file__).resolve().parent
CONOCIMIENTO_DIR = BACKEND_DIR / "conocimiento"
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"

# 8412: ocho… y doce inteligencias.
PUERTO = int(os.environ.get("HUM_PUERTO", "8412"))


def leer_env() -> dict:
    """Lee hum.env (formato KEY=valor de shell). La variable de entorno gana."""
    datos: dict[str, str] = {}
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            linea = raw.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, _, v = linea.partition("=")
            datos[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("ANTHROPIC_API_KEY", "HUM_PROVEEDOR", "HUM_MODELO", "OLLAMA_URL"):
        if os.environ.get(k):
            datos[k] = os.environ[k]
    return datos


def guardar_env(cambios: dict) -> None:
    """Actualiza claves de hum.env sin pisar las demás. Archivo con permisos 600."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    actuales = {}
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in raw and not raw.strip().startswith("#"):
                k, _, v = raw.partition("=")
                actuales[k.strip()] = v.strip()
    for k, v in cambios.items():
        if v is None or v == "":
            actuales.pop(k, None)
        else:
            actuales[k] = str(v)
    contenido = "# HUM — ajustes locales. No compartir: puede tener claves.\n"
    contenido += "".join(f"{k}={v}\n" for k, v in sorted(actuales.items()))
    ENV_PATH.write_text(contenido, encoding="utf-8")
    ENV_PATH.chmod(0o600)
