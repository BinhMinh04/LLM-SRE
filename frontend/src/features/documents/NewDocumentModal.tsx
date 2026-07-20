import { useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { DocumentCreated } from '../../lib/types'
import { SOURCE_TYPES } from '../../lib/types'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { Textarea } from '../../components/ui/Textarea'

const inputCls =
  'w-full rounded-lg border border-hair bg-plane p-1.5 text-sm text-ink outline-none focus:border-accent'

export function NewDocumentModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: () => void
}) {
  const [title, setTitle] = useState('')
  const [sourceType, setSourceType] = useState<string>(SOURCE_TYPES[0])
  const [service, setService] = useState('')
  const [tags, setTags] = useState('')
  const [content, setContent] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setErr(null)
    setBusy(true)
    try {
      const res = await api.post<DocumentCreated>('/api/documents', {
        title,
        source_type: sourceType,
        service: service || null,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        content,
      })
      alert(`Indexed ${res.chunks} chunk(s) — id ${res.document_id}`)
      onCreated()
      onClose()
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="New knowledge document" onClose={onClose}>
      <Field label="Title">
        <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} />
      </Field>
      <Field label="Source type">
        <select className={inputCls} value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
          {SOURCE_TYPES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Service (optional)">
        <input className={inputCls} value={service} onChange={(e) => setService(e.target.value)} />
      </Field>
      <Field label="Tags (comma-separated)">
        <input className={inputCls} value={tags} onChange={(e) => setTags(e.target.value)} />
      </Field>
      <Field label="Content">
        <Textarea rows={12} value={content} onChange={(e) => setContent(e.target.value)} />
      </Field>
      {err && <p className="text-xs text-sev-critical">{err}</p>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={submit} disabled={busy}>
          {busy ? 'Indexing…' : 'Ingest'}
        </Button>
      </div>
    </Modal>
  )
}
