// Markdown mínimo y seguro (párrafos, listas, **negrita**, *itálica*) sin HTML crudo.
import type { ReactNode } from 'react'

function enLinea(texto: string): ReactNode[] {
  const partes = texto.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
  return partes.map((p, i) =>
    p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong>
      : p.startsWith('*') && p.endsWith('*') && p.length > 2 ? <em key={i}>{p.slice(1, -1)}</em>
        : p)
}

export default function Prosa({ texto }: { texto: string }) {
  const bloques = texto.trim().split(/\n{2,}/)
  return (
    <div className="prosa">
      {bloques.map((b, i) => {
        const lineas = b.split('\n')
        if (lineas.every((l) => /^\s*([-*•]|\d+[.)])\s+/.test(l))) {
          const ordenada = /^\s*\d/.test(lineas[0])
          const items = lineas.map((l, j) => <li key={j}>{enLinea(l.replace(/^\s*([-*•]|\d+[.)])\s+/, ''))}</li>)
          return ordenada ? <ol key={i}>{items}</ol> : <ul key={i}>{items}</ul>
        }
        return <p key={i}>{lineas.map((l, j) => <span key={j}>{j > 0 && <br />}{enLinea(l.replace(/^#+\s*/, ''))}</span>)}</p>
      })}
    </div>
  )
}
