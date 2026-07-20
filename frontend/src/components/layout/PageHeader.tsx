import type { ReactNode } from 'react'

/** The per-page title band: big title + subtitle on the left, primary action on the right. */
export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 px-4 pb-4 pt-6 md:px-8">
      <div>
        <h1 className="font-display text-2xl font-extrabold tracking-tight text-ink">{title}</h1>
        <p className="mt-1 text-sm text-ink-2">{subtitle}</p>
      </div>
      {action}
    </div>
  )
}
