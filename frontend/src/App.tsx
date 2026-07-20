import { useState } from 'react'
import { useTheme } from './lib/theme'
import { VIEW_META, type View } from './lib/nav'
import { Sidebar } from './components/layout/Sidebar'
import { TopBar } from './components/layout/TopBar'

// Foundation shell: sidebar navigation + top bar + theme. Feature pages land in later PRs;
// each destination shows a placeholder for now.
export default function App() {
  const { theme, toggle } = useTheme()
  const [view, setView] = useState<View>('overview')
  const meta = VIEW_META[view]

  return (
    <div className="flex h-full">
      <Sidebar view={view} onNavigate={setView} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={meta.title} subtitle={meta.subtitle} theme={theme} onToggleTheme={toggle} />
        <main className="flex-1 overflow-hidden bg-plane">
          <div className="animate-in flex h-full items-center justify-center p-6 text-center font-mono text-xs uppercase tracking-wider text-muted">
            {meta.title} · coming online
          </div>
        </main>
      </div>
    </div>
  )
}
