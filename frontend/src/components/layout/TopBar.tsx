import type { ReactNode } from 'react'
import { HealthPill } from '../HealthPill'
import { ThemeToggle } from '../ThemeToggle'
import type { Theme } from '../../lib/theme'

export function TopBar({
  title,
  subtitle,
  actions,
  theme,
  onToggleTheme,
}: {
  title: string
  subtitle: string
  actions?: ReactNode
  theme: Theme
  onToggleTheme: () => void
}) {
  return (
    <header className="flex items-center justify-between border-b border-hair bg-surface/80 px-6 py-3 backdrop-blur">
      <div>
        <h1 className="font-display text-lg font-semibold tracking-tight text-ink">{title}</h1>
        <p className="font-mono text-[11px] text-muted">{subtitle}</p>
      </div>
      <div className="flex items-center gap-3">
        {actions}
        <HealthPill />
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  )
}
