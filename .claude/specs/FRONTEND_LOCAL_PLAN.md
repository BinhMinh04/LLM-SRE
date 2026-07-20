# IIM Local Frontend Test UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lean local web UI (`frontend/`) that exercises the existing RAG incident-analysis backend end-to-end — submit incidents, seed knowledge docs, and view AI analysis + evidence — so we can test and iterate.

**Architecture:** Vite + React + TypeScript single-page board. A thin `fetch` client talks to the FastAPI backend through a Vite dev proxy (`/api` → `:8000`). Two-column layout: incident/document list on the left, detail panel on the right. Incident ingest is synchronous on the backend, so the create flow is `POST` then `GET {id}` — no streaming, no polling.

**Tech Stack:** Vite 5, React 18, TypeScript 5, Tailwind CSS 3. No shadcn/Radix — hand-rolled UI primitives. No React Router (single page). No automated test framework (see Global Constraints).

## Global Constraints

- **Language:** all code, comments, UI copy, and logs in **English** (`.claude/specs/SPEC.md` §1).
- **No automated FE test framework** (spec §2, YAGNI). Per-task verification = `npx tsc --noEmit` + `npm run build` + a stated manual browser check against the running backend. "Write the failing test" steps are therefore replaced by "define the expected observable behavior + verify it manually."
- **API base is `/api`** (proxied in dev), never a hardcoded `http://localhost:8000`.
- **Backend contracts are fixed** — do not change the backend. Types mirror the DTOs in `.claude/specs/FRONTEND_LOCAL.md` §3.
- **Git:** work on `feature/frontend-local`; small frequent commits; no `Co-Authored-By` trailer.
- **Node:** assume Node ≥ 18 (Vite 5 requirement).

## Prerequisites (one-time, before Task 1)

Backend must be runnable so manual checks work:
```bash
docker compose -f iac/docker-compose.yml up        # db (pgvector) + backend on :8000
# verify:
curl -s localhost:8000/healthz                       # {"status":"ok"|"degraded",...}
```
If Bedrock creds are unavailable, incident analysis will error at the LLM step — that is a backend/env
concern, not an FE bug. The read path (list/detail of already-analyzed incidents) and document ingest
list still exercise the UI.

---

### Task 1: Scaffold + foundation (shell, proxy, API client, types, UI primitives, health dot)

Foundation task: everything needed for a running shell that talks to the backend. Later tasks add the
feature panels on top.

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`
- Create: `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/App.tsx`
- Create: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`
- Create: `frontend/src/components/ui/{Button,Card,Badge,Field,Textarea,Modal}.tsx`
- Create: `frontend/src/components/HealthDot.tsx`
- Create: `frontend/.gitignore` (node_modules, dist)

**Interfaces produced (consumed by Tasks 2–4):**
- `types.ts`: `IncidentSummary`, `IncidentDetail`, `AnalysisOut`, `EvidenceRef`, `DocumentSummary`, `IncidentCreated`, `DocumentCreated`, `Health`.
- `api.ts`: `class ApiError extends Error { status: number; detail: string }`; `api.get<T>(path): Promise<T>`; `api.post<T>(path, body): Promise<T>`. Base path `/api` (health uses `/healthz`, so allow an absolute path override).
- UI primitives: `Button({variant?: 'primary'|'ghost'|'danger', ...})`, `Card`, `Badge({tone?})`, `Field({label, children})`, `Textarea`, `Modal({open, title, onClose, children})`.

- [ ] **Step 1: Scaffold Vite React-TS app**

```bash
cd frontend 2>/dev/null || (cd .. && npm create vite@latest frontend -- --template react-ts && cd frontend)
# If `frontend/` was created empty first, run instead:
# npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 2: Configure Tailwind**

`frontend/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```
`frontend/src/index.css` (replace contents):
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }
body { @apply bg-slate-50 text-slate-800; }
```

- [ ] **Step 3: Configure the dev proxy**

`frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/healthz': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

- [ ] **Step 4: Define backend types** — `frontend/src/lib/types.ts`

```ts
export interface EvidenceRef { chunk_id: string; source_type: string; title: string }

export interface AnalysisOut {
  severity: string
  summary: string
  root_cause: string
  recommended_action: string
  confidence: number | null
  model_id: string
  _cache: 'HIT' | 'MISS'
  evidence: EvidenceRef[]
}

export interface IncidentSummary {
  id: string; service: string; source: string; status: string
  fingerprint: string; created_at: string
  severity?: string | null; summary?: string | null
}

export interface IncidentDetail {
  id: string; service: string; source: string; status: string
  fingerprint: string; context: Record<string, unknown>
  created_at: string; updated_at: string
  analysis: AnalysisOut | null
}

export interface IncidentCreated { incident_id: string; status: string; stream: string }

export interface DocumentSummary {
  id: string; title: string; source_type: string
  service: string | null; tags: string[]; chunk_count: number
  created_at: string; updated_at: string
}
export interface DocumentCreated { document_id: string; chunks: number }

export interface Health { status: string; app: string; database: string }

export type SourceType = 'runbook' | 'postmortem' | 'architecture' | 'vendor'
export const SOURCE_TYPES: SourceType[] = ['runbook', 'postmortem', 'architecture', 'vendor']
```

- [ ] **Step 5: Write the API client** — `frontend/src/lib/api.ts`

```ts
export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`HTTP ${status}: ${detail}`)
    this.name = 'ApiError'
  }
}

async function handle<T>(res: Response): Promise<T> {
  const text = await res.text()
  const body = text ? JSON.parse(text) : null
  if (!res.ok) {
    const detail =
      body && typeof body === 'object' && 'detail' in body
        ? typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
        : res.statusText
    throw new ApiError(res.status, detail)
  }
  return body as T
}

export const api = {
  get: <T>(path: string): Promise<T> => fetch(path).then((r) => handle<T>(r)),
  post: <T>(path: string, body: unknown): Promise<T> =>
    fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then((r) => handle<T>(r)),
}
```

- [ ] **Step 6: Write UI primitives** — `frontend/src/components/ui/*.tsx`

Small, presentational, Tailwind-only. Each is one file. Reference implementations:

`Button.tsx`:
```tsx
import type { ButtonHTMLAttributes } from 'react'
const styles = {
  primary: 'bg-slate-900 text-white hover:bg-slate-700',
  ghost: 'bg-white border border-slate-300 hover:bg-slate-100',
  danger: 'bg-red-600 text-white hover:bg-red-500',
}
export function Button({ variant = 'primary', className = '', ...p }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof styles }) {
  return <button className={`rounded px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${styles[variant]} ${className}`} {...p} />
}
```
`Card.tsx`:
```tsx
import type { ReactNode } from 'react'
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-slate-200 bg-white ${className}`}>{children}</div>
}
```
`Badge.tsx`:
```tsx
import type { ReactNode } from 'react'
const tones: Record<string, string> = {
  neutral: 'bg-slate-100 text-slate-700', red: 'bg-red-100 text-red-700',
  amber: 'bg-amber-100 text-amber-800', green: 'bg-green-100 text-green-700',
  blue: 'bg-blue-100 text-blue-700',
}
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  return <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${tones[tone] ?? tones.neutral}`}>{children}</span>
}
```
`Field.tsx`:
```tsx
import type { ReactNode } from 'react'
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block space-y-1"><span className="text-xs font-medium text-slate-600">{label}</span>{children}</label>
}
```
`Textarea.tsx`:
```tsx
import type { TextareaHTMLAttributes } from 'react'
export function Textarea({ className = '', ...p }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`w-full rounded border border-slate-300 p-2 font-mono text-xs ${className}`} {...p} />
}
```
`Modal.tsx`:
```tsx
import type { ReactNode } from 'react'
import { Button } from './Button'
export function Modal({ open, title, onClose, children }:
  { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-6 overflow-y-auto">
      <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="font-semibold">{title}</h2>
          <Button variant="ghost" onClick={onClose}>✕</Button>
        </div>
        <div className="p-4 space-y-3">{children}</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Health dot** — `frontend/src/components/HealthDot.tsx`

```tsx
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Health } from '../lib/types'

export function HealthDot() {
  const [state, setState] = useState<'ok' | 'degraded' | 'offline'>('offline')
  useEffect(() => {
    let alive = true
    const ping = () => api.get<Health>('/healthz')
      .then((h) => alive && setState(h.status === 'ok' ? 'ok' : 'degraded'))
      .catch(() => alive && setState('offline'))
    ping()
    const t = setInterval(ping, 10000)
    return () => { alive = false; clearInterval(t) }
  }, [])
  const color = state === 'ok' ? 'bg-green-500' : state === 'degraded' ? 'bg-amber-500' : 'bg-red-500'
  return <span className="flex items-center gap-1.5 text-xs text-slate-500">
    <span className={`h-2 w-2 rounded-full ${color}`} />{state}</span>
}
```

- [ ] **Step 8: Minimal App shell** — `frontend/src/App.tsx`

```tsx
import { HealthDot } from './components/HealthDot'

export default function App() {
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <h1 className="text-sm font-semibold">IIM · Incident Analysis (local test)</h1>
        <HealthDot />
      </header>
      <main className="flex-1 p-4 text-sm text-slate-400">Board coming in Task 2…</main>
    </div>
  )
}
```
Ensure `frontend/src/main.tsx` renders `<App/>` and imports `./index.css` (Vite template does this; adjust if needed).

- [ ] **Step 9: Verify (typecheck + build + browser)**

```bash
cd frontend
npx tsc --noEmit          # Expected: no errors
npm run build             # Expected: build succeeds, dist/ produced
npm run dev               # Expected: http://localhost:5173 shows the header
```
Manual: with the backend up, the header dot reads **ok** (green). Stop the backend → within 10s it flips to **offline** (red). No console errors.

- [ ] **Step 10: Commit**

```bash
git add frontend
git commit -m "feat(frontend): scaffold Vite+React+Tailwind shell, API client, health dot"
```

---

### Task 2: Incident read path (list + detail + two-column layout)

**Files:**
- Create: `frontend/src/features/incidents/IncidentList.tsx`
- Create: `frontend/src/features/incidents/IncidentDetail.tsx`
- Modify: `frontend/src/App.tsx` (layout + selection state)

**Interfaces:**
- Consumes: `api`, `types`, UI primitives from Task 1.
- Produces: `IncidentList({ selectedId, onSelect, refreshKey })`, `IncidentDetail({ incidentId })`. `App` owns `selectedId: string | null` and a `refreshKey: number` bumped to force list reloads (used by Task 3).

- [ ] **Step 1: Define expected behavior (manual test contract)**

Given the backend has ≥1 incident, the left column lists them (service, severity badge, status, created_at). Clicking a row loads `GET /api/incidents/{id}` into the right panel, showing analysis fields + evidence + collapsible context JSON. Empty list shows "No incidents yet."

- [ ] **Step 2: IncidentList** — `frontend/src/features/incidents/IncidentList.tsx`

```tsx
import { useEffect, useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { IncidentSummary } from '../../lib/types'
import { Badge } from '../../components/ui/Badge'

const sevTone: Record<string, string> = { critical: 'red', high: 'red', medium: 'amber', low: 'blue' }

export function IncidentList({ selectedId, onSelect, refreshKey }:
  { selectedId: string | null; onSelect: (id: string) => void; refreshKey: number }) {
  const [rows, setRows] = useState<IncidentSummary[]>([])
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    api.get<IncidentSummary[]>('/api/incidents')
      .then((r) => { setRows(r); setErr(null) })
      .catch((e: ApiError) => setErr(e.detail))
  }, [refreshKey])
  if (err) return <p className="p-3 text-xs text-red-600">Failed to load: {err}</p>
  if (!rows.length) return <p className="p-3 text-xs text-slate-400">No incidents yet — create one.</p>
  return (
    <ul className="divide-y divide-slate-100">
      {rows.map((i) => (
        <li key={i.id}>
          <button onClick={() => onSelect(i.id)}
            className={`w-full px-3 py-2 text-left hover:bg-slate-50 ${selectedId === i.id ? 'bg-slate-100' : ''}`}>
            <div className="flex items-center justify-between">
              <span className="font-medium">{i.service}</span>
              {i.severity && <Badge tone={sevTone[i.severity.toLowerCase()] ?? 'neutral'}>{i.severity}</Badge>}
            </div>
            <div className="text-xs text-slate-500">{i.status} · {new Date(i.created_at).toLocaleString()}</div>
          </button>
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 3: IncidentDetail** — `frontend/src/features/incidents/IncidentDetail.tsx`

```tsx
import { useEffect, useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { IncidentDetail as Detail } from '../../lib/types'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'

export function IncidentDetail({ incidentId }: { incidentId: string | null }) {
  const [d, setD] = useState<Detail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    if (!incidentId) { setD(null); return }
    api.get<Detail>(`/api/incidents/${incidentId}`)
      .then((r) => { setD(r); setErr(null) })
      .catch((e: ApiError) => setErr(e.detail))
  }, [incidentId])
  if (!incidentId) return <p className="p-4 text-sm text-slate-400">Select an incident.</p>
  if (err) return <p className="p-4 text-sm text-red-600">Failed to load: {err}</p>
  if (!d) return <p className="p-4 text-sm text-slate-400">Loading…</p>
  const a = d.analysis
  return (
    <div className="space-y-3 p-4">
      <div className="flex items-center gap-2">
        <h2 className="text-base font-semibold">{d.service}</h2>
        {a && <Badge tone={a.severity.toLowerCase() === 'critical' || a.severity.toLowerCase() === 'high' ? 'red' : a.severity.toLowerCase() === 'medium' ? 'amber' : 'blue'}>{a.severity}</Badge>}
        {a && <Badge tone={a._cache === 'HIT' ? 'green' : 'neutral'}>cache {a._cache}</Badge>}
      </div>
      {a ? (
        <Card className="space-y-2 p-3 text-sm">
          <p><span className="font-semibold">Summary:</span> {a.summary}</p>
          <p><span className="font-semibold">Root cause:</span> {a.root_cause}</p>
          <p><span className="font-semibold">Recommended action:</span> {a.recommended_action}</p>
          <p className="text-xs text-slate-500">
            confidence {a.confidence ?? 'n/a'} · model {a.model_id}
          </p>
        </Card>
      ) : <p className="text-sm text-slate-400">No analysis yet.</p>}
      {a && a.evidence.length > 0 && (
        <Card className="p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase text-slate-500">Evidence ({a.evidence.length})</h3>
          <ul className="space-y-1 text-sm">
            {a.evidence.map((e) => (
              <li key={e.chunk_id} className="flex items-center gap-2">
                <Badge tone="blue">{e.source_type}</Badge><span>{e.title}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <details className="rounded border border-slate-200 bg-white p-3">
        <summary className="cursor-pointer text-xs font-semibold uppercase text-slate-500">Context</summary>
        <pre className="mt-2 overflow-x-auto text-xs">{JSON.stringify(d.context, null, 2)}</pre>
      </details>
    </div>
  )
}
```

- [ ] **Step 4: Wire two-column layout** — replace `<main>` in `frontend/src/App.tsx`

```tsx
import { useState } from 'react'
import { HealthDot } from './components/HealthDot'
import { IncidentList } from './features/incidents/IncidentList'
import { IncidentDetail } from './features/incidents/IncidentDetail'

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [refreshKey] = useState(0) // Task 3 will bump this
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <h1 className="text-sm font-semibold">IIM · Incident Analysis (local test)</h1>
        <HealthDot />
      </header>
      <div className="grid flex-1 grid-cols-[320px_1fr] overflow-hidden">
        <aside className="overflow-y-auto border-r border-slate-200 bg-white">
          <IncidentList selectedId={selectedId} onSelect={setSelectedId} refreshKey={refreshKey} />
        </aside>
        <section className="overflow-y-auto">
          <IncidentDetail incidentId={selectedId} />
        </section>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Verify**

```bash
cd frontend && npx tsc --noEmit && npm run build
npm run dev
```
Manual: left column lists incidents (or "No incidents yet"). Clicking a row shows analysis + evidence + context in the right panel. No console errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): incident list + detail read path with two-column board"
```

---

### Task 3: New-incident write path (modal, presets, cache demo)

**Files:**
- Create: `frontend/src/features/incidents/samples.ts` (inlined preset payloads)
- Create: `frontend/src/features/incidents/NewIncidentModal.tsx`
- Modify: `frontend/src/App.tsx` (add button, modal open state, bump `refreshKey`, auto-select created incident)

**Interfaces:**
- Consumes: `api`, `types`, `Modal`, `Button`, `Field`, `Textarea`.
- Produces: `NewIncidentModal({ open, onClose, onCreated })` where `onCreated(incidentId: string)` fires after a successful `POST /api/incidents`.

- [ ] **Step 1: Inline sample payloads** — `frontend/src/features/incidents/samples.ts`

Copy the two objects from `backend/tests/samples/infra_oom.json` and `apicost_overage.json` verbatim as TS constants. (Read those files and paste; they are the canonical two shapes.)

```ts
export const SAMPLE_INFRA_OOM = { /* paste contents of backend/tests/samples/infra_oom.json */ } as const
export const SAMPLE_APICOST = { /* paste contents of backend/tests/samples/apicost_overage.json */ } as const
```

- [ ] **Step 2: NewIncidentModal** — `frontend/src/features/incidents/NewIncidentModal.tsx`

```tsx
import { useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { IncidentCreated } from '../../lib/types'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { Textarea } from '../../components/ui/Textarea'
import { SAMPLE_INFRA_OOM, SAMPLE_APICOST } from './samples'

export function NewIncidentModal({ open, onClose, onCreated }:
  { open: boolean; onClose: () => void; onCreated: (id: string) => void }) {
  const [source, setSource] = useState('manual')
  const [text, setText] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const loadPreset = (obj: unknown) => { setText(JSON.stringify(obj, null, 2)); setErr(null) }

  const submit = async () => {
    setErr(null)
    let context: unknown
    try { context = JSON.parse(text) } catch { setErr('Context is not valid JSON'); return }
    setBusy(true)
    try {
      const res = await api.post<IncidentCreated>('/api/incidents', { source, context })
      onCreated(res.incident_id)
      onClose()
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : String(e))
    } finally { setBusy(false) }
  }

  return (
    <Modal open={open} title="New incident" onClose={onClose}>
      <div className="flex gap-2">
        <Button variant="ghost" onClick={() => loadPreset(SAMPLE_INFRA_OOM)}>Load infra_oom</Button>
        <Button variant="ghost" onClick={() => loadPreset(SAMPLE_APICOST)}>Load apicost_overage</Button>
      </div>
      <Field label="Source">
        <select value={source} onChange={(e) => setSource(e.target.value)}
          className="rounded border border-slate-300 p-1.5 text-sm">
          <option value="manual">manual</option><option value="auto">auto</option><option value="webhook">webhook</option>
        </select>
      </Field>
      <Field label="Context (JSON — must contain 'service')">
        <Textarea rows={16} value={text} onChange={(e) => setText(e.target.value)} placeholder='{ "service": "..." }' />
      </Field>
      {err && <p className="text-xs text-red-600">{err}</p>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button onClick={submit} disabled={busy}>{busy ? 'Analyzing…' : 'Analyze'}</Button>
      </div>
    </Modal>
  )
}
```

- [ ] **Step 3: Wire into App** — `frontend/src/App.tsx`

Add state and the button; make `refreshKey` mutable; auto-select the created incident:
```tsx
// add imports
import { NewIncidentModal } from './features/incidents/NewIncidentModal'
// inside App():
const [refreshKey, setRefreshKey] = useState(0)   // replace the frozen version from Task 2
const [showIncident, setShowIncident] = useState(false)
// header right side — add before <HealthDot/>:
//   <Button onClick={() => setShowIncident(true)}>+ New incident</Button>
// after the layout grid, add:
//   <NewIncidentModal open={showIncident} onClose={() => setShowIncident(false)}
//     onCreated={(id) => { setSelectedId(id); setRefreshKey((k) => k + 1) }} />
```
(Import `Button` from `./components/ui/Button`. Place the button and modal exactly as commented.)

- [ ] **Step 4: Verify**

```bash
cd frontend && npx tsc --noEmit && npm run build && npm run dev
```
Manual (backend + Bedrock creds up):
1. Click **+ New incident** → **Load infra_oom** → **Analyze**. Modal closes, the new incident is selected, detail shows analysis with `cache MISS`.
2. Click **+ New incident** → **Load infra_oom** again → **Analyze**. Detail now shows `cache HIT`.
3. Submit `{}` (no service) → inline error surfaces the backend `422` "context.service is required".
4. Submit malformed JSON → "Context is not valid JSON" before any request.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): new-incident modal with presets and cache-hit demo"
```

---

### Task 4: Documents tab (list + ingest)

**Files:**
- Create: `frontend/src/features/documents/DocumentList.tsx`
- Create: `frontend/src/features/documents/NewDocumentModal.tsx`
- Modify: `frontend/src/App.tsx` (left-column tab switch Incidents | Documents; "+ New document" button)

**Interfaces:**
- Consumes: `api`, `types` (`DocumentSummary`, `DocumentCreated`, `SOURCE_TYPES`), UI primitives.
- Produces: `DocumentList({ refreshKey })`, `NewDocumentModal({ open, onClose, onCreated })` where `onCreated()` bumps a document refresh key.

- [ ] **Step 1: DocumentList** — `frontend/src/features/documents/DocumentList.tsx`

```tsx
import { useEffect, useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { DocumentSummary } from '../../lib/types'
import { Badge } from '../../components/ui/Badge'

export function DocumentList({ refreshKey }: { refreshKey: number }) {
  const [rows, setRows] = useState<DocumentSummary[]>([])
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    api.get<DocumentSummary[]>('/api/documents')
      .then((r) => { setRows(r); setErr(null) })
      .catch((e: ApiError) => setErr(e.detail))
  }, [refreshKey])
  if (err) return <p className="p-3 text-xs text-red-600">Failed to load: {err}</p>
  if (!rows.length) return <p className="p-3 text-xs text-slate-400">No documents indexed.</p>
  return (
    <ul className="divide-y divide-slate-100">
      {rows.map((d) => (
        <li key={d.id} className="px-3 py-2">
          <div className="flex items-center justify-between">
            <span className="font-medium">{d.title}</span>
            <Badge tone="blue">{d.source_type}</Badge>
          </div>
          <div className="text-xs text-slate-500">
            {d.chunk_count} chunks{d.service ? ` · ${d.service}` : ''}{d.tags.length ? ` · ${d.tags.join(', ')}` : ''}
          </div>
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 2: NewDocumentModal** — `frontend/src/features/documents/NewDocumentModal.tsx`

```tsx
import { useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { DocumentCreated } from '../../lib/types'
import { SOURCE_TYPES } from '../../lib/types'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { Textarea } from '../../components/ui/Textarea'

export function NewDocumentModal({ open, onClose, onCreated }:
  { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [title, setTitle] = useState('')
  const [sourceType, setSourceType] = useState<string>(SOURCE_TYPES[0])
  const [service, setService] = useState('')
  const [tags, setTags] = useState('')
  const [content, setContent] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setErr(null); setBusy(true)
    try {
      const res = await api.post<DocumentCreated>('/api/documents', {
        title, source_type: sourceType,
        service: service || null,
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
        content,
      })
      alert(`Indexed ${res.chunks} chunk(s) — id ${res.document_id}`)
      onCreated(); onClose()
    } catch (e) { setErr(e instanceof ApiError ? e.detail : String(e)) }
    finally { setBusy(false) }
  }

  const inputCls = 'w-full rounded border border-slate-300 p-1.5 text-sm'
  return (
    <Modal open={open} title="New knowledge document" onClose={onClose}>
      <Field label="Title"><input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
      <Field label="Source type">
        <select className={inputCls} value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
          {SOURCE_TYPES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </Field>
      <Field label="Service (optional)"><input className={inputCls} value={service} onChange={(e) => setService(e.target.value)} /></Field>
      <Field label="Tags (comma-separated)"><input className={inputCls} value={tags} onChange={(e) => setTags(e.target.value)} /></Field>
      <Field label="Content"><Textarea rows={12} value={content} onChange={(e) => setContent(e.target.value)} /></Field>
      {err && <p className="text-xs text-red-600">{err}</p>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button onClick={submit} disabled={busy}>{busy ? 'Indexing…' : 'Ingest'}</Button>
      </div>
    </Modal>
  )
}
```

- [ ] **Step 3: Add tabs + buttons to App** — `frontend/src/App.tsx`

Introduce `const [tab, setTab] = useState<'incidents' | 'documents'>('incidents')` and `const [docKey, setDocKey] = useState(0)` and `const [showDoc, setShowDoc] = useState(false)`. In the left aside, render a small tab switch; show `IncidentList` when `tab==='incidents'`, else `DocumentList refreshKey={docKey}`. Header buttons: **+ New incident** (when on incidents) and **+ New document**. Mount `NewDocumentModal open={showDoc} onClose={...} onCreated={() => setDocKey((k) => k + 1)}`. Right panel stays the incident detail. Keep all Task 3 wiring intact.

- [ ] **Step 4: Verify**

```bash
cd frontend && npx tsc --noEmit && npm run build && npm run dev
```
Manual: switch to **Documents** tab (empty → "No documents indexed"). **+ New document** → fill title/type/content → **Ingest** → alert shows chunk count → the document appears in the list. Then create an incident whose service matches the doc and confirm evidence chunks can appear in its detail (depends on retrieval/embeddings being configured).

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): documents tab with list and ingest modal"
```

---

## Self-Review

**Spec coverage:**
- §3 endpoints — healthz (T1), incidents list/detail (T2), incident create (T3), documents list/create (T4). ✓
- §4 stack/layout — Vite+React+TS+Tailwind, no shadcn, no router, `/api` proxy, two-column board (T1, T2). ✓
- §5 modules — types/api/ui primitives/HealthDot (T1); IncidentList/Detail (T2); NewIncidentModal + samples (T3); DocumentList/NewDocumentModal (T4); App wiring (T2–T4). ✓
- §6 data flow — load list+health (T1/T2); create→GET detail→refresh (T3); doc create→refresh (T4); row click→detail (T2). ✓
- §7 error handling — ApiError with `detail`, inline 422, empty states (T1–T4). ✓
- §8 running — proxy + npm scripts (T1); prerequisites block covers the backend. ✓
- §9 acceptance — each criterion maps to a Task-4-or-earlier manual verify step. ✓
- §10 open items — evidence rendered as `[source_type] title` (T2); list filters intentionally deferred. ✓

**Placeholder scan:** the only intentional "paste from file" is T3/Step 1 sample constants (the source files are named exactly); all component/config steps contain full code. ✓

**Type consistency:** `IncidentCreated.incident_id`, `AnalysisOut._cache`, `EvidenceRef.{chunk_id,source_type,title}`, `DocumentCreated.chunks`, `SOURCE_TYPES` used identically across tasks. `refreshKey` promoted from frozen (T2) to stateful (T3) is called out explicitly. ✓
