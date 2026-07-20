import type { ReactNode } from 'react'

export type BadgeTone = 'neutral' | 'accent' | 'info' | 'success' | 'warning' | 'danger' | 'purple'

const HUE: Record<Exclude<BadgeTone, 'neutral'>, string> = {
  accent: 'var(--accent)',
  info: 'var(--info)',
  success: 'var(--sev-low)',
  warning: 'var(--sev-medium)',
  danger: 'var(--sev-critical)',
  purple: 'var(--purple)',
}

/**
 * A soft pill: tinted background + saturated text in one hue. `dot` adds a
 * leading status dot. Neutral uses surface tokens; every other tone derives
 * its tint from a single CSS variable so light/dark stay in sync.
 */
export function Badge({
  children,
  tone = 'neutral',
  dot = false,
  className = '',
}: {
  children: ReactNode
  tone?: BadgeTone
  dot?: boolean
  className?: string
}) {
  const base =
    'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap'

  if (tone === 'neutral') {
    return (
      <span className={`${base} bg-surface-2 text-ink-2 ${className}`}>
        {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-60" />}
        {children}
      </span>
    )
  }

  const hue = HUE[tone]
  return (
    <span
      className={`${base} ${className}`}
      style={{ background: `color-mix(in srgb, ${hue} 15%, transparent)`, color: hue }}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full" style={{ background: hue }} />}
      {children}
    </span>
  )
}
