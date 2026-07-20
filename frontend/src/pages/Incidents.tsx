import { IncidentList } from '../features/incidents/IncidentList'
import { IncidentDetail } from '../features/incidents/IncidentDetail'

export function Incidents({
  selectedId,
  onSelect,
  refreshKey,
}: {
  selectedId: string | null
  onSelect: (id: string) => void
  refreshKey: number
}) {
  return (
    <div className="grid h-full grid-cols-[300px_1fr] overflow-hidden">
      <aside className="overflow-y-auto border-r border-hair bg-surface">
        <IncidentList selectedId={selectedId} onSelect={onSelect} refreshKey={refreshKey} />
      </aside>
      <section className="overflow-y-auto bg-plane">
        <IncidentDetail incidentId={selectedId} />
      </section>
    </div>
  )
}
