// Mi mapa: las 12 inteligencias, cómo te percibís, cómo cambia y lo que HUM va entendiendo.
import { useEffect, useState } from 'react'
import { api, type Mapa as MapaT } from '../api'
import Orbe from '../components/Orbe'
import Radar from '../components/Radar'

const EVIDENCIA: Record<string, string> = { A: 'respaldo sólido', B: 'respaldo moderado', C: 'respaldo débil o conceptual' }

export default function Mapa() {
  const [mapa, setMapa] = useState<MapaT | null>(null)
  const [elegida, setElegida] = useState('vital')
  const [reevaluar, setReevaluar] = useState<Record<string, number> | null>(null)

  const cargar = () => api.mapa().then(setMapa)
  useEffect(() => { void cargar() }, [])
  if (!mapa) return <div className="grid h-full place-items-center"><Orbe tam={60} estado="pensando" /></div>

  const i = mapa.inteligencias.find((x) => x.id === elegida)!
  const dim = mapa.dimensiones.find((d) => d.id === i.dimension_id)!

  async function guardarEvaluacion() {
    if (!reevaluar) return
    await api.autoevaluar(reevaluar); setReevaluar(null); void cargar()
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold">Mi mapa</h1>
          <p className="mt-1 max-w-2xl text-tenue">Las 12 inteligencias de JFlow son un mapa para mirar tu vida completa. Los números son tu autopercepción, no una medición: lo valioso es cómo cambian.</p>
        </div>
        <button className="boton boton-sutil" onClick={() => setReevaluar(Object.fromEntries(mapa.inteligencias.map((x) => [x.id, x.autopercepcion ?? 5])))}>Volver a evaluarme</button>
      </div>

      {reevaluar && (
        <div className="tarjeta mt-6 p-5">
          <h2 className="font-semibold">¿Cómo te percibís hoy?</h2>
          <div className="mt-3 grid gap-x-8 gap-y-2 md:grid-cols-2 lg:grid-cols-3">
            {mapa.inteligencias.map((x) => (
              <label key={x.id} className="block">
                <div className="flex justify-between text-sm"><span>{x.icono} {x.nombre}</span><b className="tabular-nums">{reevaluar[x.id]}</b></div>
                <input type="range" min={1} max={10} value={reevaluar[x.id]} className="w-full" onChange={(e) => setReevaluar({ ...reevaluar, [x.id]: Number(e.target.value) })} />
              </label>
            ))}
          </div>
          <div className="mt-4 flex gap-2"><button className="boton boton-primario" onClick={guardarEvaluacion}>Guardar</button><button className="boton boton-sutil" onClick={() => setReevaluar(null)}>Cancelar</button></div>
        </div>
      )}

      <div className="mt-6 grid items-start gap-6 lg:grid-cols-2">
        <div className="tarjeta p-4"><Radar dimensiones={mapa.dimensiones} inteligencias={mapa.inteligencias} elegida={elegida} alElegir={setElegida} /></div>

        <article className="tarjeta p-6">
          <p className="text-sm font-semibold uppercase tracking-widest" style={{ color: dim.color }}>{dim.nombre}</p>
          <h2 className="mt-1 text-2xl font-semibold">{i.icono} Inteligencia {i.nombre.toLowerCase()}</h2>
          <p className="mt-2 leading-relaxed">{i.definicion}</p>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-xl bg-capa-2 p-2"><p className="text-2xl font-semibold">{i.autopercepcion ?? '—'}</p><p className="text-xs text-tenue">te percibís</p></div>
            <div className="rounded-xl bg-capa-2 p-2"><p className="text-2xl font-semibold">{i.actividad_30d.acciones_hechas}</p><p className="text-xs text-tenue">acciones en 30 días</p></div>
            <div className="rounded-xl bg-capa-2 p-2"><p className="text-2xl font-semibold">{i.actividad_30d.avances}<span className="text-base text-tenue"> / {i.actividad_30d.dificultades}</span></p><p className="text-xs text-tenue">avances / dificultades</p></div>
          </div>

          <h3 className="mt-5 text-sm font-semibold uppercase tracking-wider text-tenue">Lo que HUM entiende hoy</h3>
          <p className="mt-1">{i.lectura || <span className="text-tenue">Todavía no charlaron sobre esto. HUM la va a ir conociendo con el tiempo.</span>}</p>
          {i.observaciones.length > 0 && (
            <ul className="mt-2 space-y-1 text-sm text-tenue">
              {i.observaciones.slice(0, 4).map((o, k) => <li key={k}>{o.senal > 0 ? '▲' : o.senal < 0 ? '▼' : '•'} {o.texto}</li>)}
            </ul>
          )}

          <h3 className="mt-5 text-sm font-semibold uppercase tracking-wider text-tenue">Prácticas para desarrollarla</h3>
          <ul className="mt-2 space-y-2">
            {i.practicas.map((p) => (
              <li key={p.nombre} className="rounded-xl bg-capa-2 px-3 py-2">
                <p className="font-medium">{p.nombre} <span className="ml-1 rounded bg-black/30 px-1.5 py-0.5 text-[10px] text-tenue" title={EVIDENCIA[p.evidencia[0]]}>evidencia {p.evidencia}</span></p>
                <p className="text-sm text-tenue">{p.como}</p>
              </li>
            ))}
          </ul>

          <h3 className="mt-5 text-sm font-semibold uppercase tracking-wider text-tenue">Preguntas para pensarla</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{i.preguntas.map((q) => <li key={q}>{q}</li>)}</ul>
          {i.cuidado && <p className="mt-4 rounded-xl border border-amber-500/30 bg-amber-950/30 p-3 text-sm text-amber-100">⚠️ {i.cuidado}</p>}
          <p className="mt-4 text-xs text-tenue">En qué se apoya: {i.base}</p>
        </article>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {mapa.dimensiones.map((d) => (
          <div key={d.id} className="tarjeta p-4">
            <p className="font-semibold" style={{ color: d.color }}>{d.nombre}</p>
            <p className="mb-2 text-xs text-tenue">{d.descripcion}</p>
            {mapa.inteligencias.filter((x) => x.dimension_id === d.id).map((x) => (
              <button key={x.id} onClick={() => setElegida(x.id)} className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm ${x.id === elegida ? 'bg-capa-2' : 'hover:bg-capa-2/60'}`}>
                <span className="w-28 shrink-0">{x.icono} {x.nombre}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-black/30">
                  <span className="block h-full rounded-full" style={{ width: `${(x.autopercepcion ?? 0) * 10}%`, background: d.color }} />
                </span>
                <span className="w-6 text-right tabular-nums text-tenue">{x.autopercepcion ?? '—'}</span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
