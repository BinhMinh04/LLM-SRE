import { useEffect, useState } from 'react'
import { AlertTriangle, BookOpen, Layers, ShieldAlert } from 'lucide-react'
import { api, ApiError } from '../lib/api'
import type { DocumentSummary, IncidentSummary } from '../lib/types'
import { severityMeta, SEVERITY_ORDER } from '../lib/severity'
import { StatTile } from '../components/ui/StatTile'
import { Card } from '../components/ui/Card'
import { SeverityBadge } from '../components/ui/SeverityBadge'

export function Overview({
  refreshKey,
  onOpenIncident,
}: {
  refreshKey: number
  onOpenIncident: (id: string) => void
}) {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([])
  const [docs, setDocs] = useState<DocumentSummary[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.get<IncidentSummary[]>('/api/incidents'), api.get<DocumentSummary[]>('/api/documents')])
      .then(([i, d]) => {
        setIncidents(i)
        setDocs(d)
        setErr(null)
      })
      .catch((e: ApiError) => setErr(e.detail))
  }, [refreshKey])

  const urgent = incidents.filter((r) => severityMeta(r.severity).urgent).length
  const chunks = docs.reduce((s, d) => s + d.chunk_count, 0)
  const counts = SEVERITY_ORDER.map((key) => ({
    key,
    meta: severityMeta(key),
    n: incidents.filter((r) => severityMeta(r.severity).key === key).length,
  }))
  const total = incidents.length
  const recent = incidents.slice(0, 6)

  if (err) return <p className="p-6 text-sm text-sev-critical">Failed to load: {err}</p>

  return (
    <div className="animate-in h-full space-y-5 overflow-y-auto p-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Incidents" value={total} icon={AlertTriangle} sublabel="Total ingested" />
        <StatTile
          label="Needs attention"
          value={urgent}
          icon={ShieldAlert}
          accent="var(--sev-critical)"
          sublabel="Critical + High"
        />
        <StatTile
          label="Knowledge docs"
          value={docs.length}
          icon={BookOpen}
          accent="var(--sev-low)"
          sublabel="Indexed for RAG"
        />
        <StatTile
          label="Evidence chunks"
          value={chunks}
          icon={Layers}
          accent="#7c5cff"
          sublabel="Retrievable"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.4fr]">
        <Card className="p-5">
          <h3 className="font-display text-sm font-semibold tracking-tight text-ink">Severity breakdown</h3>
          {total === 0 ? (
            <p className="mt-3 text-sm text-muted">No incidents yet.</p>
          ) : (
            <>
              <div className="mt-4 flex h-2.5 gap-0.5 overflow-hidden rounded-full">
                {counts
                  .filter((c) => c.n > 0)
                  .map((c) => (
                    <div
                      key={c.key}
                      style={{ background: c.meta.color, flexGrow: c.n }}
                      title={`${c.meta.label}: ${c.n}`}
                    />
                  ))}
              </div>
              <ul className="mt-4 space-y-2">
                {counts.map((c) => (
                  <li key={c.key} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-ink-2">
                      <span className="h-2 w-2 rounded-full" style={{ background: c.meta.color }} />
                      {c.meta.label}
                    </span>
                    <span className="font-medium tabular-nums text-ink">{c.n}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>

        <Card className="p-5">
          <h3 className="mb-1 font-display text-sm font-semibold tracking-tight text-ink">Recent incidents</h3>
          {recent.length === 0 ? (
            <p className="mt-3 text-sm text-muted">No incidents yet — create one from the Incidents tab.</p>
          ) : (
            <ul className="divide-y divide-hair">
              {recent.map((i) => (
                <li key={i.id}>
                  <button
                    onClick={() => onOpenIncident(i.id)}
                    className="flex w-full items-center justify-between py-2.5 text-left hover:opacity-80"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-display text-sm font-semibold tracking-tight text-ink">
                        {i.service}
                      </div>
                      <div className="truncate text-xs text-muted">
                        {i.summary || i.status} · {new Date(i.created_at).toLocaleString()}
                      </div>
                    </div>
                    <SeverityBadge severity={i.severity} size="xs" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
