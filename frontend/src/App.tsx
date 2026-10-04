import { useCallback, useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api, type Estado } from './api'
import Orbe from './components/Orbe'
import Ajustes from './pages/Ajustes'
import Bienvenida from './pages/Bienvenida'
import Conversar from './pages/Conversar'
import Hoy from './pages/Hoy'
import Mapa from './pages/Mapa'
import Memoria from './pages/Memoria'
import Planes from './pages/Planes'

const SECCIONES = [
  { a: '/hoy', icono: '☀️', nombre: 'Hoy' },
  { a: '/conversar', icono: '💬', nombre: 'Conversar' },
  { a: '/mapa', icono: '🧭', nombre: 'Mi mapa' },
  { a: '/planes', icono: '🌱', nombre: 'Planes' },
  { a: '/memoria', icono: '🫶', nombre: 'Lo que HUM sabe' },
  { a: '/ajustes', icono: '⚙️', nombre: 'Ajustes' },
]

export default function App() {
  const [estado, setEstado] = useState<Estado | null>(null)
  const [error, setError] = useState('')
  const cargar = useCallback(() => api.estado().then(setEstado).catch((e) => setError(String(e.message ?? e))), [])
  useEffect(() => { void cargar() }, [cargar])

  if (error) return <div className="grid h-full place-items-center p-8 text-center text-tenue">No puedo hablar con HUM: {error}</div>
  if (!estado) return <div className="grid h-full place-items-center"><Orbe tam={72} estado="pensando" /></div>
  if (!estado.persona.onboarding) return <Bienvenida alTerminar={cargar} />

  return (
    <div className="flex h-full">
      <nav className="flex w-16 shrink-0 flex-col border-r border-borde bg-capa/60 py-4 md:w-56">
        <div className="mb-6 flex items-center gap-3 px-3 md:px-5">
          <Orbe tam={36} />
          <div className="hidden md:block">
            <p className="text-lg font-bold tracking-[0.25em] texto-degrade">HUM</p>
            <p className="text-[11px] leading-tight text-tenue">Inteligencia humanizada</p>
          </div>
        </div>
        {SECCIONES.map((s) => (
          <NavLink key={s.a} to={s.a} className={({ isActive }) =>
            `mx-2 mb-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] transition ${isActive ? 'bg-capa-2 text-white shadow-inner' : 'text-tenue hover:bg-capa-2/60 hover:text-tinta'}`}>
            <span className="text-lg">{s.icono}</span><span className="hidden md:inline">{s.nombre}</span>
          </NavLink>
        ))}
        <div className="mt-auto hidden px-5 text-[11px] leading-snug text-tenue md:block">
          {estado.error_proveedor ? <span className="text-amber-300">Sin modelo configurado</span>
            : <>Piensa con <b className="text-tinta">{estado.proveedor}</b>{estado.modelo && <> · {estado.modelo}</>}</>}
          <p className="mt-2 opacity-70">UEI · JFlowOS<br />IdeasDevOps & Disruptia AI</p>
        </div>
      </nav>
      <main className="min-w-0 flex-1 overflow-y-auto">
        {estado.error_proveedor && (
          <div className="border-b border-amber-500/30 bg-amber-950/40 px-6 py-2 text-sm text-amber-200">
            {estado.error_proveedor} <NavLink to="/ajustes" className="underline">Ir a Ajustes</NavLink>
          </div>
        )}
        <Routes>
          <Route path="/" element={<Navigate to="/hoy" replace />} />
          <Route path="/hoy" element={<Hoy />} />
          <Route path="/conversar" element={<Conversar />} />
          <Route path="/conversar/:id" element={<Conversar />} />
          <Route path="/mapa" element={<Mapa />} />
          <Route path="/planes" element={<Planes />} />
          <Route path="/memoria" element={<Memoria />} />
          <Route path="/ajustes" element={<Ajustes alCambiar={cargar} />} />
          <Route path="*" element={<Navigate to="/hoy" replace />} />
        </Routes>
      </main>
    </div>
  )
}
