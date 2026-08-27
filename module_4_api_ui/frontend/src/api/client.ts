const BASE = '/api/v1'

let _userId = 'demo-steward'
let _role = 'steward'

export function setCredentials(userId: string, role: string) {
  _userId = userId
  _role = role
}

export function getCredentials() {
  return { userId: _userId, role: _role }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers({
    'X-User-Id': _userId,
    'X-User-Role': _role,
    ...(init.headers as Record<string, string>),
  })
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${BASE}${path}`, { ...init, headers })
  if (res.status === 204) return null as T
  const text = await res.text()
  const json = text ? JSON.parse(text) : null
  if (!res.ok) throw new Error(json?.detail ?? json?.error ?? res.statusText)
  return json as T
}

export const api = {
  get: <T>(path: string) => req<T>(path),
  post: <T>(path: string, body?: unknown) =>
    req<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    req<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),
  upload: <T>(path: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return req<T>(path, { method: 'POST', body: form })
  },
}
