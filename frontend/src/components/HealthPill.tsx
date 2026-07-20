import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Health } from '../lib/types'

type State = 'ok' | 'degraded' | 'offline'

const meta: Record<State, { label: string; color: string }> = {
  ok: { label: 'Operational', color: 'var(--sev-low)' },
  degraded: { label: 'Degraded', color: 'var(--sev-medium)' },
  offline: { label: 'Backend offline', color: 'var(--sev-critical)' },
}

export function HealthPill() {
  const [state, setState] = useState<State>('offline')
  useEffect(() => {
    let alive = true
    const ping = () =>
      api
        .get<Health>('/healthz')
        .then((h) => alive && setState(h.status === 'ok' ? 'ok' : 'degraded'))
        .catch(() => alive && setState('offline'))
    ping()
    const t = setInterval(ping, 10000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])
  const m = meta[state]
  return (
    <span
      className="inline-flex h-9 items-center gap-2 rounded-xl border border-hair bg-surface px-3 text-xs font-semibold"
      style={{ color: m.color }}
      title={`Backend: ${m.label}`}
    >
      <span className="relative flex h-2 w-2">
        {state === 'ok' && (
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
            style={{ background: m.color }}
          />
        )}
        <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: m.color }} />
      </span>
      {m.label}
    </span>
  )
}
