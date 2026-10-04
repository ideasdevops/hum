// Lo que HUM sabe de vos: todo visible, editable y borrable. Tus datos son tuyos.
import { useEffect, useState } from 'react'
import { api, type Recuerdo } from '../api'

const TIPOS: Record<string, string> = {
  hecho: '📌 Hecho', experiencia: '🌄 Experiencia', emocion: '💗 Emoción', aprendizaje: '💡 Aprendizaje', vinculo: '🤝 Vínculo',
  valor: '🧭 Valor', preferencia: '⭐ Preferencia', salud: '🩺 Salud', trabajo: '💼 Trabajo', meta: '🎯 Deseo',
}

export default function Memoria() {
  const [recuerdos, setRecuerdos] = useState<Recuerdo[]>([])
  const [q, setQ] = useState('')
  const [editando, setEditando] = useState<number | null>(null)
  const [borrador, setBorrador] = useState('')

  const cargar = (consulta = q) => api.recuerdos(consulta).then(setRecuerdos)
  useEffect(() => { void cargar('') }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function olvidar(r: Recuerdo) { await api.olvidar(r.id); void cargar() }
  async function guardar(r: Recuerdo) { await api.cambiarRecuerdo(r.id, { contenido: borrador }); setEditando(null); void cargar() }
  async function olvidarTodo() {
    const t = prompt('Esto borra TODO lo que HUM sabe: recuerdos, conversaciones, planes y tu mapa. Escribí OLVIDAR para confirmar.')
    if (t?.trim().toUpperCase() !== 'OLVIDAR') return
    await api.olvidarTodo(); location.href = '/'
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="text-3xl font-semibold">Lo que HUM sabe de vos</h1>
      <p className="mt-1 text-tenue">Esto es lo que HUM recuerda de tus charlas para acompañarte mejor. Vive solo en este equipo. Podés corregirlo o borrarlo cuando quieras.</p>
      <div className="mt-5 flex gap-2">
        <input className="campo" placeholder="Buscar…" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && cargar()} />
        <button className="boton boton-sutil" onClick={() => cargar()}>Buscar</button>
      </div>
      {!recuerdos.length && <p className="mt-8 text-center text-tenue">{q ? 'No encontré nada.' : 'Todavía no hay recuerdos. Aparecen después de charlar con HUM.'}</p>}
      <ul className="mt-5 space-y-2">
        {recuerdos.map((r) => (
          <li key={r.id} className="tarjeta flex items-start gap-3 p-3">
            <span className="w-28 shrink-0 text-xs text-tenue">{TIPOS[r.tipo] ?? r.tipo}<br />{new Date(r.fecha).toLocaleDateString('es-AR')}</span>
            <div className="min-w-0 flex-1">
              {editando === r.id ? (
                <div className="flex gap-2"><input className="campo" value={borrador} onChange={(e) => setBorrador(e.target.value)} autoFocus />
                  <button className="boton boton-primario" onClick={() => guardar(r)}>Guardar</button></div>
              ) : <p>{r.contenido}</p>}
              <p className="mt-1 text-xs text-tenue">{'●'.repeat(r.importancia)}{'○'.repeat(5 - r.importancia)} importancia</p>
            </div>
            <div className="flex shrink-0 gap-2 text-sm">
              <button className="text-tenue hover:text-tinta" onClick={() => { setEditando(r.id); setBorrador(r.contenido) }}>Editar</button>
              <button className="text-tenue hover:text-rose-300" onClick={() => olvidar(r)}>Olvidar</button>
            </div>
          </li>
        ))}
      </ul>
      <div className="tarjeta mt-10 p-5">
        <h2 className="font-semibold">Tus datos</h2>
        <p className="mt-1 text-sm text-tenue">Descargá todo en un archivo, o pedile a HUM que olvide todo y empiece de cero.</p>
        <div className="mt-3 flex gap-2">
          <a className="boton boton-sutil" href="/api/exportar">⬇ Exportar todo</a>
          <button className="boton border border-rose-500/40 text-rose-200 hover:bg-rose-500/10" onClick={olvidarTodo}>Olvidar todo</button>
        </div>
      </div>
    </div>
  )
}
