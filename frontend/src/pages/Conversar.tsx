// Conversar con HUM: por texto, dictando, o en modo voz (manos libres).
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, enviarMensaje, type Alerta, type Conversacion, type Mensaje } from '../api'
import AlertaAyuda from '../components/AlertaAyuda'
import Orbe, { type EstadoOrbe } from '../components/Orbe'
import Prosa from '../components/Prosa'
import { Fraseador, grabar, Hablante, type Grabacion } from '../voz'

const SUGERENCIAS = [
  'Estoy con poca energía últimamente, ¿me ayudás a ver por qué?',
  'Tengo que tomar una decisión importante y no sé por dónde empezar.',
  'Quiero ordenar mis finanzas este mes.',
  'Hoy necesito descargarme un rato.',
]

type MensajeVista = Pick<Mensaje, 'rol' | 'contenido'> & { id: number | string; por_voz?: number }

export default function Conversar() {
  const { id } = useParams()
  const navegar = useNavigate()
  const cid = id ? Number(id) : null
  const [lista, setLista] = useState<Conversacion[]>([])
  const [mensajes, setMensajes] = useState<MensajeVista[]>([])
  const [texto, setTexto] = useState('')
  const [pensando, setPensando] = useState(false)
  const [alerta, setAlerta] = useState<Alerta | null>(null)
  const [aviso, setAviso] = useState('')
  const [dictando, setDictando] = useState<Grabacion | null>(null)
  const [modoVoz, setModoVoz] = useState(false)
  const fin = useRef<HTMLDivElement>(null)
  // cid en un ref: así `mandar` es estable y el modo voz no se reinicia al crear la conversación,
  // y la conversación recién creada no se recarga del servidor en medio de la respuesta.
  const cidRef = useRef<number | null>(cid)
  const creadaAhora = useRef<number | null>(null)

  const cargarLista = useCallback(() => api.conversaciones().then(setLista), [])
  useEffect(() => { void cargarLista() }, [cargarLista])
  useEffect(() => {
    cidRef.current = cid
    if (cid && cid === creadaAhora.current) return
    setAlerta(null)
    if (cid) api.conversacion(cid).then((c) => setMensajes(c.mensajes)).catch(() => navegar('/conversar'))
    else setMensajes([])
  }, [cid, navegar])
  useEffect(() => { fin.current?.scrollIntoView({ behavior: 'smooth' }) }, [mensajes])

  /** Manda un mensaje; devuelve la respuesta completa. `alTrozo` recibe el texto a medida que llega. */
  const mandar = useCallback(async (contenido: string, modo: 'texto' | 'voz', porVoz: boolean, alTrozo?: (t: string) => void) => {
    let destino = cidRef.current
    if (!destino) {
      destino = (await api.nuevaConversacion(modo)).id
      cidRef.current = destino
      creadaAhora.current = destino
      navegar(`/conversar/${destino}`, { replace: true })
    }
    const idRespuesta = `r${Date.now()}`
    setMensajes((m) => [...m, { id: `u${Date.now()}`, rol: 'user', contenido, por_voz: porVoz ? 1 : 0 },
      { id: idRespuesta, rol: 'assistant', contenido: '' }])
    setPensando(true)
    let respuesta = ''
    await enviarMensaje(destino, contenido, modo, porVoz, (e) => {
      if (e.tipo === 'texto') {
        respuesta += e.t
        alTrozo?.(e.t)
        setMensajes((m) => m.map((x) => (x.id === idRespuesta ? { ...x, contenido: respuesta } : x)))
      } else if (e.tipo === 'alerta') setAlerta({ clase: e.clase, lineas: e.lineas })
      else if (e.tipo === 'error') {
        setMensajes((m) => m.map((x) => (x.id === idRespuesta ? { ...x, contenido: `⚠️ ${e.detalle}` } : x)))
      }
    })
    setPensando(false)
    void cargarLista()
    return respuesta
  }, [navegar, cargarLista])

  async function enviarTexto() {
    const t = texto.trim()
    if (!t || pensando) return
    setTexto('')
    await mandar(t, 'texto', false)
  }

  async function alternarDictado() {
    if (dictando) {
      dictando.detener()
      const audio = await dictando.resultado
      setDictando(null)
      if (!audio) return
      setAviso('Transcribiendo…')
      try {
        const t = await api.transcribir(audio)
        setTexto((prev) => (prev ? prev + ' ' : '') + t)
      } catch (e) { setAviso(String((e as Error).message)) ; return }
      setAviso('')
    } else {
      try { setDictando(await grabar(false)) } catch { setAviso('No tengo acceso al micrófono.') }
    }
  }

  async function guardarAprendizajes() {
    if (!cid) return
    setAviso('HUM está guardando lo que aprendió de esta charla…')
    try {
      const r = await api.digerir(cid)
      if (r.nada) setAviso('No había nada nuevo para guardar.')
      else setAviso(`Guardé ${r.recuerdos} recuerdos, ${r.observaciones} observaciones, ${(r.metas as number) + (r.acciones as number)} propuestas para tus Planes y ${r.seguimientos} seguimientos.`)
    } catch (e) { setAviso(String((e as Error).message)) }
  }

  async function borrar(c: Conversacion) {
    if (!confirm(`¿Borrar «${c.titulo}»? Lo que HUM ya aprendió de ella se conserva en «Lo que HUM sabe».`)) return
    await api.borrarConversacion(c.id)
    if (c.id === cid) navegar('/conversar')
    void cargarLista()
  }

  return (
    <div className="flex h-full">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-borde lg:flex">
        <div className="p-3">
          <button className="boton boton-primario w-full" onClick={() => navegar('/conversar')}>＋ Nueva conversación</button>
        </div>
        <ul className="flex-1 overflow-y-auto px-2 pb-4">
          {lista.map((c) => (
            <li key={c.id} className={`group mb-1 flex items-center rounded-lg ${c.id === cid ? 'bg-capa-2' : 'hover:bg-capa-2/60'}`}>
              <button className="min-w-0 flex-1 px-3 py-2 text-left" onClick={() => navegar(`/conversar/${c.id}`)}>
                <p className="truncate text-sm">{c.modo === 'voz' ? '🎙️ ' : ''}{c.titulo}</p>
                <p className="text-[11px] text-tenue">{new Date(c.actualizada).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })}</p>
              </button>
              <button className="px-2 text-tenue opacity-0 hover:text-rose-300 group-hover:opacity-100" title="Borrar" onClick={() => borrar(c)}>✕</button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-borde px-6 py-3">
          <p className="truncate font-medium">{lista.find((c) => c.id === cid)?.titulo ?? 'Nueva conversación'}</p>
          <div className="flex gap-2">
            {cid && <button className="boton boton-sutil text-sm" onClick={guardarAprendizajes} title="Convertir esta charla en recuerdos y propuestas ahora">✨ Guardar aprendizajes</button>}
            <button className="boton boton-primario text-sm" onClick={() => setModoVoz(true)}>🎙️ Hablar con HUM</button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-10">
          {!mensajes.length && (
            <div className="mx-auto mt-10 max-w-xl text-center">
              <div className="mx-auto mb-6 w-fit"><Orbe tam={84} /></div>
              <p className="text-xl">¿De qué querés hablar hoy?</p>
              <p className="mt-2 text-tenue">Podés escribir, dictar o hablar conmigo en voz alta.</p>
              <div className="mt-6 grid gap-2 sm:grid-cols-2">
                {SUGERENCIAS.map((s) => (
                  <button key={s} className="tarjeta p-3 text-left text-sm text-tenue hover:border-mente hover:text-tinta" onClick={() => mandar(s, 'texto', false)}>{s}</button>
                ))}
              </div>
            </div>
          )}
          <div className="mx-auto max-w-3xl space-y-5">
            {mensajes.map((m) => (
              m.rol === 'user' ? (
                <div key={m.id} className="flex justify-end">
                  <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-capa-2 px-4 py-2.5">{m.por_voz ? '🎙️ ' : ''}{m.contenido}</div>
                </div>
              ) : (
                <div key={m.id} className="flex gap-3">
                  <Orbe tam={30} estado={pensando && !m.contenido ? 'pensando' : 'reposo'} />
                  <div className="max-w-[85%] pt-1 leading-relaxed">
                    {m.contenido ? <Prosa texto={m.contenido} /> : <span className="text-tenue">pensando…</span>}
                  </div>
                </div>
              )
            ))}
            <div ref={fin} />
          </div>
        </div>

        <footer className="border-t border-borde px-4 py-3 md:px-10">
          <div className="mx-auto max-w-3xl space-y-2">
            {alerta && <AlertaAyuda alerta={alerta} alCerrar={() => setAlerta(null)} />}
            {aviso && <p className="text-sm text-tenue">{aviso} <button className="ml-2 underline" onClick={() => setAviso('')}>ok</button></p>}
            <div className="flex items-end gap-2">
              <button onClick={alternarDictado} title={dictando ? 'Terminar de dictar' : 'Dictar'}
                className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl border ${dictando ? 'animate-pulse border-rose-400 bg-rose-500/20' : 'border-borde bg-capa-2 hover:border-mente'}`}>
                {dictando ? '⏹' : '🎤'}
              </button>
              <textarea className="campo max-h-48 min-h-11 resize-none" rows={1} value={texto} placeholder="Escribile a HUM…"
                onChange={(e) => setTexto(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void enviarTexto() } }} />
              <button className="boton boton-primario h-11 shrink-0" disabled={pensando || !texto.trim()} onClick={enviarTexto}>Enviar</button>
            </div>
          </div>
        </footer>
      </section>

      {modoVoz && <ModoVoz mandar={mandar} alSalir={() => setModoVoz(false)} alerta={alerta} />}
    </div>
  )
}

type Mandar = (c: string, modo: 'texto' | 'voz', porVoz: boolean, alTrozo?: (t: string) => void) => Promise<string>

/** Charla por voz manos libres: escucha → HUM piensa → HUM habla → vuelve a escuchar. */
function ModoVoz({ mandar, alSalir, alerta }: { mandar: Mandar; alSalir: () => void; alerta: Alerta | null }) {
  const [estado, setEstado] = useState<EstadoOrbe>('reposo')
  const [nivel, setNivel] = useState(0)
  const [dijiste, setDijiste] = useState('')
  const [dice, setDice] = useState('')
  const [error, setError] = useState('')
  const activo = useRef(true)
  const grabacion = useRef<Grabacion | null>(null)
  const hablante = useRef<Hablante | null>(null)

  const ciclo = useCallback(async () => {
    while (activo.current) {
      setEstado('escuchando'); setError('')
      let g: Grabacion
      try { g = await grabar(true, 20000) } catch { setError('No tengo acceso al micrófono.'); setEstado('reposo'); return }
      grabacion.current = g
      const medidor = setInterval(() => setNivel(g.nivel()), 80)
      const audio = await g.resultado
      clearInterval(medidor); setNivel(0)
      if (!activo.current) return
      if (!audio) { setEstado('reposo'); return } // nadie habló: queda en pausa hasta tocar el orbe
      setEstado('pensando')
      let t = ''
      try { t = await api.transcribir(audio) } catch (e) { setError((e as Error).message); continue }
      if (!t.trim()) continue
      setDijiste(t); setDice('')
      const h = new Hablante()
      hablante.current = h
      const terminado = new Promise<void>((ok) => { h.alTerminar = ok })
      h.alEmpezar = () => setEstado('hablando')
      const frases = new Fraseador((f) => h.decir(f))
      await mandar(t, 'voz', true, (trozo) => { setDice((d) => d + trozo); frases.agregar(trozo) })
      frases.cerrar(); h.cerrar()
      await terminado
    }
  }, [mandar])

  useEffect(() => {
    activo.current = true
    void ciclo()
    return () => { activo.current = false; grabacion.current?.cancelar(); hablante.current?.detener() }
  }, [ciclo])

  function tocarOrbe() {
    if (estado === 'hablando') { hablante.current?.detener(); hablante.current?.alTerminar() }
    else if (estado === 'escuchando') grabacion.current?.detener()
    else if (estado === 'reposo') void ciclo()
  }

  const etiqueta = { reposo: 'Tocá el orbe para hablar', escuchando: 'Te escucho…', pensando: 'Pensando…', hablando: 'Tocá para interrumpir' }[estado]

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-noche/95 px-6 backdrop-blur">
      <button onClick={() => { activo.current = false; alSalir() }} className="absolute right-6 top-6 boton boton-sutil">Terminar</button>
      <button onClick={tocarOrbe} className="rounded-full focus:outline-none" aria-label={etiqueta}>
        <Orbe tam={220} estado={estado} nivel={nivel} />
      </button>
      <p className="mt-8 text-lg text-tenue">{etiqueta}</p>
      {error && <p className="mt-2 text-amber-300">{error}</p>}
      <div className="mt-8 max-w-2xl space-y-3 text-center">
        {dijiste && <p className="text-tenue">«{dijiste}»</p>}
        {dice && <p className="text-xl leading-relaxed">{dice}</p>}
      </div>
      {alerta && <div className="mt-6 w-full max-w-2xl"><AlertaAyuda alerta={alerta} /></div>}
    </div>
  )
}
