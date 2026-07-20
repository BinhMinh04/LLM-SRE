import type { ReactNode } from 'react'

/** Console-style section label: monospace, uppercase, with a `//` marker. */
export function Eyebrow({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`font-mono text-[11px] font-medium uppercase tracking-wider text-muted ${className}`}>
      <span className="text-accent">// </span>
      {children}
    </div>
  )
}
