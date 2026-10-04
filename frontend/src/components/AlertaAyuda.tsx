import type { Alerta } from '../api'

const TITULOS: Record<string, string> = {
  vida: 'No estás solo. Hay personas listas para escucharte ahora',
  violencia: 'Tu seguridad es lo primero',
  consumo: 'Pedir ayuda es un paso enorme',
}

export default function AlertaAyuda({ alerta, alCerrar }: { alerta: Alerta; alCerrar?: () => void }) {
  return (
    <div role="alert" className="rounded-2xl border border-rose-400/40 bg-rose-950/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="font-semibold text-rose-100">💗 {TITULOS[alerta.clase] ?? 'Líneas de ayuda'}</p>
        {alCerrar && <button onClick={alCerrar} className="text-sm text-rose-200/70 hover:text-white" aria-label="Cerrar">✕</button>}
      </div>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {alerta.lineas.map((l) => (
          <li key={l.nombre + l.numero} className="rounded-xl bg-black/25 px-3 py-2">
            <a href={`tel:${l.numero.replace(/\D/g, '')}`} className="text-xl font-bold tracking-wide text-white">{l.numero}</a>
            <p className="text-sm text-rose-100">{l.nombre}</p>
            <p className="text-xs text-rose-200/70">{l.detalle}</p>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-rose-200/70">HUM es una IA de acompañamiento: no reemplaza la ayuda profesional ni los servicios de emergencia.</p>
    </div>
  )
}
