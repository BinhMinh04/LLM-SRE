import type { LucideIcon } from 'lucide-react'

/**
 * A bare stat tile (hero number) — no plot, so no hover layer (dataviz rule).
 * The value uses proportional figures; `accent` optionally tints the icon chip.
 */
export function StatTile({
  label,
  value,
  sublabel,
  icon: Icon,
  accent = 'var(--accent)',
}: {
  label: string
  value: string | number
  sublabel?: string
  icon: LucideIcon
  accent?: string
}) {
  return (
    <div className="rounded-xl border border-hair bg-surface p-4 shadow-card">
      <div className="flex items-start justify-between">
        <span className="font-mono text-[11px] font-medium uppercase tracking-wider text-muted">
          {label}
        </span>
        <span
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ background: `color-mix(in srgb, ${accent} 14%, transparent)`, color: accent }}
        >
          <Icon size={16} />
        </span>
      </div>
      <div className="mt-2 font-display text-4xl font-semibold tabular-nums text-ink">{value}</div>
      {sublabel && <div className="mt-0.5 text-xs text-ink-2">{sublabel}</div>}
    </div>
  )
}
