import type { ReactNode } from 'react'
import { X } from 'lucide-react'

export function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl border border-hair bg-surface shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-hair px-5 py-3.5">
          <h2 className="font-display text-base font-semibold tracking-tight text-ink">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted transition hover:bg-surface-2 hover:text-ink"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
        <div className="space-y-3 p-5">{children}</div>
      </div>
    </div>
  )
}
