import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { AlertTriangle, Cpu, FileSearch, FileText, Gauge, MousePointerClick, Sparkles } from 'lucide-react'
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
import { useIncidentStream } from '../../lib/useIncidentStream'

export function IncidentDetail({ incidentId }: { incidentId: string | null }) {
  const [d, setD] = useState<Detail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchDetail = useCallback((id: string) => {
    let alive = true
    setErr(null)
    api
      .get<Detail>(`/api/incidents/${id}`)
      .then((r) => alive && setD(r))
      .catch((e) => alive && setErr(errText(e)))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (!incidentId) {
      setD(null)
      setErr(null)
      return
    }
    setD(null)
    setLoading(true)
    return fetchDetail(incidentId)
  }, [incidentId, fetchDetail])

  // While the incident is still analyzing, subscribe to its live progress; once analysis
  // settles (success or failure), re-fetch the authoritative detail rather than hand-building
  // it from the stream payload.
  const analyzing = d?.status === 'analyzing'
  const stream = useIncidentStream(analyzing ? incidentId : null)

  useEffect(() => {
    if (!incidentId || !(stream.result || stream.error)) return
    return fetchDetail(incidentId)
  }, [stream.result, stream.error, incidentId, fetchDetail])

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
      {analyzing && !stream.result && !stream.error ? (
        <Card className="p-5">
          <div className="flex items-center gap-2">
            <Sparkles size={15} className="text-accent" />
            <h3 className="font-display text-sm font-bold text-ink">Analyzing…</h3>
          </div>
          <ul className="mt-4 space-y-3">
            {stream.stages.length === 0 ? (
              <li className="text-sm text-muted">Starting…</li>
            ) : (
              stream.stages.map((s, i) => (
                <li key={i} className="flex items-center gap-3 text-sm">
                  <span className="h-2 w-2 shrink-0 rounded-full bg-accent" />
                  <span className="font-medium text-ink">{s.label}</span>
                  {s.detail && <span className="text-xs text-muted">{s.detail}</span>}
                </li>
              ))
            )}
          </ul>
        </Card>
      ) : a ? (
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
      ) : d.status === 'failed' ? (
        <Card className="p-5">
          <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
            <span
              className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl"
              style={{
                background: 'color-mix(in srgb, var(--sev-critical) 14%, transparent)',
                color: 'var(--sev-critical)',
              }}
            >
              <AlertTriangle size={26} />
            </span>
            <h3 className="font-display text-base font-bold text-ink">Analysis failed</h3>
            <p className="mt-1.5 max-w-md text-sm leading-relaxed text-ink-2">
              {stream.error ?? 'The AI analysis could not complete.'}
            </p>
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
