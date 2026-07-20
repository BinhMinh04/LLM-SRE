import type { LucideIcon } from 'lucide-react'
import { Badge, type BadgeTone } from './Badge'

/**
 * A dashboard stat card: a tinted icon chip and an optional status pill on the
 * top row, then the hero number and its label. No plot, so no hover data layer
 * (dataviz rule) — just a gentle lift on hover.
 */
export function StatTile({
  label,
  value,
  icon: Icon,
  accent = 'var(--accent)',
  badge,
}: {
  label: string
  value: string | number
  icon: LucideIcon
  accent?: string
  badge?: { text: string; tone?: BadgeTone }
}) {
  return (
    <div className="group rounded-2xl border border-hair bg-surface p-5 shadow-card transition duration-300 hover:-translate-y-0.5 hover:shadow-card-hover">
      <div className="flex items-start justify-between">
        <span
          className="flex h-11 w-11 items-center justify-center rounded-xl transition-transform duration-300 group-hover:scale-105"
          style={{ background: `color-mix(in srgb, ${accent} 15%, transparent)`, color: accent }}
        >
          <Icon size={20} strokeWidth={2.2} />
        </span>
        {badge && <Badge tone={badge.tone ?? 'neutral'}>{badge.text}</Badge>}
      </div>
      <div className="mt-4 font-display text-[2.5rem] font-extrabold leading-none tracking-tight tabular-nums text-ink">
        {value}
      </div>
      <div className="mt-1.5 text-sm font-medium text-ink-2">{label}</div>
    </div>
  )
}
