// Versiones nuevas de HUM: aviso en el panel, novedades y actualización con un botón (sin terminal).
import { useCallback, useEffect, useState } from 'react'
import { api, type Version } from '../api'
import Orbe from './Orbe'

const OMITIDA = 'hum-version-omitida'
const clave = (v: Version) => `${v.nueva_version}|${v.novedades[0] ?? ''}|${v.novedades.length}`

/** Estado de versión compartido: se consulta al abrir y después cada hora (el servidor revisa el repo cada 6 h). */
export function useVersion() {
  const [v, setV] = useState<Version | null>(null)
  const cargar = useCallback((revisar = false) => api.version(revisar).then((x) => { setV(x); return x }), [])
  useEffect(() => {
    void cargar().catch(() => {})
    const t = setInterval(() => { void cargar().catch(() => {}) }, 3600_000)
    return () => clearInterval(t)
  }, [cargar])
  return { v, cargar }
}

/** Pantalla mientras se actualiza: espera a que HUM vuelva con la versión nueva y recarga. */
export function Actualizando({ desde, alFallar }: { desde: string; alFallar: (detalle: string) => void }) {
  const [segundos, setSegundos] = useState(0)
  useEffect(() => {
    const inicio = Date.now()
    let vivo = true
    const vuelta = async () => {
      while (vivo) {
        await new Promise((ok) => setTimeout(ok, 3000))
        setSegundos(Math.round((Date.now() - inicio) / 1000))
        try {
          const x = await api.version()
          if (x.proceso.estado === 'error') return alFallar(x.proceso.detalle || 'La actualización no se pudo completar.')
          if (x.proceso.estado === 'ok' && x.commit && x.commit !== desde) return location.reload()
        } catch { /* el servidor se está reiniciando */ }
        if (Date.now() - inicio > 10 * 60_000) return alFallar('HUM tardó demasiado en volver. Cerralo y abrilo de nuevo.')
      }
    }
    void vuelta()
    return () => { vivo = false }
  }, [desde, alFallar])
  return (
    <div className="fixed inset-0 z-[60] grid place-items-center bg-noche/95 px-6 text-center backdrop-blur">
      <div>
        <div className="mx-auto mb-6 w-fit"><Orbe tam={120} estado="pensando" /></div>
        <p className="text-xl">Actualizando HUM…</p>
        <p className="mt-2 text-tenue">Bajo la versión nueva y me reinicio. Puede tardar unos minutos: no cierres esta ventana.</p>
        <p className="mt-4 text-xs text-tenue tabular-nums">{segundos} s</p>
      </div>
    </div>
  )
}

function useActualizar(v: Version | null) {
  const [actualizando, setActualizando] = useState(false)
  const [error, setError] = useState('')
  const empezar = async () => {
    if (!confirm('HUM se va a actualizar y reiniciar. Si estás en una charla por voz, se corta. ¿Seguimos?')) return
    setError('')
    try { await api.actualizar(); setActualizando(true) } catch (e) { setError((e as Error).message) }
  }
  const alFallar = useCallback((d: string) => { setActualizando(false); setError(d) }, [])
  const pantalla = actualizando && v ? <Actualizando desde={v.commit} alFallar={alFallar} /> : null
  return { empezar, error, pantalla }
}

function Novedades({ v }: { v: Version }) {
  return (
    <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-tenue">
      {v.novedades.map((n, i) => <li key={i}>{n}</li>)}
    </ul>
  )
}

/** Franja arriba del panel cuando hay versión nueva. «Más tarde» la oculta hasta que salga otra. */
export function AvisoVersion({ v }: { v: Version | null }) {
  const [abierto, setAbierto] = useState(false)
  const [omitida, setOmitida] = useState(() => localStorage.getItem(OMITIDA))
  const { empezar, error, pantalla } = useActualizar(v)
  if (pantalla) return pantalla
  if (!v?.disponible || !v.puede || omitida === clave(v)) return null
  return (
    <div className="border-b border-cyan-500/30 bg-cyan-950/40 px-6 py-2 text-sm text-cyan-100">
      <div className="flex flex-wrap items-center gap-3">
        <span>✨ Hay una versión nueva de HUM{v.nueva_version && v.nueva_version !== v.version ? ` (${v.nueva_version})` : ''}.</span>
        <button className="underline" onClick={() => setAbierto(!abierto)}>{abierto ? 'Ocultar novedades' : 'Ver novedades'}</button>
        <button className="boton boton-primario px-3 py-1 text-sm" onClick={empezar}>Actualizar ahora</button>
        <button className="text-tenue underline" onClick={() => { localStorage.setItem(OMITIDA, clave(v)); setOmitida(clave(v)) }}>Más tarde</button>
      </div>
      {abierto && <Novedades v={v} />}
      {error && <p className="mt-1 text-amber-300">{error}</p>}
    </div>
  )
}

/** Sección de Ajustes: versión instalada, buscar y actualizar. */
export function SeccionVersion({ v, cargar }: { v: Version | null; cargar: (revisar?: boolean) => Promise<Version> }) {
  const [buscando, setBuscando] = useState(false)
  const { empezar, error, pantalla } = useActualizar(v)
  const buscar = async () => { setBuscando(true); try { await cargar(true) } catch { /* se muestra el motivo */ } setBuscando(false) }
  return (
    <section className="tarjeta p-5">
      {pantalla}
      <h2 className="font-semibold">Versión</h2>
      <p className="mt-2 text-sm text-tenue">
        Tenés HUM <b className="text-tinta">{v?.version ?? '…'}</b>{v?.commit && <> · {v.commit}</>}
        {v?.revisado && <> · revisado {new Date(v.revisado).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })}</>}
      </p>
      {v?.motivo && <p className="mt-2 text-sm text-amber-300">{v.motivo}</p>}
      {v?.disponible ? (
        <div className="mt-3">
          <p>✨ Hay una versión nueva{v.nueva_version && v.nueva_version !== v.version ? ` (${v.nueva_version})` : ''}. Novedades:</p>
          <Novedades v={v} />
          <button className="boton boton-primario mt-3" onClick={empezar}>Actualizar ahora</button>
        </div>
      ) : v?.puede && !v.motivo && <p className="mt-2 text-sm">Estás al día.</p>}
      {v?.commit && (
        <button className="boton boton-sutil mt-3" disabled={buscando} onClick={buscar}>{buscando ? 'Buscando…' : 'Buscar actualizaciones'}</button>
      )}
      {error && <p className="mt-2 text-sm text-amber-300">{error}</p>}
    </section>
  )
}
