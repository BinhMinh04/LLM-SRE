import { useEffect, useState } from 'react'
import { FileText } from 'lucide-react'
import { api, ApiError } from '../../lib/api'
import type { DocumentSummary } from '../../lib/types'
import { Badge } from '../../components/ui/Badge'

export function DocumentList({ refreshKey }: { refreshKey: number }) {
  const [rows, setRows] = useState<DocumentSummary[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<DocumentSummary[]>('/api/documents')
      .then((r) => {
        setRows(r)
        setErr(null)
      })
      .catch((e: ApiError) => setErr(e.detail))
  }, [refreshKey])

  if (err) return <p className="text-sm text-sev-critical">Failed to load: {err}</p>
  if (!rows.length)
    return (
      <div className="rounded-xl border border-dashed border-hair p-10 text-center text-sm text-muted">
        No documents indexed. Use <span className="font-medium text-ink-2">New document</span> to add one.
      </div>
    )
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {rows.map((d) => (
        <div key={d.id} className="rounded-xl border border-hair bg-surface p-4 shadow-card">
          <div className="flex items-start justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-muted">
                <FileText size={15} />
              </span>
              <span className="truncate font-display text-sm font-semibold tracking-tight text-ink">
                {d.title}
              </span>
            </div>
            <Badge tone="accent">{d.source_type}</Badge>
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs text-muted">
            <span className="font-medium tabular-nums text-ink-2">{d.chunk_count}</span> chunks
            {d.service && <span>· {d.service}</span>}
          </div>
          {d.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {d.tags.map((t) => (
                <span key={t} className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-2">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
