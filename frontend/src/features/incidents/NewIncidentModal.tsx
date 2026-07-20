import { useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { IncidentCreated } from '../../lib/types'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { Textarea } from '../../components/ui/Textarea'
import { SAMPLE_INFRA_OOM, SAMPLE_APICOST } from './samples'

export function NewIncidentModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const [source, setSource] = useState('manual')
  const [text, setText] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const loadPreset = (obj: unknown) => {
    setText(JSON.stringify(obj, null, 2))
    setErr(null)
  }

  const submit = async () => {
    setErr(null)
    let context: unknown
    try {
      context = JSON.parse(text)
    } catch {
      setErr('Context is not valid JSON')
      return
    }
    setBusy(true)
    try {
      const res = await api.post<IncidentCreated>('/api/incidents', { source, context })
      onCreated(res.incident_id)
      onClose()
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} title="New incident" onClose={onClose}>
      <div className="flex gap-2">
        <Button variant="ghost" onClick={() => loadPreset(SAMPLE_INFRA_OOM)}>
          Load infra_oom
        </Button>
        <Button variant="ghost" onClick={() => loadPreset(SAMPLE_APICOST)}>
          Load apicost_overage
        </Button>
      </div>
      <Field label="Source">
        <select
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="rounded-lg border border-hair bg-plane p-1.5 text-sm text-ink outline-none focus:border-accent"
        >
          <option value="manual">manual</option>
          <option value="auto">auto</option>
          <option value="webhook">webhook</option>
        </select>
      </Field>
      <Field label="Context (JSON — must contain 'service')">
        <Textarea
          rows={16}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={'{ "service": "..." }'}
        />
      </Field>
      {err && <p className="text-xs text-sev-critical">{err}</p>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={submit} disabled={busy}>
          {busy ? 'Analyzing…' : 'Analyze'}
        </Button>
      </div>
    </Modal>
  )
}
