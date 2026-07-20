import type { ReactNode } from 'react'

/** A small, tracked, uppercase section label. */
export function Eyebrow({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`text-[11px] font-bold uppercase tracking-[0.14em] text-muted ${className}`}
    >
      {children}
    </div>
  )
}
