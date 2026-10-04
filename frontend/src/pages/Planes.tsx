// Planes: lo que HUM propone (vos decidís), metas con WOOP y acciones pequeñas.
import { useEffect, useState } from 'react'
import { api, type Accion, type Mapa, type Meta } from '../api'
import Orbe from '../components/Orbe'

const FRECUENCIAS = [['una_vez', 'Una vez'], ['diaria', 'Diaria'], ['semanal', 'Semanal'], ['dias_semana', 'Algunos días']]

export default function Planes() {
  const [metas, setMetas] = useState<Meta[] | null>(null)
  const [acciones, setAcciones] = useState<Accion[]>([])
  const [mapa, setMapa] = useState<Mapa | null>(null)
  const [nuevaMeta, setNuevaMeta] = useState(false)
  const [nuevaAccion, setNuevaAccion] = useState<number | null | undefined>(undefined)

  const cargar = () => api.planes().then((p) => { setMetas(p.metas); setAcciones(p.acciones) })
  useEffect(() => { void cargar(); api.mapa().then(setMapa) }, [])
  if (!metas || !mapa) return <div className="grid h-full place-items-center"><Orbe tam={60} estado="pensando" /></div>

  const nombre = (id: string) => mapa.inteligencias.find((i) => i.id === id)
  const propuestasMetas = metas.filter((m) => m.estado === 'propuesta')
  const propuestasAcciones = acciones.filter((a) => a.estado === 'propuesta' && !propuestasMetas.some((m) => m.id === a.meta_id))
  const activas = metas.filter((m) => m.estado === 'activa')
  const otras = metas.filter((m) => !['propuesta', 'activa'].includes(m.estado))
  const sueltas = acciones.filter((a) => a.estado === 'activa' && !a.meta_id)

  const meta = async (id: number, c: Partial<Meta>) => { await api.cambiarMeta(id, c); void cargar() }
  const accion = async (id: number, c: Partial<Accion>) => { await api.cambiarAccion(id, c); void cargar() }

  const Chip = ({ id }: { id: string }) => {
    const i = nombre(id); if (!i) return null
    const d = mapa.dimensiones.find((x) => x.id === i.dimension_id)!
    return <span className="rounded-full px-2 py-0.5 text-xs" style={{ background: d.color + '26', color: '#ececf4' }}>{i.icono} {i.nombre}</span>
  }

  const FilaAccion = ({ a }: { a: Accion }) => (
    <li className="flex items-start gap-3 rounded-xl bg-capa-2 px-3 py-2">
      <div className="min-w-0 flex-1">
        <p className={a.estado === 'hecha' ? 'text-tenue line-through' : ''}>{a.titulo}</p>
        {a.si_entonces && <p className="text-xs italic text-tenue">{a.si_entonces}</p>}
        <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-tenue">
          {a.inteligencia && <Chip id={a.inteligencia} />}
          <span>{FRECUENCIAS.find((f) => f[0] === a.frecuencia)?.[1]}</span>
          {!!a.hechas_7d && <span>· {a.hechas_7d} en 7 días</span>}
        </p>
      </div>
      {a.estado === 'propuesta' ? (
        <div className="flex shrink-0 gap-1">
          <button className="boton boton-primario px-3 py-1 text-sm" onClick={() => accion(a.id, { estado: 'activa' })}>Acepto</button>
          <button className="boton boton-sutil px-3 py-1 text-sm" onClick={() => accion(a.id, { estado: 'descartada' })}>No</button>
        </div>
      ) : (
        <button className="shrink-0 text-xs text-tenue hover:text-rose-300" onClick={() => accion(a.id, { estado: 'descartada' })}>Quitar</button>
      )}
    </li>
  )

  const TarjetaMeta = ({ m }: { m: Meta }) => {
    const suyas = acciones.filter((a) => a.meta_id === m.id && a.estado !== 'descartada')
    return (
      <article className={`tarjeta p-5 ${m.estado === 'propuesta' ? 'border-mente/50' : ''}`}>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="text-lg font-semibold">{m.titulo}</h3>
            <p className="mt-0.5 flex flex-wrap gap-1.5 text-xs text-tenue">
              {m.area && <span className="rounded-full bg-black/30 px-2 py-0.5">{m.area}</span>}
              {m.horizonte && <span className="rounded-full bg-black/30 px-2 py-0.5">{m.horizonte}</span>}
              {m.inteligencias.map((i) => <Chip key={i} id={i} />)}
            </p>
          </div>
          {m.estado === 'propuesta' ? (
            <div className="flex gap-2">
              <button className="boton boton-primario" onClick={() => meta(m.id, { estado: 'activa' })}>La acepto</button>
              <button className="boton boton-sutil" onClick={() => meta(m.id, { estado: 'descartada' })}>No es para mí</button>
            </div>
          ) : m.estado === 'activa' ? (
            <div className="flex gap-2 text-sm">
              <button className="boton boton-sutil px-3 py-1" onClick={() => meta(m.id, { estado: 'lograda' })}>🎉 Lograda</button>
              <button className="px-2 text-tenue hover:text-tinta" onClick={() => meta(m.id, { estado: 'pausada' })}>Pausar</button>
            </div>
          ) : (
            <button className="boton boton-sutil px-3 py-1 text-sm" onClick={() => meta(m.id, { estado: 'activa' })}>Reactivar</button>
          )}
        </div>
        {m.porque && <p className="mt-3 text-sm"><span className="text-tenue">Por qué te importa: </span>{m.porque}</p>}
        {(m.resultado || m.obstaculo || m.plan) && (
          <dl className="mt-3 grid gap-2 text-sm md:grid-cols-3">
            {m.resultado && <div className="rounded-xl bg-capa-2 p-2.5"><dt className="text-xs uppercase tracking-wider text-cuerpo">Lo mejor que puede pasar</dt><dd className="mt-1">{m.resultado}</dd></div>}
            {m.obstaculo && <div className="rounded-xl bg-capa-2 p-2.5"><dt className="text-xs uppercase tracking-wider text-espiritu">Tu obstáculo interno</dt><dd className="mt-1">{m.obstaculo}</dd></div>}
            {m.plan && <div className="rounded-xl bg-capa-2 p-2.5"><dt className="text-xs uppercase tracking-wider text-mente">Tu plan si-entonces</dt><dd className="mt-1">{m.plan}</dd></div>}
          </dl>
        )}
        {m.estado === 'activa' && (
          <label className="mt-3 flex items-center gap-3 text-sm text-tenue">Progreso
            <input type="range" min={0} max={100} step={5} defaultValue={m.progreso} className="flex-1"
              onMouseUp={(e) => meta(m.id, { progreso: Number((e.target as HTMLInputElement).value) })}
              onKeyUp={(e) => meta(m.id, { progreso: Number((e.target as HTMLInputElement).value) })} />
            <span className="w-10 text-right tabular-nums text-tinta">{m.progreso}%</span>
          </label>
        )}
        {(suyas.length > 0 || m.estado === 'activa') && (
          <ul className="mt-3 space-y-2">
            {suyas.map((a) => <FilaAccion key={a.id} a={a} />)}
            {m.estado === 'activa' && <li><button className="text-sm text-tenue hover:text-tinta" onClick={() => setNuevaAccion(m.id)}>＋ Agregar un paso</button></li>}
          </ul>
        )}
      </article>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold">Planes</h1>
          <p className="mt-1 text-tenue">Lo que charlás con HUM se convierte en propuestas. Nada entra en tus planes sin que lo aceptes.</p>
        </div>
        <div className="flex gap-2">
          <button className="boton boton-sutil" onClick={() => setNuevaAccion(null)}>＋ Acción</button>
          <button className="boton boton-primario" onClick={() => setNuevaMeta(true)}>＋ Meta</button>
        </div>
      </div>

      {(propuestasMetas.length > 0 || propuestasAcciones.length > 0) && (
        <section className="mt-6">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><Orbe tam={22} /> HUM te propone</h2>
          <div className="space-y-3">
            {propuestasMetas.map((m) => <TarjetaMeta key={m.id} m={m} />)}
            {propuestasAcciones.length > 0 && <ul className="space-y-2">{propuestasAcciones.map((a) => <FilaAccion key={a.id} a={a} />)}</ul>}
          </div>
        </section>
      )}

      <section className="mt-8">
        <h2 className="mb-3 font-semibold">En marcha</h2>
        {!activas.length && !sueltas.length && <p className="text-tenue">Todavía no hay metas activas.</p>}
        <div className="space-y-3">{activas.map((m) => <TarjetaMeta key={m.id} m={m} />)}</div>
        {sueltas.length > 0 && <><h3 className="mb-2 mt-5 text-sm text-tenue">Hábitos y acciones sueltas</h3><ul className="space-y-2">{sueltas.map((a) => <FilaAccion key={a.id} a={a} />)}</ul></>}
      </section>

      {otras.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 font-semibold text-tenue">Logradas y en pausa</h2>
          <div className="space-y-3 opacity-80">{otras.map((m) => <TarjetaMeta key={m.id} m={m} />)}</div>
        </section>
      )}

      {nuevaMeta && <FormMeta mapa={mapa} alCerrar={() => { setNuevaMeta(false); void cargar() }} />}
      {nuevaAccion !== undefined && <FormAccion mapa={mapa} metaId={nuevaAccion} alCerrar={() => { setNuevaAccion(undefined); void cargar() }} />}
    </div>
  )
}

function Modal({ titulo, children, alCerrar }: { titulo: string; children: React.ReactNode; alCerrar: () => void }) {
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/60 p-4" onClick={alCerrar}>
      <div className="tarjeta max-h-[90vh] w-full max-w-lg overflow-y-auto bg-capa p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="mb-4 text-xl font-semibold">{titulo}</h2>{children}
      </div>
    </div>
  )
}

function FormMeta({ mapa, alCerrar }: { mapa: Mapa; alCerrar: () => void }) {
  const [m, setM] = useState({ titulo: '', porque: '', area: '', resultado: '', obstaculo: '', plan: '', horizonte: 'mes', inteligencias: [] as string[] })
  const campo = (k: keyof typeof m, etiqueta: string, ayuda = '') => (
    <label className="mb-3 block text-sm"><span className="text-tenue">{etiqueta}</span>
      <input className="campo mt-1" placeholder={ayuda} value={m[k] as string} onChange={(e) => setM({ ...m, [k]: e.target.value })} /></label>
  )
  return (
    <Modal titulo="Nueva meta" alCerrar={alCerrar}>
      {campo('titulo', '¿Qué querés lograr?', 'Ej.: dormir 7 horas entre semana')}
      {campo('porque', '¿Por qué te importa?')}
      {campo('resultado', 'Lo mejor que podría pasar si lo lográs')}
      {campo('obstaculo', '¿Qué hay en vos que puede frenarte?', 'una emoción, un hábito, una creencia')}
      {campo('plan', 'Tu plan si-entonces', 'Si aparece…, entonces voy a…')}
      <div className="mb-3 grid grid-cols-2 gap-3">
        {campo('area', 'Área', 'salud, trabajo, familia…')}
        <label className="block text-sm"><span className="text-tenue">Horizonte</span>
          <select className="campo mt-1" value={m.horizonte} onChange={(e) => setM({ ...m, horizonte: e.target.value })}>
            {['semana', 'mes', 'trimestre', 'año'].map((h) => <option key={h}>{h}</option>)}
          </select></label>
      </div>
      <p className="mb-1 text-sm text-tenue">Inteligencias que trabaja</p>
      <div className="mb-4 flex flex-wrap gap-1.5">
        {mapa.inteligencias.map((i) => (
          <button key={i.id} onClick={() => setM({ ...m, inteligencias: m.inteligencias.includes(i.id) ? m.inteligencias.filter((x) => x !== i.id) : [...m.inteligencias, i.id] })}
            className={`rounded-full border px-2.5 py-1 text-xs ${m.inteligencias.includes(i.id) ? 'border-mente bg-mente/20' : 'border-borde'}`}>{i.icono} {i.nombre}</button>
        ))}
      </div>
      <div className="flex justify-end gap-2">
        <button className="boton boton-sutil" onClick={alCerrar}>Cancelar</button>
        <button className="boton boton-primario" disabled={!m.titulo.trim()} onClick={async () => { await api.crearMeta({ ...m, estado: 'activa' }); alCerrar() }}>Crear</button>
      </div>
    </Modal>
  )
}

function FormAccion({ mapa, metaId, alCerrar }: { mapa: Mapa; metaId: number | null; alCerrar: () => void }) {
  const [a, setA] = useState({ titulo: '', si_entonces: '', frecuencia: 'diaria', inteligencia: '' })
  return (
    <Modal titulo="Nueva acción" alCerrar={alCerrar}>
      <label className="mb-3 block text-sm"><span className="text-tenue">¿Qué vas a hacer? (en chiquito)</span>
        <input className="campo mt-1" value={a.titulo} placeholder="Ej.: caminar 10 minutos" onChange={(e) => setA({ ...a, titulo: e.target.value })} /></label>
      <label className="mb-3 block text-sm"><span className="text-tenue">¿Después de qué lo hacés?</span>
        <input className="campo mt-1" value={a.si_entonces} placeholder="Después de almorzar, voy a…" onChange={(e) => setA({ ...a, si_entonces: e.target.value })} /></label>
      <div className="mb-4 grid grid-cols-2 gap-3">
        <label className="block text-sm"><span className="text-tenue">Frecuencia</span>
          <select className="campo mt-1" value={a.frecuencia} onChange={(e) => setA({ ...a, frecuencia: e.target.value })}>
            {FRECUENCIAS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
          </select></label>
        <label className="block text-sm"><span className="text-tenue">Inteligencia</span>
          <select className="campo mt-1" value={a.inteligencia} onChange={(e) => setA({ ...a, inteligencia: e.target.value })}>
            <option value="">—</option>
            {mapa.inteligencias.map((i) => <option key={i.id} value={i.id}>{i.nombre}</option>)}
          </select></label>
      </div>
      <div className="flex justify-end gap-2">
        <button className="boton boton-sutil" onClick={alCerrar}>Cancelar</button>
        <button className="boton boton-primario" disabled={!a.titulo.trim()} onClick={async () => { await api.crearAccion({ ...a, meta_id: metaId, estado: 'activa' }); alCerrar() }}>Crear</button>
      </div>
    </Modal>
  )
}
