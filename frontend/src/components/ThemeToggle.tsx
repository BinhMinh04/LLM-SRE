import { Moon, Sun } from 'lucide-react'
import type { Theme } from '../lib/theme'

export function ThemeToggle({ theme, onToggle }: { theme: Theme; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      aria-label="Toggle theme"
      title={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
      className="flex h-9 w-9 items-center justify-center rounded-xl border border-hair bg-surface text-ink-2 transition hover:bg-surface-2 hover:text-ink"
    >
      {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  )
}
