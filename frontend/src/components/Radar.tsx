// Rueda de las 12 inteligencias: autopercepción actual (y la anterior, punteada, para ver la evolución).
// Los sectores y los puntos llevan el color de su dimensión; las etiquetas, tinta de texto.
import { useState } from 'react'
import type { Dimension, Inteligencia } from '../api'

type Props = { dimensiones: Dimension[]; inteligencias: Inteligencia[]; alElegir?: (id: string) => void; elegida?: string }

const TAM = 460
const C = TAM / 2
const R = 160

function punto(i: number, n: number, v: number) {
  const a = (Math.PI * 2 * i) / n - Math.PI / 2
  const r = (R * v) / 10
  return [C + r * Math.cos(a), C + r * Math.sin(a)] as const
}

function sector(i0: number, i1: number, n: number) {
  const a0 = (Math.PI * 2 * (i0 - 0.5)) / n - Math.PI / 2
  const a1 = (Math.PI * 2 * (i1 + 0.5)) / n - Math.PI / 2
  const p0 = [C + R * Math.cos(a0), C + R * Math.sin(a0)]
  const p1 = [C + R * Math.cos(a1), C + R * Math.sin(a1)]
  return `M${C},${C} L${p0[0]},${p0[1]} A${R},${R} 0 0 1 ${p1[0]},${p1[1]} Z`
}

export default function Radar({ dimensiones, inteligencias, alElegir, elegida }: Props) {
  const [hover, setHover] = useState<string | null>(null)
  const n = inteligencias.length
  const color = Object.fromEntries(dimensiones.map((d) => [d.id, d.color]))
  const actual = inteligencias.map((x) => x.autopercepcion ?? 0)
  const anterior = inteligencias.map((x) => (x.historial.length > 1 ? x.historial[x.historial.length - 2].valor : null))
  const hayAnterior = anterior.some((v) => v !== null)
  const poligono = (vals: (number | null)[]) => vals.map((v, i) => punto(i, n, v ?? 0).join(',')).join(' ')
  const sobre = hover ? inteligencias.find((x) => x.id === hover) : null

  return (
    <figure className="relative mx-auto w-full max-w-[560px]">
      <svg viewBox={`-50 -6 ${TAM + 100} ${TAM + 12}`} className="w-full" role="img"
        aria-label={'Autopercepción: ' + inteligencias.map((x) => `${x.nombre} ${x.autopercepcion ?? 'sin dato'}`).join(', ')}>
        {dimensiones.map((d) => {
          const idx = inteligencias.map((x, i) => (x.dimension_id === d.id ? i : -1)).filter((i) => i >= 0)
          return <path key={d.id} d={sector(idx[0], idx[idx.length - 1], n)} fill={d.color} opacity={0.07} />
        })}
        {[2, 4, 6, 8, 10].map((v) => (
          <polygon key={v} points={poligono(Array(n).fill(v))} fill="none" stroke="#2a2a3d" strokeWidth={1} />
        ))}
        {inteligencias.map((_, i) => {
          const [x, y] = punto(i, n, 10)
          return <line key={i} x1={C} y1={C} x2={x} y2={y} stroke="#2a2a3d" strokeWidth={1} />
        })}
        {hayAnterior && (
          <polygon points={poligono(anterior)} fill="none" stroke="#9a9ab3" strokeWidth={2} strokeDasharray="5 5" />
        )}
        <polygon points={poligono(actual)} fill="#ececf4" fillOpacity={0.08} stroke="#ececf4" strokeWidth={2} strokeLinejoin="round" />
        {inteligencias.map((x, i) => {
          const [px, py] = punto(i, n, x.autopercepcion ?? 0)
          const [lx, ly] = punto(i, n, 12.3)
          const activa = elegida === x.id || hover === x.id
          return (
            <g key={x.id} className="cursor-pointer" onMouseEnter={() => setHover(x.id)} onMouseLeave={() => setHover(null)}
              onClick={() => alElegir?.(x.id)}>
              <circle cx={lx} cy={ly} r={30} fill="transparent" />
              <circle cx={px} cy={py} r={14} fill="transparent" />
              {x.autopercepcion !== null && (
                <circle cx={px} cy={py} r={activa ? 7 : 5} fill={color[x.dimension_id]} stroke="#13131f" strokeWidth={2} />
              )}
              <text x={lx} y={ly - 4} textAnchor="middle" fontSize={13} fontWeight={activa ? 700 : 500} fill={activa ? '#ffffff' : '#ececf4'}>
                {x.icono} {x.nombre}
              </text>
              <text x={lx} y={ly + 12} textAnchor="middle" fontSize={11} fill="#9a9ab3">
                {x.autopercepcion !== null ? `${x.autopercepcion}/10` : '—'}
              </text>
            </g>
          )
        })}
      </svg>
      {sobre && (
        <div className="pointer-events-none absolute left-1/2 top-1/2 w-56 -translate-x-1/2 -translate-y-1/2 rounded-xl border border-borde bg-capa/95 p-3 text-sm shadow-xl">
          <p className="font-semibold">{sobre.icono} {sobre.nombre} · <span className="text-tenue">{sobre.dimension}</span></p>
          <p className="mt-1 text-tenue">Hoy: <b className="text-tinta">{sobre.autopercepcion ?? '—'}</b>/10
            {sobre.historial.length > 1 && <> · antes {sobre.historial[sobre.historial.length - 2].valor}</>}</p>
          <p className="text-tenue">Últimos 30 días: {sobre.actividad_30d.acciones_hechas} acciones, {sobre.actividad_30d.observaciones} señales</p>
        </div>
      )}
      <figcaption className="mt-2 flex flex-wrap items-center justify-center gap-x-5 gap-y-1 text-sm text-tenue">
        {dimensiones.map((d) => (
          <span key={d.id} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: d.color }} />{d.nombre}</span>
        ))}
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 bg-tinta" />Hoy</span>
        {hayAnterior && <span className="flex items-center gap-1.5"><span className="w-5 border-t-2 border-dashed border-tenue" />Evaluación anterior</span>}
      </figcaption>
    </figure>
  )
}
