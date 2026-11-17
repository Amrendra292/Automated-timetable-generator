const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function saveToken(token: string | null) {
  if (token) localStorage.setItem('schedwise_token', token)
  else localStorage.removeItem('schedwise_token')
}

export async function api<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const headers = new Headers(options.headers || {})
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      message = typeof body.detail === 'string' ? body.detail : body.detail?.message || JSON.stringify(body.detail || body)
    } catch { /* keep fallback message */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function downloadCsv(token: string) {
  const response = await fetch(`${API_URL}/api/timetable/export.csv`, { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) throw new Error('Generate a timetable before exporting it.')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'schedwise-timetable.csv'
  anchor.click()
  URL.revokeObjectURL(url)
}
