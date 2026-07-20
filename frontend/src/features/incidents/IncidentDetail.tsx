import { useEffect, useState, type ReactNode } from 'react'
import { Cpu, FileSearch, FileText, Gauge, MousePointerClick } from 'lucide-react'
import { api, errText } from '../../lib/api'
import type { IncidentDetail as Detail } from '../../lib/types'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { SeverityBadge } from '../../components/ui/SeverityBadge'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Eyebrow } from '../../components/ui/Eyebrow'
import { Skeleton } from '../../components/ui/Skeleton'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { incidentRef } from '../../lib/format'

export function IncidentDetail({ incidentId }: { incidentId: string | null }) {
  const [d, setD] = useState<Detail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!incidentId) {
      setD(null)
      setErr(null)
      return
    }
    let alive = true
    setD(null)
    setErr(null)
    setLoading(true)
    api
      .get<Detail>(`/api/incidents/${incidentId}`)
      .then((r) => alive && setD(r))
      .catch((e) => alive && setErr(errText(e)))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [incidentId])

  if (!incidentId) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState
          icon={MousePointerClick}
          title="Select an incident"
          hint="Pick one from the list to see its AI triage — severity, root cause, recommended action, and the evidence it cited."
          className="border-0"
        />
      </div>
    )
  }
  if (err) {
    return (
      <div className="p-6">
        <ErrorState detail={err} />
      </div>
    )
  }
  if (loading || !d) return <DetailSkeleton />

  const a = d.analysis
  return (
    <div key={incidentId} className="animate-in mx-auto max-w-3xl space-y-5 p-6">
      {/* Header */}
      <div>
        <Eyebrow>{incidentRef(d.id)}</Eyebrow>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <h2 className="font-display text-2xl font-extrabold tracking-tight text-ink">{d.service}</h2>
          {a && <SeverityBadge severity={a.severity} />}
          <StatusBadge status={d.status} />
          {a && <Badge tone={a._cache === 'HIT' ? 'success' : 'neutral'}>cache {a._cache}</Badge>}
          <Badge>{d.source}</Badge>
        </div>
        <div className="mt-2 font-mono text-[11px] text-muted">
          fingerprint <span className="text-ink-2">{d.fingerprint}</span>
        </div>
      </div>

      {/* Analysis */}
      {a ? (
        <Card className="divide-y divide-hair">
          <Section label="Summary">{a.summary}</Section>
          <Section label="Root cause">{a.root_cause}</Section>
          <Section label="Recommended action">{a.recommended_action}</Section>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-3.5 text-xs text-muted">
            <span className="inline-flex items-center gap-1.5">
              <Gauge size={13} /> confidence{' '}
              <span className="font-semibold text-ink-2">{a.confidence ?? 'n/a'}</span>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Cpu size={13} /> <span className="font-mono text-ink-2">{a.model_id}</span>
            </span>
          </div>
        </Card>
      ) : (
        <Card className="p-5">
          <EmptyState
            icon={FileSearch}
            title="No analysis yet"
            hint="This incident hasn't produced an AI analysis."
            className="border-0 py-6"
          />
        </Card>
      )}

      {/* Evidence */}
      {a && a.evidence.length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2">
            <FileText size={15} className="text-accent" />
            <h3 className="font-display text-sm font-bold text-ink">Evidence</h3>
            <Badge tone="accent">{a.evidence.length}</Badge>
          </div>
          <ul className="mt-3 space-y-1.5">
            {a.evidence.map((e) => (
              <li
                key={e.chunk_id}
                className="flex items-center gap-2.5 rounded-lg bg-surface-2 px-3 py-2 text-sm"
              >
                <Badge tone="info">{e.source_type}</Badge>
                <span className="truncate text-ink">{e.title}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Raw context */}
      <details className="group rounded-2xl border border-hair bg-surface">
        <summary className="cursor-pointer px-5 py-3.5 text-[11px] font-bold uppercase tracking-[0.14em] text-muted transition hover:text-ink-2">
          Raw context
        </summary>
        <pre className="max-h-96 overflow-auto border-t border-hair p-4 font-mono text-xs leading-relaxed text-ink-2">
          {JSON.stringify(d.context, null, 2)}
        </pre>
      </details>
    </div>
  )
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="px-5 py-4">
      <Eyebrow>{label}</Eyebrow>
      <p className="mt-1.5 leading-relaxed text-ink">{children}</p>
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-3xl space-y-5 p-6">
      <div className="space-y-2">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-3 w-48" />
      </div>
      <Skeleton className="h-56 rounded-2xl" />
      <Skeleton className="h-28 rounded-2xl" />
    </div>
  )
}
