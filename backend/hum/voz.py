"""
La voz de HUM, 100 % local: lo que la persona dice no sale del equipo para ser transcripto.

  Oído  faster-whisper (Whisper en CPU, int8). Modelo «small» por defecto: buen español
        en equipos modestos. Se baja solo la primera vez (~480 MB).
  Voz   Piper (ONNX, rapidísimo en CPU). Voz por defecto es_AR «daniela» (alta calidad).
        Se baja sola la primera vez (~110 MB).

Los modelos se cargan una sola vez y quedan en memoria.
"""
import importlib.util
import io
import logging
import tempfile
import threading
import urllib.request
import wave
from pathlib import Path

from config import MODELOS_DIR, MODELOS_SISTEMA, WHISPER_DEFECTO
from db import ajuste

log = logging.getLogger("hum.voz")

VOCES = {
    "es_AR-daniela-high": "es/es_AR/daniela/high/es_AR-daniela-high",
    "es_MX-claude-high": "es/es_MX/claude/high/es_MX-claude-high",
    "es_ES-sharvard-medium": "es/es_ES/sharvard/medium/es_ES-sharvard-medium",
}
_HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"

_whisper = None
_whisper_nombre = None
_voz = None
_voz_nombre = None
_candado = threading.Lock()


class ErrorVoz(RuntimeError):
    pass


def _modelo_whisper():
    global _whisper, _whisper_nombre
    nombre = ajuste("whisper_modelo", WHISPER_DEFECTO)
    with _candado:
        if _whisper is None or _whisper_nombre != nombre:
            try:
                from faster_whisper import WhisperModel  # noqa: PLC0415
            except ImportError:
                raise ErrorVoz("Falta faster-whisper (pip install faster-whisper).")
            MODELOS_DIR.mkdir(parents=True, exist_ok=True)
            log.info("cargando Whisper %s…", nombre)
            del_sistema = MODELOS_SISTEMA / "whisper" / nombre
            if (del_sistema / "model.bin").exists():
                _whisper = WhisperModel(str(del_sistema), device="cpu", compute_type="int8")
            else:
                _whisper = WhisperModel(nombre, device="cpu", compute_type="int8",
                                        download_root=str(MODELOS_DIR / "whisper"))
            _whisper_nombre = nombre
    return _whisper


def transcribir(audio: bytes, sufijo: str = ".webm") -> str:
    """Audio del navegador (webm/ogg/wav) → texto. ffmpeg decodifica vía PyAV."""
    modelo = _modelo_whisper()
    with tempfile.NamedTemporaryFile(suffix=sufijo) as f:
        f.write(audio)
        f.flush()
        segmentos, _info = modelo.transcribe(
            f.name, language="es", beam_size=1, vad_filter=True,
            initial_prompt=("Conversación en español rioplatense con HUM, la inteligencia humanizada de JFlowOS. "
                            "Palabras propias: HUM, JFlowOS, JFlow, UEI, Ideas Box, DisruptIA, IdeasDevOps."),
        )
        return " ".join(s.text.strip() for s in segmentos).strip()


def _archivos_voz(nombre: str) -> Path:
    ruta = VOCES.get(nombre)
    if not ruta:
        raise ErrorVoz(f"Voz desconocida: {nombre}")
    sistema = MODELOS_SISTEMA / "piper" / f"{nombre}.onnx"
    if sistema.exists() and sistema.with_suffix(".onnx.json").exists():
        return sistema
    destino = MODELOS_DIR / "piper"
    destino.mkdir(parents=True, exist_ok=True)
    onnx = destino / f"{nombre}.onnx"
    for sufijo in (".onnx", ".onnx.json"):
        archivo = destino / f"{nombre}{sufijo}"
        if not archivo.exists():
            log.info("descargando voz %s%s…", nombre, sufijo)
            tmp = archivo.with_suffix(archivo.suffix + ".part")
            urllib.request.urlretrieve(_HF + ruta + sufijo, tmp)
            tmp.rename(archivo)
    return onnx


def _modelo_voz():
    global _voz, _voz_nombre
    nombre = ajuste("voz", "es_AR-daniela-high")
    with _candado:
        if _voz is None or _voz_nombre != nombre:
            try:
                from piper import PiperVoice  # noqa: PLC0415
            except ImportError:
                raise ErrorVoz("Falta piper-tts (pip install piper-tts).")
            _voz = PiperVoice.load(_archivos_voz(nombre))
            _voz_nombre = nombre
    return _voz


def sintetizar(texto: str) -> bytes:
    """Texto → WAV."""
    from piper import SynthesisConfig  # noqa: PLC0415

    voz = _modelo_voz()
    velocidad = float(ajuste("voz_velocidad", "1.0") or 1.0)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        voz.synthesize_wav(_limpiar_para_voz(texto), w,
                           syn_config=SynthesisConfig(length_scale=1.0 / max(0.6, min(1.6, velocidad))))
    return buf.getvalue()


def _limpiar_para_voz(texto: str) -> str:
    """Saca el markdown que no se dice en voz alta."""
    import re  # noqa: PLC0415

    t = re.sub(r"[*_`#>]+", "", texto)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"^\s*[-•]\s+", "", t, flags=re.M)
    return t.strip()


def estado() -> dict:
    # Solo se fija si están instaladas: importarlas acá cargaría las bibliotecas nativas en cada /api/estado
    hay_whisper = importlib.util.find_spec("faster_whisper") is not None
    hay_piper = importlib.util.find_spec("piper") is not None
    voz = ajuste("voz", "es_AR-daniela-high")
    return {
        "oido": hay_whisper, "voz": hay_piper,
        "whisper_modelo": ajuste("whisper_modelo", WHISPER_DEFECTO),
        "voz_elegida": voz, "voces": list(VOCES),
        "voz_descargada": (MODELOS_DIR / "piper" / f"{voz}.onnx").exists()
                          or (MODELOS_SISTEMA / "piper" / f"{voz}.onnx").exists(),
        "cargados": {"oido": _whisper is not None, "voz": _voz is not None},
    }


def precalentar() -> None:
    """Carga los modelos en segundo plano para que la primera charla por voz no espere."""
    def _tarea():
        for f in (_modelo_voz, _modelo_whisper):
            try:
                f()
            except Exception as e:  # noqa: BLE001
                log.warning("no pude precargar la voz: %s", e)
    threading.Thread(target=_tarea, daemon=True).start()
