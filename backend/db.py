"""
Base de datos de HUM (SQLite, un archivo en el home de la persona).

Qué guarda y por qué:
  persona            quién es, cómo quiere que le hablen, su contexto de vida
  autoevaluaciones   cómo se percibe en cada inteligencia, con historia: así se ve si mejora
  inteligencias      la lectura viva que HUM hace de cada una (texto), actualizada al digerir
  conversaciones     chats y charlas por voz
  mensajes
  recuerdos          lo que HUM aprendió de su vida (hechos, experiencias, emociones, vínculos…)
  observaciones      evidencia concreta por inteligencia que sale de las conversaciones
  metas              lo que quiere lograr, con WOOP (deseo, resultado, obstáculo, plan si-entonces)
  acciones           micro-hábitos y pasos; las propone HUM, las acepta la persona
  acciones_hechas    registro de cumplimiento
  seguimientos       «preguntarle el jueves cómo le fue»: lo que HUM retoma después
  registros          check-in del día (ánimo, energía, sueño)
  ajustes            preferencias de la app

Regla de oro: lo que cambia la vida de la persona (metas, acciones) entra como
«propuesta» y solo pasa a «activa» cuando la persona la acepta.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config import DATA_DIR, DB_PATH

ESQUEMA = """
CREATE TABLE IF NOT EXISTS persona (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    nombre TEXT NOT NULL DEFAULT '',
    como_llamarte TEXT NOT NULL DEFAULT '',
    contexto TEXT NOT NULL DEFAULT '',          -- trabajo, familia, momento de vida (texto libre)
    valores TEXT NOT NULL DEFAULT '',           -- lo que le importa
    onboarding INTEGER NOT NULL DEFAULT 0,
    creada TEXT NOT NULL,
    actualizada TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS autoevaluaciones (
    id INTEGER PRIMARY KEY,
    inteligencia TEXT NOT NULL,
    valor INTEGER NOT NULL CHECK (valor BETWEEN 1 AND 10),
    fecha TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_autoeval ON autoevaluaciones(inteligencia, fecha);

CREATE TABLE IF NOT EXISTS inteligencias (
    id TEXT PRIMARY KEY,
    lectura TEXT NOT NULL DEFAULT '',           -- lo que HUM entiende hoy de esta inteligencia en la persona
    actualizada TEXT
);

CREATE TABLE IF NOT EXISTS conversaciones (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL DEFAULT 'Conversación nueva',
    modo TEXT NOT NULL DEFAULT 'texto',
    creada TEXT NOT NULL,
    actualizada TEXT NOT NULL,
    digerida_hasta INTEGER NOT NULL DEFAULT 0,  -- id del último mensaje ya digerido
    archivada INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY,
    conversacion_id INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    rol TEXT NOT NULL CHECK (rol IN ('user', 'assistant')),
    contenido TEXT NOT NULL,
    por_voz INTEGER NOT NULL DEFAULT 0,
    creado TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mensajes ON mensajes(conversacion_id, id);

CREATE TABLE IF NOT EXISTS recuerdos (
    id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL,                         -- hecho, experiencia, emocion, aprendizaje, vinculo, valor, preferencia, salud
    contenido TEXT NOT NULL,
    inteligencias TEXT NOT NULL DEFAULT '',     -- ids separados por coma
    importancia INTEGER NOT NULL DEFAULT 3,
    fecha TEXT NOT NULL,
    conversacion_id INTEGER,
    activo INTEGER NOT NULL DEFAULT 1
);
CREATE VIRTUAL TABLE IF NOT EXISTS recuerdos_fts USING fts5(
    contenido, content='recuerdos', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS recuerdos_ai AFTER INSERT ON recuerdos BEGIN
    INSERT INTO recuerdos_fts(rowid, contenido) VALUES (new.id, new.contenido);
END;
CREATE TRIGGER IF NOT EXISTS recuerdos_ad AFTER DELETE ON recuerdos BEGIN
    INSERT INTO recuerdos_fts(recuerdos_fts, rowid, contenido) VALUES ('delete', old.id, old.contenido);
END;
CREATE TRIGGER IF NOT EXISTS recuerdos_au AFTER UPDATE OF contenido ON recuerdos BEGIN
    INSERT INTO recuerdos_fts(recuerdos_fts, rowid, contenido) VALUES ('delete', old.id, old.contenido);
    INSERT INTO recuerdos_fts(rowid, contenido) VALUES (new.id, new.contenido);
END;

CREATE TABLE IF NOT EXISTS observaciones (
    id INTEGER PRIMARY KEY,
    inteligencia TEXT NOT NULL,
    texto TEXT NOT NULL,
    senal INTEGER NOT NULL DEFAULT 0,           -- 1 fortaleza o avance, -1 dificultad, 0 neutro
    fecha TEXT NOT NULL,
    conversacion_id INTEGER
);
CREATE INDEX IF NOT EXISTS ix_obs ON observaciones(inteligencia, fecha);

CREATE TABLE IF NOT EXISTS metas (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,
    porque TEXT NOT NULL DEFAULT '',
    area TEXT NOT NULL DEFAULT '',              -- trabajo, familia, salud, finanzas, aprendizaje, vínculos, propósito…
    inteligencias TEXT NOT NULL DEFAULT '',
    deseo TEXT NOT NULL DEFAULT '',             -- WOOP
    resultado TEXT NOT NULL DEFAULT '',
    obstaculo TEXT NOT NULL DEFAULT '',
    plan TEXT NOT NULL DEFAULT '',              -- «si <obstáculo>, entonces <acción>»
    horizonte TEXT NOT NULL DEFAULT '',         -- semana, mes, trimestre, año
    estado TEXT NOT NULL DEFAULT 'propuesta',   -- propuesta, activa, pausada, lograda, descartada
    progreso INTEGER NOT NULL DEFAULT 0,
    origen TEXT NOT NULL DEFAULT 'persona',     -- persona | hum
    conversacion_id INTEGER,
    creada TEXT NOT NULL,
    actualizada TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS acciones (
    id INTEGER PRIMARY KEY,
    meta_id INTEGER REFERENCES metas(id) ON DELETE SET NULL,
    titulo TEXT NOT NULL,
    inteligencia TEXT NOT NULL DEFAULT '',
    frecuencia TEXT NOT NULL DEFAULT 'una_vez', -- una_vez, diaria, semanal, dias_semana
    si_entonces TEXT NOT NULL DEFAULT '',       -- intención de implementación: «después de X, hago Y»
    estado TEXT NOT NULL DEFAULT 'propuesta',   -- propuesta, activa, hecha, descartada
    origen TEXT NOT NULL DEFAULT 'persona',
    conversacion_id INTEGER,
    creada TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS acciones_hechas (
    id INTEGER PRIMARY KEY,
    accion_id INTEGER NOT NULL REFERENCES acciones(id) ON DELETE CASCADE,
    fecha TEXT NOT NULL,                        -- AAAA-MM-DD
    nota TEXT NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_hechas ON acciones_hechas(accion_id, fecha);

CREATE TABLE IF NOT EXISTS seguimientos (
    id INTEGER PRIMARY KEY,
    texto TEXT NOT NULL,
    fecha TEXT NOT NULL,                        -- desde cuándo retomarlo (AAAA-MM-DD)
    estado TEXT NOT NULL DEFAULT 'pendiente',   -- pendiente, hecho, descartado
    conversacion_id INTEGER,
    creado TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL UNIQUE,                 -- AAAA-MM-DD, uno por día
    animo INTEGER,
    energia INTEGER,
    sueno REAL,
    nota TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS foco_diario (
    fecha TEXT PRIMARY KEY,
    inteligencia TEXT NOT NULL,
    texto TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def hoy() -> str:
    return datetime.now().date().isoformat()


def _conectar() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


@contextmanager
def db():
    con = _conectar()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def iniciar() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.chmod(0o700)
    with db() as con:
        con.executescript(ESQUEMA)
        if not con.execute("SELECT 1 FROM persona WHERE id = 1").fetchone():
            con.execute("INSERT INTO persona (id, creada, actualizada) VALUES (1, ?, ?)", (ahora(), ahora()))
    DB_PATH.chmod(0o600)


def filas(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def ajuste(clave: str, defecto: str = "") -> str:
    with db() as con:
        r = con.execute("SELECT valor FROM ajustes WHERE clave = ?", (clave,)).fetchone()
    return r["valor"] if r else defecto


def guardar_ajuste(clave: str, valor: str) -> None:
    with db() as con:
        con.execute(
            "INSERT INTO ajustes (clave, valor) VALUES (?, ?) ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, valor),
        )
