import { statusMeta } from '../../lib/status'
import { Badge } from './Badge'

/** Incident lifecycle status as a pastel pill (color + text label + dot). */
export function StatusBadge({ status }: { status?: string | null }) {
  const m = statusMeta(status)
  return (
    <Badge tone={m.tone} dot>
      {m.label}
    </Badge>
  )
}
