// Primer encuentro: quién sos, tu contexto y cómo te percibís hoy en las 12 inteligencias.
import { useEffect, useState } from 'react'
import { api, type Mapa } from '../api'
import Orbe from '../components/Orbe'

export default function Bienvenida({ alTerminar }: { alTerminar: () => void }) {
  const [paso, setPaso] = useState(0)
  const [nombre, setNombre] = useState('')
  const [llamarte, setLlamarte] = useState('')
  const [contexto, setContexto] = useState('')
  const [mapa, setMapa] = useState<Mapa | null>(null)
  const [valores, setValores] = useState<Record<string, number>>({})
  const [guardando, setGuardando] = useState(false)

  useEffect(() => { api.mapa().then((m) => { setMapa(m); setValores(Object.fromEntries(m.inteligencias.map((i) => [i.id, 5]))) }) }, [])

  async function terminar() {
    setGuardando(true)
    await api.guardarPersona({ nombre, como_llamarte: llamarte || nombre, contexto, valores: '', onboarding: true })
    await api.autoevaluar(valores)
    alTerminar()
  }

  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col justify-center px-6 py-12">
      {paso === 0 && (
        <div className="text-center">
          <div className="mx-auto mb-8 w-fit"><Orbe tam={120} /></div>
          <h1 className="text-5xl font-bold tracking-[0.3em] texto-degrade">HUM</h1>
          <p className="mt-4 text-xl text-tinta">Hola. Soy HUM, la inteligencia humanizada de JFlowOS.</p>
          <p className="mx-auto mt-4 max-w-lg text-tenue">
            Te acompaño a mejorar un poco cada día en tu trabajo, tu vida, tus decisiones y lo que aprendés.
            Miro la vida completa, en tres dimensiones (<span className="text-cuerpo">Cuerpo</span>, <span className="text-mente">Mente</span> y <span className="text-espiritu">Espíritu</span>)
            y doce inteligencias. Lo que charlemos no se pierde: se convierte en planes que vos decidís.
          </p>
          <p className="mx-auto mt-4 max-w-lg text-sm text-tenue">
            Todo lo que sé de vos queda guardado en este equipo; lo podés ver y borrar cuando quieras.
            Soy una IA: no reemplazo a un profesional de la salud.
          </p>
          <button className="boton boton-primario mt-8 px-8 py-3 text-lg" onClick={() => setPaso(1)}>Empecemos</button>
        </div>
      )}

      {paso === 1 && (
        <div className="tarjeta p-8">
          <h2 className="text-2xl font-semibold">Contame de vos</h2>
          <label className="mt-6 block text-sm text-tenue">¿Cómo te llamás?</label>
          <input className="campo mt-1" value={nombre} onChange={(e) => setNombre(e.target.value)} autoFocus />
          <label className="mt-4 block text-sm text-tenue">¿Cómo querés que te diga? (opcional)</label>
          <input className="campo mt-1" value={llamarte} onChange={(e) => setLlamarte(e.target.value)} placeholder={nombre} />
          <label className="mt-4 block text-sm text-tenue">Tu momento de vida, en pocas palabras (trabajo, familia, lo que estás atravesando)</label>
          <textarea className="campo mt-1 h-28" value={contexto} onChange={(e) => setContexto(e.target.value)}
            placeholder="Ej.: trabajo en una empresa de logística, vivo con mi pareja, estoy empezando a entrenar y quiero ordenar mis finanzas." />
          <div className="mt-6 flex justify-between">
            <button className="boton boton-sutil" onClick={() => setPaso(0)}>Atrás</button>
            <button className="boton boton-primario" disabled={!nombre.trim()} onClick={() => setPaso(2)}>Seguir</button>
          </div>
        </div>
      )}

      {paso === 2 && mapa && (
        <div className="tarjeta p-8">
          <h2 className="text-2xl font-semibold">¿Cómo te percibís hoy?</h2>
          <p className="mt-2 text-sm text-tenue">
            Del 1 al 10, sin pensarlo demasiado. No es un examen ni una medición: es tu punto de partida,
            y lo vas a poder revisar cuando quieras para ver cómo cambia.
          </p>
          {mapa.dimensiones.map((d) => (
            <div key={d.id} className="mt-6">
              <p className="mb-2 text-sm font-semibold uppercase tracking-widest" style={{ color: d.color }}>{d.nombre}</p>
              {mapa.inteligencias.filter((i) => i.dimension_id === d.id).map((i) => (
                <div key={i.id} className="mb-3">
                  <div className="flex items-baseline justify-between">
                    <span className="font-medium">{i.icono} {i.nombre}</span>
                    <span className="text-lg font-semibold tabular-nums">{valores[i.id]}</span>
                  </div>
                  <p className="text-xs text-tenue">{i.definicion}</p>
                  <input type="range" min={1} max={10} value={valores[i.id] ?? 5} className="mt-1 w-full"
                    onChange={(e) => setValores({ ...valores, [i.id]: Number(e.target.value) })} />
                </div>
              ))}
            </div>
          ))}
          <div className="mt-6 flex justify-between">
            <button className="boton boton-sutil" onClick={() => setPaso(1)}>Atrás</button>
            <button className="boton boton-primario" disabled={guardando} onClick={terminar}>{guardando ? 'Guardando…' : 'Listo, conozcámonos'}</button>
          </div>
        </div>
      )}
    </div>
  )
}
