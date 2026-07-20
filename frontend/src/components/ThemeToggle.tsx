import { Moon, Sun } from 'lucide-react'
import type { Theme } from '../lib/theme'

export function ThemeToggle({ theme, onToggle }: { theme: Theme; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      aria-label="Toggle theme"
      title={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
      className="flex h-8 w-8 items-center justify-center rounded-lg border border-hair bg-surface text-ink-2 transition hover:bg-surface-2 hover:text-ink"
    >
      {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}
