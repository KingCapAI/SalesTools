const TOKEN_KEY = 'hangtime_token'
const USER_KEY = 'hangtime_user'

export type Me = { id: number; name: string; emoji: string; city: string }

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getStoredUser(): Me | null {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? (JSON.parse(raw) as Me) : null
}

export function saveSession(token: string, user: Me) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(path, { ...options, headers: { ...headers, ...(options.headers as Record<string, string>) } })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const get = <T,>(path: string) => api<T>(path)
export const post = <T,>(path: string, body?: unknown) =>
  api<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
export const del = <T,>(path: string) => api<T>(path, { method: 'DELETE' })
