import { DocumentList } from '../features/documents/DocumentList'

export function KnowledgeBase({ refreshKey }: { refreshKey: number }) {
  return (
    <div className="animate-in h-full overflow-y-auto p-6">
      <DocumentList refreshKey={refreshKey} />
    </div>
  )
}
