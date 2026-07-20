import { HelpCircle, ShieldAlert } from 'lucide-react'
import { NAV_SECTIONS, type View } from '../../lib/nav'

export function Sidebar({ view, onNavigate }: { view: View; onNavigate: (v: View) => void }) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col bg-rail text-rail-text md:flex">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 py-5">
        <span
          className="flex h-10 w-10 items-center justify-center rounded-xl text-white shadow-rail"
          style={{ background: 'linear-gradient(135deg, var(--accent), var(--purple))' }}
        >
          <ShieldAlert size={20} strokeWidth={2.2} />
        </span>
        <div className="leading-tight">
          <div className="font-display text-lg font-extrabold tracking-tight text-white">IIM</div>
          <div className="text-[11px] font-medium text-rail-dim">Incident Intelligence</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-1">
        {NAV_SECTIONS.map((section) => (
          <div key={section.heading} className="mb-5">
            <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-rail-dim">
              {section.heading}
            </div>
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon
                const active = view === item.view
                return (
                  <button
                    key={item.view}
                    onClick={() => onNavigate(item.view)}
                    aria-current={active ? 'page' : undefined}
                    className={`relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                      active
                        ? 'bg-[var(--rail-active-bg)] text-white'
                        : 'text-rail-text hover:bg-[var(--rail-hover)] hover:text-white'
                    }`}
                  >
                    {active && (
                      <span className="absolute -left-3 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-accent" />
                    )}
                    <Icon size={18} strokeWidth={2.1} className={active ? '' : 'opacity-80'} />
                    {item.label}
                  </button>
                )
              })}
              {section.soon?.map((item) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.label}
                    className="flex cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-rail-dim"
                    title="Planned — not built yet"
                  >
                    <Icon size={18} strokeWidth={2} />
                    <span className="flex-1">{item.label}</span>
                    <span className="rounded-full bg-white/[0.06] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide">
                      Soon
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-rail-hair px-3 py-3">
        <div
          className="flex cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-rail-dim"
          title="Planned — not built yet"
        >
          <HelpCircle size={18} strokeWidth={2} /> Help &amp; docs
        </div>
        <div className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-rail-dim">
          Local test build · v0.1
        </div>
      </div>
    </aside>
  )
}
