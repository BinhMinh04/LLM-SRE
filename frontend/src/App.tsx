import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useTheme } from './lib/theme'
import { VIEW_META, type View } from './lib/nav'
import { Sidebar } from './components/layout/Sidebar'
import { TopBar } from './components/layout/TopBar'
import { Button } from './components/ui/Button'
import { Overview } from './pages/Overview'
import { Incidents } from './pages/Incidents'
import { KnowledgeBase } from './pages/KnowledgeBase'
import { NewIncidentModal } from './features/incidents/NewIncidentModal'
import { NewDocumentModal } from './features/documents/NewDocumentModal'

export default function App() {
  const { theme, toggle } = useTheme()
  const [view, setView] = useState<View>('overview')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [dataVersion, setDataVersion] = useState(0)
  const [showIncident, setShowIncident] = useState(false)
  const [showDoc, setShowDoc] = useState(false)

  const openIncident = (id: string) => {
    setSelectedId(id)
    setView('incidents')
  }

  const meta = VIEW_META[view]
  const actions =
    view === 'knowledge' ? (
      <Button onClick={() => setShowDoc(true)}>
        <Plus size={15} /> New document
      </Button>
    ) : (
      <Button onClick={() => setShowIncident(true)}>
        <Plus size={15} /> New incident
      </Button>
    )

  return (
    <div className="flex h-full">
      <Sidebar view={view} onNavigate={setView} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          title={meta.title}
          subtitle={meta.subtitle}
          actions={actions}
          theme={theme}
          onToggleTheme={toggle}
        />
        <main className="flex-1 overflow-hidden bg-plane">
          {view === 'overview' && <Overview refreshKey={dataVersion} onOpenIncident={openIncident} />}
          {view === 'incidents' && (
            <Incidents selectedId={selectedId} onSelect={setSelectedId} refreshKey={dataVersion} />
          )}
          {view === 'knowledge' && <KnowledgeBase refreshKey={dataVersion} />}
        </main>
      </div>

      <NewIncidentModal
        open={showIncident}
        onClose={() => setShowIncident(false)}
        onCreated={(id) => {
          setSelectedId(id)
          setView('incidents')
          setDataVersion((v) => v + 1)
        }}
      />
      <NewDocumentModal
        open={showDoc}
        onClose={() => setShowDoc(false)}
        onCreated={() => setDataVersion((v) => v + 1)}
      />
    </div>
  )
}
