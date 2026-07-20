import type { ReactNode } from 'react'

export function Card({
  children,
  className = '',
  interactive = false,
}: {
  children: ReactNode
  className?: string
  interactive?: boolean
}) {
  return (
    <div
      className={`rounded-2xl border border-hair bg-surface shadow-card ${
        interactive ? 'transition duration-300 hover:-translate-y-0.5 hover:shadow-card-hover' : ''
      } ${className}`}
    >
      {children}
    </div>
  )
}

/** Card header row: a title (with optional icon) and an optional action slot. */
export function CardHeader({
  title,
  action,
  className = '',
}: {
  title: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={`flex items-center justify-between gap-3 ${className}`}>
      <h3 className="font-display text-base font-bold tracking-tight text-ink">{title}</h3>
      {action}
    </div>
  )
}
