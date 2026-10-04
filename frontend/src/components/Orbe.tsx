// El orbe de HUM: tres círculos (Cuerpo, Mente, Espíritu) dentro de una esfera con el degradé de JFlowOS.
export type EstadoOrbe = 'reposo' | 'escuchando' | 'pensando' | 'hablando'

export default function Orbe({ tam = 40, estado = 'reposo', nivel = 0 }: { tam?: number; estado?: EstadoOrbe; nivel?: number }) {
  const escala = estado === 'escuchando' ? 1 + Math.min(nivel * 6, 0.35) : 1
  return (
    <div className={`orbe-${estado} relative shrink-0`} style={{ width: tam, height: tam }}>
      <div className="absolute inset-0 rounded-full blur-xl opacity-60 degrade" style={{ transform: `scale(${escala})`, transition: 'transform 80ms' }} />
      <svg viewBox="0 0 64 64" className="relative h-full w-full">
        <defs>
          <linearGradient id="hum-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#22d3ee" /><stop offset=".5" stopColor="#8b5cf6" /><stop offset="1" stopColor="#ec4899" />
          </linearGradient>
          <radialGradient id="hum-n" cx=".35" cy=".3" r=".8">
            <stop offset="0" stopColor="#fff" stopOpacity=".5" /><stop offset=".45" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="32" cy="32" r="28" fill="url(#hum-g)" />
        <circle cx="32" cy="32" r="28" fill="url(#hum-n)" />
        <g className="orbe-anillo" style={{ transformOrigin: '32px 32px' }} fill="none" stroke="#fff" strokeOpacity=".85" strokeWidth="2.4">
          <circle cx="32" cy="24" r="7" /><circle cx="25" cy="36" r="7" /><circle cx="39" cy="36" r="7" />
        </g>
      </svg>
    </div>
  )
}
