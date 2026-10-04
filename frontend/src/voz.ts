// Voz en el navegador: grabar (con detección de silencio para el modo manos libres)
// y reproducir lo que HUM dice, frase por frase, a medida que llega.
import { api } from './api'

export type Grabacion = { detener: () => void; cancelar: () => void; nivel: () => number; resultado: Promise<Blob | null> }

/**
 * Empieza a grabar. Con `auto`, corta solo: después de oír voz, cuando hay ~1,3 s de silencio;
 * si nadie habla en `esperaMax` ms, termina sin audio (null).
 */
export async function grabar(auto: boolean, esperaMax = 12000): Promise<Grabacion> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  })
  const ctx = new AudioContext()
  const fuente = ctx.createMediaStreamSource(stream)
  const analizador = ctx.createAnalyser()
  analizador.fftSize = 1024
  fuente.connect(analizador)
  const muestras = new Float32Array(analizador.fftSize)

  const tipo = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : ''
  const rec = new MediaRecorder(stream, tipo ? { mimeType: tipo } : undefined)
  const partes: Blob[] = []
  rec.ondataavailable = (e) => { if (e.data.size) partes.push(e.data) }

  let huboVoz = false
  let cancelado = false
  let ultimoSonido = performance.now()
  const inicio = performance.now()
  let nivelActual = 0
  let ruidoBase = 0.01

  const nivel = () => {
    analizador.getFloatTimeDomainData(muestras)
    let s = 0
    for (const m of muestras) s += m * m
    return Math.sqrt(s / muestras.length)
  }

  const resultado = new Promise<Blob | null>((resolver) => {
    rec.onstop = () => {
      clearInterval(vigia)
      stream.getTracks().forEach((t) => t.stop())
      ctx.close()
      if (cancelado || (auto && !huboVoz) || !partes.length) return resolver(null)
      resolver(new Blob(partes, { type: rec.mimeType || 'audio/webm' }))
    }
  })

  // Calibra el ruido de fondo los primeros 300 ms y después vigila voz y silencio.
  const vigia = setInterval(() => {
    nivelActual = nivel()
    const t = performance.now()
    if (t - inicio < 300) { ruidoBase = Math.max(ruidoBase, nivelActual); return }
    const umbral = Math.max(0.02, ruidoBase * 2.5)
    if (nivelActual > umbral) { huboVoz = true; ultimoSonido = t }
    if (!auto || rec.state !== 'recording') return
    if (huboVoz && t - ultimoSonido > 1300) rec.stop()
    else if (!huboVoz && t - inicio > esperaMax) rec.stop()
  }, 60)

  rec.start(250)
  return {
    detener: () => { if (rec.state === 'recording') rec.stop() },
    cancelar: () => { cancelado = true; if (rec.state === 'recording') rec.stop() },
    nivel: () => nivelActual,
    resultado,
  }
}

/** Reproduce frases en orden; la síntesis de la siguiente se pide mientras suena la actual. */
export class Hablante {
  private cola: Promise<Blob | null>[] = []
  private sonando = false
  private audio: HTMLAudioElement | null = null
  private parado = false
  private pendienteFin = false
  alTerminar: () => void = () => {}
  alEmpezar: () => void = () => {}

  decir(frase: string) {
    if (!frase.trim() || this.parado) return
    this.cola.push(api.hablar(frase).catch(() => null))
    if (!this.sonando) void this.siguiente()
  }

  /** Avisa que no vienen más frases: cuando se vacíe la cola, dispara alTerminar. */
  cerrar() {
    this.pendienteFin = true
    if (!this.sonando && !this.cola.length) this.terminar()
  }

  detener() {
    this.parado = true
    this.cola = []
    this.audio?.pause()
    this.sonando = false
  }

  private terminar() {
    this.pendienteFin = false
    this.alTerminar()
  }

  private async siguiente(): Promise<void> {
    const prox = this.cola.shift()
    if (!prox) {
      this.sonando = false
      if (this.pendienteFin) this.terminar()
      return
    }
    this.sonando = true
    const blob = await prox
    if (this.parado) return
    if (!blob) return this.siguiente()
    const url = URL.createObjectURL(blob)
    this.audio = new Audio(url)
    this.alEmpezar()
    await new Promise<void>((ok) => {
      this.audio!.onended = () => ok()
      this.audio!.onerror = () => ok()
      this.audio!.play().catch(() => ok())
    })
    URL.revokeObjectURL(url)
    if (!this.parado) void this.siguiente()
  }
}

/** Corta el texto que va llegando en frases completas para empezar a hablar cuanto antes. */
export class Fraseador {
  private buf = ''
  private alFrase: (f: string) => void
  constructor(alFrase: (f: string) => void) { this.alFrase = alFrase }

  agregar(t: string) {
    this.buf += t
    for (;;) {
      const m = this.buf.match(/^([\s\S]{12,}?[.!?…:;])\s+/) ?? this.buf.match(/^([\s\S]+?)\n+/)
      if (!m) break
      this.alFrase(m[1].trim())
      this.buf = this.buf.slice(m[0].length)
    }
  }

  cerrar() {
    if (this.buf.trim()) this.alFrase(this.buf.trim())
    this.buf = ''
  }
}
