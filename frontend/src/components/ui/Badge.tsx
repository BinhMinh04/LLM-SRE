import type { ReactNode } from 'react'

const tones: Record<string, string> = {
  neutral: 'bg-surface-2 text-ink-2',
  accent: 'text-accent',
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  const accentStyle =
    tone === 'accent' ? { background: 'color-mix(in srgb, var(--accent) 14%, transparent)' } : undefined
  return (
    <span
      className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone] ?? tones.neutral}`}
      style={accentStyle}
    >
      {children}
    </span>
  )
}
