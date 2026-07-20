import { ShieldAlert } from 'lucide-react'
import { NAV, NAV_SOON, type View } from '../../lib/nav'

export function Sidebar({ view, onNavigate }: { view: View; onNavigate: (v: View) => void }) {
  return (
    <aside className="flex w-60 flex-col border-r border-hair bg-surface">
      <div className="bg-grid flex items-center gap-2.5 border-b border-hair px-4 py-4">
        <span
          className="flex h-9 w-9 items-center justify-center rounded-xl text-white shadow-card"
          style={{ background: 'linear-gradient(135deg, var(--accent), #7c5cff)' }}
        >
          <ShieldAlert size={18} />
        </span>
        <div className="leading-tight">
          <div className="font-display text-lg font-bold tracking-tight text-ink">IIM</div>
          <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
            Triage&nbsp;Console
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-2 py-2">
        {NAV.map((item) => {
          const Icon = item.icon
          const active = view === item.view
          return (
            <button
              key={item.view}
              onClick={() => onNavigate(item.view)}
              className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                active ? 'bg-accent-weak text-accent' : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`}
            >
              <Icon size={16} />
              {item.label}
            </button>
          )
        })}

        <div className="px-3 pb-1 pt-4 font-mono text-[10px] uppercase tracking-wider text-muted">
          Coming soon
        </div>
        {NAV_SOON.map((item) => {
          const Icon = item.icon
          return (
            <div
              key={item.label}
              className="flex cursor-not-allowed items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-muted/70"
            >
              <Icon size={16} />
              {item.label}
            </div>
          )
        })}
      </nav>

      <div className="border-t border-hair px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-muted">
        Local test · v0.1
      </div>
    </aside>
  )
}
