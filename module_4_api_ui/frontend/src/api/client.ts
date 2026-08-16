import type { ApiErrorBody, Role } from './types'

const BASE_URL = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly context: Record<string, unknown>

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail || body.error)
    this.name = 'ApiError'
    this.status = status
    this.code = body.error
    this.context = body.context ?? {}
  }
}

export interface Identity {
  userId: string
  role: Role
}

// The active identity is module state rather than a hook dependency so that query
// functions, which run outside React's render, can attach the headers too.
let identity: Identity = { userId: 'demo-steward', role: 'steward' }

export function setIdentity(next: Identity): void {
  identity = next
}

export function getIdentity(): Identity {
  return identity
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('X-User-Id', identity.userId)
  headers.set('X-User-Role', identity.role)
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers })

  if (response.status === 204) {
    return null as T
  }

  const text = await response.text()
  const parsed: unknown = text ? JSON.parse(text) : null

  if (!response.ok) {
    const body = (parsed ?? {
      error: 'unknown_error',
      detail: response.statusText,
      context: {},
    }) as ApiErrorBody
    throw new ApiError(response.status, body)
  }

  return parsed as T
}

export function buildQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      value.forEach((entry) => search.append(key, String(entry)))
    } else {
      search.set(key, String(value))
    }
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body === undefined ? undefined : JSON.stringify(body) }),
  upload: <T>(path: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<T>(path, { method: 'POST', body: form })
  },
}
