import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

/** An empty screen framed as an invitation to act, not a dead end. */
export function EmptyState({
  icon: Icon,
  title,
  hint,
  action,
  className = '',
}: {
  icon: LucideIcon
  title: string
  hint?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl border border-dashed border-hair px-6 py-14 text-center ${className}`}
    >
      <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2 text-muted">
        <Icon size={26} strokeWidth={1.75} />
      </span>
      <h3 className="font-display text-base font-bold text-ink">{title}</h3>
      {hint && <p className="mt-1.5 max-w-sm text-sm text-ink-2">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
