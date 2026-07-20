// Incident lifecycle status → pastel badge tone. The label always renders, so a
// status is never communicated by color alone. Unknown statuses fall back to a
// title-cased neutral pill rather than breaking, since the backend owns the
// exact vocabulary.

export type StatusTone = 'info' | 'warning' | 'success' | 'neutral' | 'accent'

export interface StatusMeta {
  label: string
  tone: StatusTone
}

const TABLE: Record<string, StatusMeta> = {
  new: { label: 'New', tone: 'info' },
  open: { label: 'Open', tone: 'warning' },
  investigating: { label: 'Investigating', tone: 'info' },
  analyzing: { label: 'Analyzing', tone: 'info' },
  analyzed: { label: 'Analyzed', tone: 'accent' },
  triaged: { label: 'Triaged', tone: 'accent' },
  monitoring: { label: 'Monitoring', tone: 'accent' },
  mitigated: { label: 'Mitigated', tone: 'success' },
  resolved: { label: 'Resolved', tone: 'success' },
  closed: { label: 'Closed', tone: 'neutral' },
}

export function statusMeta(status?: string | null): StatusMeta {
  const s = (status ?? '').toLowerCase().trim()
  if (s in TABLE) return TABLE[s]
  const label = s ? s.charAt(0).toUpperCase() + s.slice(1) : 'Unknown'
  return { label, tone: 'neutral' }
}
