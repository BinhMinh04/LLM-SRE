// Thin fetch wrapper. Talks to the backend via the relative `/api` (and `/healthz`)
// paths, which Vite proxies to :8000 in dev. Non-2xx responses throw an ApiError
// carrying the backend's `detail` string so the UI can surface 422 validation messages.

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`HTTP ${status}: ${detail}`)
    this.name = 'ApiError'
  }
}

async function handle<T>(res: Response): Promise<T> {
  const text = await res.text()
  let body: unknown = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = null // non-JSON error page (e.g. proxy 500) — fall back to status text
  }
  if (!res.ok) {
    const detail =
      body && typeof body === 'object' && 'detail' in body
        ? typeof (body as { detail: unknown }).detail === 'string'
          ? (body as { detail: string }).detail
          : JSON.stringify((body as { detail: unknown }).detail)
        : res.statusText || `Request failed (HTTP ${res.status})`
    throw new ApiError(res.status, detail)
  }
  return body as T
}

/** Normalise any thrown value (ApiError, network TypeError, …) to a message. */
export function errText(e: unknown): string {
  if (e instanceof ApiError) return e.detail
  if (e instanceof Error) return e.message
  return String(e)
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
