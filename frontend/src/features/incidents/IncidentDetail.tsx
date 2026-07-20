import { useEffect, useState } from 'react'
import { FileText } from 'lucide-react'
import { api, ApiError } from '../../lib/api'
import type { IncidentDetail as Detail } from '../../lib/types'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { SeverityBadge } from '../../components/ui/SeverityBadge'
import { Eyebrow } from '../../components/ui/Eyebrow'

export function IncidentDetail({ incidentId }: { incidentId: string | null }) {
  const [d, setD] = useState<Detail | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!incidentId) {
      setD(null)
      return
    }
    setD(null)
    api
      .get<Detail>(`/api/incidents/${incidentId}`)
      .then((r) => {
        setD(r)
        setErr(null)
      })
      .catch((e: ApiError) => setErr(e.detail))
  }, [incidentId])

  if (!incidentId)
    return (
      <div className="flex h-full items-center justify-center p-8 text-center text-sm text-muted">
        Select an incident to see its AI analysis and evidence.
      </div>
    )
  if (err) return <p className="p-6 text-sm text-sev-critical">Failed to load: {err}</p>
  if (!d) return <p className="p-6 text-sm text-muted">Loading…</p>

  const a = d.analysis
  return (
    <div key={incidentId} className="animate-in mx-auto max-w-3xl space-y-4 p-6">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">{d.service}</h2>
          {a && <SeverityBadge severity={a.severity} />}
          {a && <Badge tone={a._cache === 'HIT' ? 'accent' : 'neutral'}>cache {a._cache}</Badge>}
          <Badge>{d.source}</Badge>
        </div>
        <div className="mt-1.5 font-mono text-[11px] text-muted">
          fingerprint <span className="text-ink-2">{d.fingerprint}</span>
        </div>
      </div>

      {a ? (
        <Card className="space-y-3 p-4 text-sm">
          <Section label="Summary" value={a.summary} />
          <Section label="Root cause" value={a.root_cause} />
          <Section label="Recommended action" value={a.recommended_action} />
          <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-hair pt-3 text-xs text-muted">
            <span>
              confidence <span className="font-medium text-ink-2">{a.confidence ?? 'n/a'}</span>
            </span>
            <span>
              model <span className="font-mono text-ink-2">{a.model_id}</span>
            </span>
          </div>
        </Card>
      ) : (
        <Card className="p-4 text-sm text-muted">No analysis yet.</Card>
      )}

      {a && a.evidence.length > 0 && (
        <Card className="p-4">
          <Eyebrow className="mb-3 flex items-center gap-1.5">
            <FileText size={12} /> Evidence · {a.evidence.length} chunk{a.evidence.length > 1 ? 's' : ''}
          </Eyebrow>
          <ul className="space-y-2 text-sm">
            {a.evidence.map((e) => (
              <li key={e.chunk_id} className="flex items-center gap-2">
                <Badge tone="accent">{e.source_type}</Badge>
                <span className="text-ink">{e.title}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <details className="group rounded-xl border border-hair bg-surface">
        <summary className="cursor-pointer px-4 py-3 font-mono text-[11px] uppercase tracking-wider text-muted">
          <span className="text-accent">// </span>Raw context
        </summary>
        <pre className="overflow-x-auto border-t border-hair p-4 text-xs text-ink-2">
          {JSON.stringify(d.context, null, 2)}
        </pre>
      </details>
    </div>
  )
}

function Section({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Eyebrow>{label}</Eyebrow>
      <p className="mt-1 leading-relaxed text-ink">{value}</p>
    </div>
  )
}
