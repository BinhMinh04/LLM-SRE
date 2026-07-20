import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'
const KEY = 'iim-theme'

function getInitial(): Theme {
  const stored = localStorage.getItem(KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/** Theme state persisted to localStorage; applied via `data-theme` on <html>. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getInitial)
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(KEY, theme)
  }, [theme])
  return { theme, toggle: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')) }
}
