import { useEffect, useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { IncidentSummary } from '../../lib/types'
import { SeverityBadge } from '../../components/ui/SeverityBadge'

export function IncidentList({
  selectedId,
  onSelect,
  refreshKey,
}: {
  selectedId: string | null
  onSelect: (id: string) => void
  refreshKey: number
}) {
  const [rows, setRows] = useState<IncidentSummary[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<IncidentSummary[]>('/api/incidents')
      .then((r) => {
        setRows(r)
        setErr(null)
      })
      .catch((e: ApiError) => setErr(e.detail))
  }, [refreshKey])

  if (err) return <p className="p-3 text-xs text-sev-critical">Failed to load: {err}</p>
  if (!rows.length) return <p className="p-4 text-xs text-muted">No incidents yet — create one.</p>
  return (
    <ul className="divide-y divide-hair">
      {rows.map((i) => (
        <li key={i.id}>
          <button
            onClick={() => onSelect(i.id)}
            className={`w-full border-l-2 px-3 py-2.5 text-left transition ${
              selectedId === i.id
                ? 'border-accent bg-accent-weak'
                : 'border-transparent hover:bg-surface-2'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-display text-sm font-semibold tracking-tight text-ink">
                {i.service}
              </span>
              <SeverityBadge severity={i.severity} size="xs" />
            </div>
            <div className="mt-0.5 text-xs text-muted">
              {i.status} · {new Date(i.created_at).toLocaleString()}
            </div>
            <div className="mt-1 truncate font-mono text-[10px] text-muted/70">{i.fingerprint}</div>
          </button>
        </li>
      ))}
    </ul>
  )
}
