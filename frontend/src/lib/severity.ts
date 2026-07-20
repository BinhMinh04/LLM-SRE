// Severity → status palette (fixed, pre-validated in the dataviz reference).
// Every rendering pairs the color with a text label, so meaning is never color-alone.

export type SeverityKey = 'critical' | 'high' | 'medium' | 'low' | 'unknown'

export interface SeverityMeta {
  key: SeverityKey
  label: string
  /** CSS custom-property reference for the status color. */
  color: string
  /** True for severities that should draw the eye (dashboard "needs attention"). */
  urgent: boolean
}

const TABLE: Record<Exclude<SeverityKey, 'unknown'>, SeverityMeta> = {
  critical: { key: 'critical', label: 'Critical', color: 'var(--sev-critical)', urgent: true },
  high: { key: 'high', label: 'High', color: 'var(--sev-high)', urgent: true },
  medium: { key: 'medium', label: 'Medium', color: 'var(--sev-medium)', urgent: false },
  low: { key: 'low', label: 'Low', color: 'var(--sev-low)', urgent: false },
}

export function severityMeta(severity?: string | null): SeverityMeta {
  const s = (severity ?? '').toLowerCase()
  if (s in TABLE) return TABLE[s as keyof typeof TABLE]
  return { key: 'unknown', label: severity || 'Unknown', color: 'var(--muted)', urgent: false }
}

export const SEVERITY_ORDER: Exclude<SeverityKey, 'unknown'>[] = ['critical', 'high', 'medium', 'low']
