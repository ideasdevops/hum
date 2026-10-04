// Hoy: cómo estás, en qué enfocarte, lo que te propusiste y lo que HUM quiere retomar.
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type Hoy as HoyT } from '../api'
import Orbe from '../components/Orbe'

const FRECUENCIA: Record<string, string> = { una_vez: 'una vez', diaria: 'diaria', semanal: 'semanal', dias_semana: 'algunos días' }

function Escala({ etiqueta, valor, alCambiar, min = 1, max = 10, paso = 1, sufijo = '' }:
  { etiqueta: string; valor: number | null; alCambiar: (v: number) => void; min?: number; max?: number; paso?: number; sufijo?: string }) {
  return (
    <label className="block">
      <div className="flex justify-between text-sm"><span className="text-tenue">{etiqueta}</span><span className="font-semibold tabular-nums">{valor ?? '—'}{valor !== null ? sufijo : ''}</span></div>
      <input type="range" min={min} max={max} step={paso} value={valor ?? Math.round((min + max) / 2)} className="w-full"
        onChange={(e) => alCambiar(Number(e.target.value))} />
    </label>
  )
}

export default function Hoy() {
  const [hoy, setHoy] = useState<HoyT | null>(null)
  const [registro, setRegistro] = useState<{ animo: number | null; energia: number | null; sueno: number | null; nota: string }>({ animo: null, energia: null, sueno: null, nota: '' })
  const [guardado, setGuardado] = useState(false)
  const [cargandoFoco, setCargandoFoco] = useState(false)
  const [errorFoco, setErrorFoco] = useState('')
  const navegar = useNavigate()

  const cargar = useCallback(() => api.hoy().then((h) => { setHoy(h); if (h.registro) setRegistro({ ...h.registro, nota: h.registro.nota ?? '' }) }), [])
  useEffect(() => { void cargar() }, [cargar])

  async function pedirFoco(rehacer = false) {
    setCargandoFoco(true); setErrorFoco('')
    try { await api.foco(rehacer); await cargar() } catch (e) { setErrorFoco((e as Error).message) }
    setCargandoFoco(false)
  }

  async function guardarRegistro() {
    await api.registrar(registro); setGuardado(true); setTimeout(() => setGuardado(false), 2500)
  }

  async function marcar(id: number, hecha: boolean) { await api.marcarHoy(id, hecha); void cargar() }
  async function seguimiento(id: number, estado: string) { await api.seguimiento(id, estado); void cargar() }

  if (!hoy) return <div className="grid h-full place-items-center"><Orbe tam={60} estado="pensando" /></div>
  const fecha = new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <p className="text-sm text-tenue first-letter:uppercase">{fecha}</p>
      <h1 className="mt-1 text-3xl font-semibold">{hoy.saludo} 👋</h1>
      {hoy.racha > 1 && <p className="mt-1 text-tenue">Llevás <b className="text-tinta">{hoy.racha} días seguidos</b> cumpliendo algo de tus planes.</p>}

      {hoy.propuestas > 0 && (
        <Link to="/planes" className="mt-5 flex items-center gap-3 rounded-2xl border border-mente/40 bg-mente/10 px-4 py-3 hover:bg-mente/20">
          <span className="text-xl">🌱</span>
          <span>HUM te dejó <b>{hoy.propuestas} propuesta{hoy.propuestas > 1 ? 's' : ''}</b> a partir de sus charlas. Revisalas en Planes.</span>
        </Link>
      )}

      <div className="mt-6 grid gap-5 lg:grid-cols-5">
        <section className="tarjeta p-5 lg:col-span-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">✨ Tu foco de hoy</h2>
            {hoy.foco && <button className="text-sm text-tenue hover:text-tinta" disabled={cargandoFoco} onClick={() => pedirFoco(true)}>Otro</button>}
          </div>
          {hoy.foco ? (
            <>
              <p className="mt-2 text-sm uppercase tracking-widest text-mente">{hoy.foco.nombre}</p>
              <p className="mt-1 text-lg leading-relaxed">{hoy.foco.texto}</p>
            </>
          ) : (
            <div className="mt-3">
              <p className="text-tenue">HUM elige una inteligencia y una práctica chiquita para hoy, según tu vida y cómo amaneciste.</p>
              <button className="boton boton-primario mt-3" disabled={cargandoFoco} onClick={() => pedirFoco()}>{cargandoFoco ? 'Pensando…' : 'Proponeme un foco'}</button>
            </div>
          )}
          {errorFoco && <p className="mt-2 text-sm text-amber-300">{errorFoco}</p>}
        </section>

        <section className="tarjeta space-y-3 p-5 lg:col-span-2">
          <h2 className="font-semibold">🌡️ ¿Cómo estás hoy?</h2>
          <Escala etiqueta="Ánimo" valor={registro.animo} alCambiar={(v) => setRegistro({ ...registro, animo: v })} />
          <Escala etiqueta="Energía" valor={registro.energia} alCambiar={(v) => setRegistro({ ...registro, energia: v })} />
          <Escala etiqueta="Horas de sueño" valor={registro.sueno} min={0} max={12} paso={0.5} sufijo=" h" alCambiar={(v) => setRegistro({ ...registro, sueno: v })} />
          <input className="campo text-sm" placeholder="Una nota (opcional)" value={registro.nota} onChange={(e) => setRegistro({ ...registro, nota: e.target.value })} />
          <button className="boton boton-sutil w-full" onClick={guardarRegistro}>{guardado ? '✓ Guardado' : 'Guardar'}</button>
        </section>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <section className="tarjeta p-5">
          <h2 className="font-semibold">🌱 Lo que te propusiste</h2>
          {!hoy.acciones.length && <p className="mt-2 text-sm text-tenue">Todavía no hay acciones activas. Charlá con HUM sobre algo que quieras mejorar, o creá una en Planes.</p>}
          <ul className="mt-3 space-y-2">
            {hoy.acciones.map((a) => (
              <li key={a.id} className="flex items-start gap-3 rounded-xl bg-capa-2 px-3 py-2.5">
                <input type="checkbox" checked={!!a.hecha_hoy} onChange={(e) => marcar(a.id, e.target.checked)} className="mt-1 h-5 w-5 accent-[#8b5cf6]" />
                <div className="min-w-0">
                  <p className={a.hecha_hoy ? 'text-tenue line-through' : ''}>{a.titulo}</p>
                  <p className="text-xs text-tenue">{FRECUENCIA[a.frecuencia] ?? a.frecuencia}{a.meta_titulo && <> · {a.meta_titulo}</>}</p>
                  {a.si_entonces && !a.hecha_hoy && <p className="mt-1 text-xs italic text-tenue">{a.si_entonces}</p>}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="tarjeta p-5">
          <h2 className="font-semibold">💭 HUM quiere retomar</h2>
          {!hoy.seguimientos.length && <p className="mt-2 text-sm text-tenue">Nada pendiente por ahora.</p>}
          <ul className="mt-3 space-y-2">
            {hoy.seguimientos.map((s) => (
              <li key={s.id} className="rounded-xl bg-capa-2 px-3 py-2.5">
                <p>{s.texto}</p>
                <div className="mt-2 flex gap-2 text-sm">
                  <button className="boton boton-primario px-3 py-1" onClick={() => navegar('/conversar')}>Charlarlo</button>
                  <button className="boton boton-sutil px-3 py-1" onClick={() => seguimiento(s.id, 'hecho')}>Ya está</button>
                  <button className="px-2 text-tenue hover:text-tinta" onClick={() => seguimiento(s.id, 'descartado')}>Descartar</button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
