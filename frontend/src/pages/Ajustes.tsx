// Ajustes: con qué piensa HUM, su voz y tu perfil.
import { useEffect, useState } from 'react'
import { api, type Persona } from '../api'

type A = {
  proveedor: string; modelo: string; anthropic_key: boolean; voz: string; voz_velocidad: number; whisper_modelo: string
  voces: string[]; ollama_modelos: string[]; disponibles: Record<string, boolean>
}
const PROVEEDORES = [
  ['auto', 'Automático', 'El mejor disponible: API de Anthropic, Claude Code o Ollama.'],
  ['anthropic', 'API de Anthropic', 'Claude Opus 5.5 con tu clave. La mejor latencia para hablar por voz.'],
  ['claude-code', 'Claude Code', 'Usa la cuenta de Claude Code de este equipo (la de Ideas Box). Sin clave extra.'],
  ['ollama', 'Ollama (local)', 'Un modelo en tu equipo: nada sale de acá. La calidad depende del modelo.'],
]

export default function Ajustes({ alCambiar }: { alCambiar: () => void }) {
  const [a, setA] = useState<A | null>(null)
  const [p, setP] = useState<Persona | null>(null)
  const [clave, setClave] = useState('')
  const [msj, setMsj] = useState('')

  useEffect(() => { api.ajustes().then((x) => setA(x as unknown as A)); api.persona().then(setP) }, [])
  if (!a || !p) return null

  async function guardar(cambios: Record<string, unknown>) {
    try { setA((await api.guardarAjustes(cambios)) as unknown as A); setMsj('Guardado.'); alCambiar() } catch (e) { setMsj((e as Error).message) }
  }
  async function probarVoz() {
    setMsj('Generando…')
    try { new Audio(URL.createObjectURL(await api.hablar('Hola, soy HUM. Así suena mi voz.'))).play(); setMsj('') } catch (e) { setMsj((e as Error).message) }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
      <h1 className="text-3xl font-semibold">Ajustes</h1>
      {msj && <p className="text-sm text-tenue">{msj}</p>}

      <section className="tarjeta p-5">
        <h2 className="font-semibold">Con qué piensa HUM</h2>
        <div className="mt-3 space-y-2">
          {PROVEEDORES.map(([id, nombre, ayuda]) => (
            <label key={id} className={`flex cursor-pointer gap-3 rounded-xl border p-3 ${a.proveedor === id ? 'border-mente bg-mente/10' : 'border-borde'}`}>
              <input type="radio" checked={a.proveedor === id} onChange={() => guardar({ proveedor: id, modelo: '' })} className="mt-1" />
              <div><p>{nombre} {id !== 'auto' && <span className={`ml-1 text-xs ${a.disponibles[id] ? 'text-emerald-300' : 'text-tenue'}`}>{a.disponibles[id] ? '● disponible' : '○ no disponible'}</span>}</p>
                <p className="text-sm text-tenue">{ayuda}</p></div>
            </label>
          ))}
        </div>
        <label className="mt-4 block text-sm"><span className="text-tenue">Clave de Anthropic {a.anthropic_key && '(ya hay una cargada)'}</span>
          <div className="mt-1 flex gap-2"><input type="password" className="campo" placeholder="sk-ant-…" value={clave} onChange={(e) => setClave(e.target.value)} />
            <button className="boton boton-sutil" onClick={() => { void guardar({ anthropic_key: clave }); setClave('') }}>Guardar</button></div>
          <span className="text-xs text-tenue">Se guarda en ~/.config/hum/hum.env, solo legible por tu usuario.</span>
        </label>
        {a.proveedor === 'ollama' && (
          <label className="mt-4 block text-sm"><span className="text-tenue">Modelo de Ollama</span>
            <select className="campo mt-1" value={a.modelo} onChange={(e) => guardar({ modelo: e.target.value })}>
              <option value="">El primero disponible</option>
              {a.ollama_modelos.map((m) => <option key={m}>{m}</option>)}
            </select></label>
        )}
        {(a.proveedor === 'claude-code' || a.proveedor === 'anthropic') && (
          <label className="mt-4 block text-sm"><span className="text-tenue">Modelo (vacío = el recomendado)</span>
            <input className="campo mt-1" defaultValue={a.modelo} placeholder={a.proveedor === 'anthropic' ? 'claude-opus-5-5' : 'el de tu cuenta'} onBlur={(e) => guardar({ modelo: e.target.value })} /></label>
        )}
      </section>

      <section className="tarjeta p-5">
        <h2 className="font-semibold">Voz</h2>
        <p className="text-sm text-tenue">La voz y el oído de HUM funcionan en este equipo: tu voz no se manda a ningún servicio para transcribirla.</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm"><span className="text-tenue">Voz de HUM</span>
            <select className="campo mt-1" value={a.voz} onChange={(e) => guardar({ voz: e.target.value })}>
              {a.voces.map((v) => <option key={v}>{v}</option>)}
            </select></label>
          <label className="block text-sm"><span className="text-tenue">Velocidad ({a.voz_velocidad.toFixed(2)})</span>
            <input type="range" min={0.7} max={1.4} step={0.05} defaultValue={a.voz_velocidad} className="mt-3 w-full" onMouseUp={(e) => guardar({ voz_velocidad: Number((e.target as HTMLInputElement).value) })} /></label>
          <label className="block text-sm"><span className="text-tenue">Oído (Whisper)</span>
            <select className="campo mt-1" value={a.whisper_modelo} onChange={(e) => guardar({ whisper_modelo: e.target.value })}>
              {[['tiny', 'tiny: el más liviano'], ['base', 'base: rápido'], ['small', 'small: recomendado'], ['medium', 'medium: más preciso, más lento']].map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </select></label>
          <div className="flex items-end"><button className="boton boton-sutil w-full" onClick={probarVoz}>▶ Probar la voz</button></div>
        </div>
      </section>

      <section className="tarjeta p-5">
        <h2 className="font-semibold">Tu perfil</h2>
        {(['nombre', 'como_llamarte'] as const).map((k) => (
          <label key={k} className="mt-3 block text-sm"><span className="text-tenue">{k === 'nombre' ? 'Nombre' : 'Cómo querés que te diga'}</span>
            <input className="campo mt-1" value={p[k]} onChange={(e) => setP({ ...p, [k]: e.target.value })} /></label>
        ))}
        <label className="mt-3 block text-sm"><span className="text-tenue">Tu contexto (HUM lo va completando con lo que charlan)</span>
          <textarea className="campo mt-1 h-28" value={p.contexto} onChange={(e) => setP({ ...p, contexto: e.target.value })} /></label>
        <label className="mt-3 block text-sm"><span className="text-tenue">Lo que te importa</span>
          <textarea className="campo mt-1 h-20" value={p.valores} onChange={(e) => setP({ ...p, valores: e.target.value })} /></label>
        <button className="boton boton-primario mt-3" onClick={async () => { await api.guardarPersona({ nombre: p.nombre, como_llamarte: p.como_llamarte, contexto: p.contexto, valores: p.valores }); setMsj('Perfil guardado.'); alCambiar() }}>Guardar perfil</button>
      </section>

      <p className="text-center text-xs text-tenue">HUM 0.1 · la IA de UEI (Universo Estratégico Inteligente) · JFlowOS · IdeasDevOps & Disruptia AI<br />
        HUM es una IA de acompañamiento: no reemplaza a profesionales de la salud, legales ni financieros.</p>
    </div>
  )
}
