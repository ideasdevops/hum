// Cliente de la API local de HUM.

export type Dimension = { id: string; nombre: string; color: string; descripcion: string }
export type Practica = { nombre: string; como: string; evidencia: string }
export type Observacion = { inteligencia: string; texto: string; senal: number; fecha: string }
export type Inteligencia = {
  id: string; nombre: string; dimension_id: string; dimension: string; icono: string
  definicion: string; base: string; evidencia: string; senales: string[]; preguntas: string[]
  practicas: Practica[]; cuidado?: string
  autopercepcion: number | null; historial: { valor: number; fecha: string }[]
  lectura: string; lectura_fecha: string | null; observaciones: Observacion[]
  actividad_30d: { observaciones: number; avances: number; dificultades: number; acciones_hechas: number }
  metas: { id: number; titulo: string }[]
}
export type Mapa = { dimensiones: Dimension[]; inteligencias: Inteligencia[] }

export type Persona = { nombre: string; como_llamarte: string; contexto: string; valores: string; onboarding: number }
export type Conversacion = { id: number; titulo: string; modo: string; creada: string; actualizada: string; mensajes?: number }
export type Mensaje = { id: number; rol: 'user' | 'assistant'; contenido: string; por_voz: number; creado: string }
export type Meta = {
  id: number; titulo: string; porque: string; area: string; inteligencias: string[]; deseo: string; resultado: string
  obstaculo: string; plan: string; horizonte: string; estado: string; progreso: number; origen: string
}
export type Accion = {
  id: number; meta_id: number | null; titulo: string; inteligencia: string; frecuencia: string; si_entonces: string
  estado: string; origen: string; hecha_hoy?: number | null; hechas_7d?: number; hechas_total?: number; meta_titulo?: string
}
export type Linea = { nombre: string; numero: string; detalle: string }
export type Alerta = { clase: string; lineas: Linea[] }
export type Seguimiento = { id: number; texto: string; fecha: string; estado: string }
export type Recuerdo = { id: number; tipo: string; contenido: string; inteligencias: string; importancia: number; fecha: string }
export type Hoy = {
  saludo: string; onboarding: boolean
  registro: { animo: number | null; energia: number | null; sueno: number | null; nota: string } | null
  acciones: Accion[]; seguimientos: Seguimiento[]
  foco: { inteligencia: string; texto: string; nombre: string } | null
  propuestas: number; racha: number
}
export type Estado = {
  persona: { nombre: string; como_llamarte: string; onboarding: number }
  proveedor: string; modelo: string; error_proveedor: string
  disponibles: Record<string, boolean>
  voz: { oido: boolean; voz: boolean; voz_elegida: string; voces: string[] }
}

async function pedir<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const r = await fetch(ruta, {
    ...opciones,
    headers: opciones.body && typeof opciones.body === 'string' ? { 'Content-Type': 'application/json', ...opciones.headers } : opciones.headers,
  })
  if (!r.ok) {
    let detalle = `${r.status}`
    try { detalle = (await r.json()).detail ?? detalle } catch { /* sin cuerpo */ }
    throw new Error(typeof detalle === 'string' ? detalle : JSON.stringify(detalle))
  }
  return r.json() as Promise<T>
}

const json = (datos: unknown) => JSON.stringify(datos)

export const api = {
  // Con tope: si el servidor quedó colgado, la interfaz avisa en vez de girar para siempre
  estado: () => pedir<Estado>('/api/estado', { signal: AbortSignal.timeout(15000) }),
  persona: () => pedir<Persona>('/api/persona'),
  guardarPersona: (p: Partial<Omit<Persona, 'onboarding'>> & { onboarding?: boolean }) =>
    pedir<Persona>('/api/persona', { method: 'PUT', body: json(p), signal: AbortSignal.timeout(20000) }),
  mapa: () => pedir<Mapa>('/api/inteligencias'),
  autoevaluar: (valores: Record<string, number>) =>
    pedir('/api/autoevaluacion', { method: 'POST', body: json({ valores }), signal: AbortSignal.timeout(20000) }),

  conversaciones: () => pedir<Conversacion[]>('/api/conversaciones'),
  nuevaConversacion: (modo = 'texto') => pedir<{ id: number }>('/api/conversaciones', { method: 'POST', body: json({ modo }) }),
  conversacion: (id: number) => pedir<Conversacion & { mensajes: Mensaje[] }>(`/api/conversaciones/${id}`),
  borrarConversacion: (id: number) => pedir(`/api/conversaciones/${id}`, { method: 'DELETE' }),
  digerir: (id: number) => pedir<Record<string, number | boolean>>(`/api/conversaciones/${id}/digerir`, { method: 'POST' }),

  planes: () => pedir<{ metas: Meta[]; acciones: Accion[] }>('/api/planes'),
  crearMeta: (m: Partial<Meta>) => pedir<{ id: number }>('/api/metas', { method: 'POST', body: json(m) }),
  cambiarMeta: (id: number, c: Partial<Meta>) => pedir(`/api/metas/${id}`, { method: 'PATCH', body: json(c) }),
  crearAccion: (a: Partial<Accion>) => pedir<{ id: number }>('/api/acciones', { method: 'POST', body: json(a) }),
  cambiarAccion: (id: number, c: Partial<Accion>) => pedir(`/api/acciones/${id}`, { method: 'PATCH', body: json(c) }),
  marcarHoy: (id: number, hecha: boolean) => pedir(`/api/acciones/${id}/hoy`, { method: 'POST', body: json({ hecha }) }),

  hoy: () => pedir<Hoy>('/api/hoy'),
  registrar: (r: { animo?: number | null; energia?: number | null; sueno?: number | null; nota?: string }) =>
    pedir('/api/registro', { method: 'PUT', body: json(r) }),
  foco: (rehacer = false) => pedir<{ inteligencia: string; texto: string; nombre: string }>(`/api/foco?rehacer=${rehacer}`, { method: 'POST' }),
  seguimiento: (id: number, estado: string) => pedir(`/api/seguimientos/${id}`, { method: 'PATCH', body: json({ estado }) }),

  recuerdos: (q = '') => pedir<Recuerdo[]>(`/api/recuerdos?q=${encodeURIComponent(q)}`),
  cambiarRecuerdo: (id: number, c: Partial<Recuerdo>) => pedir(`/api/recuerdos/${id}`, { method: 'PATCH', body: json(c) }),
  olvidar: (id: number) => pedir(`/api/recuerdos/${id}`, { method: 'DELETE' }),
  olvidarTodo: () => pedir('/api/olvidar-todo', { method: 'POST', body: json({ confirmacion: 'OLVIDAR' }) }),

  ajustes: () => pedir<Record<string, unknown>>('/api/ajustes'),
  guardarAjustes: (a: Record<string, unknown>) => pedir<Record<string, unknown>>('/api/ajustes', { method: 'PUT', body: json(a) }),

  transcribir: async (audio: Blob) => {
    const r = await fetch('/api/voz/transcribir', { method: 'POST', body: audio, headers: { 'Content-Type': audio.type || 'audio/webm' } })
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? 'No pude escuchar el audio.')
    return (await r.json()).texto as string
  },
  hablar: async (texto: string) => {
    const r = await fetch('/api/voz/hablar', { method: 'POST', body: json({ texto }), headers: { 'Content-Type': 'application/json' } })
    if (!r.ok) throw new Error('No pude generar la voz.')
    return r.blob()
  },
}

export type EventoChat =
  | { tipo: 'texto'; t: string }
  | { tipo: 'alerta'; clase: string; lineas: Linea[] }
  | { tipo: 'fin'; id: number }
  | { tipo: 'error'; detalle: string }

/** Manda un mensaje y va entregando la respuesta de HUM a medida que llega (SSE sobre POST). */
export async function enviarMensaje(
  cid: number, texto: string, modo: 'texto' | 'voz', porVoz: boolean, alEvento: (e: EventoChat) => void,
) {
  const r = await fetch(`/api/conversaciones/${cid}/mensaje`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: json({ texto, modo, por_voz: porVoz }),
  })
  if (!r.ok || !r.body) {
    alEvento({ tipo: 'error', detalle: (await r.json().catch(() => ({}))).detail ?? `Error ${r.status}` })
    return
  }
  const lector = r.body.getReader()
  const dec = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await lector.read()
    if (done) break
    buffer += dec.decode(value, { stream: true })
    let i: number
    while ((i = buffer.indexOf('\n\n')) >= 0) {
      const bloque = buffer.slice(0, i)
      buffer = buffer.slice(i + 2)
      if (bloque.startsWith('data: ')) {
        try { alEvento(JSON.parse(bloque.slice(6))) } catch { /* bloque incompleto */ }
      }
    }
  }
}
